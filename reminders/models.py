import datetime, calendar
from itertools import groupby

from django.db import models
from django.db.models import Q

from doctors.models import DoctorProfile
from patients.models import PatientProfile
from common.models import UserProfile, Drug
from configs.dev.settings import MESSAGE_CUTOFF, REMINDER_MERGE_INTERVAL, DOCTOR_INITIATED_WELCOME_SEND_TIME

class Prescription(models.Model):
	"""Model for prescriptions"""
	prescriber     				= models.ForeignKey(UserProfile, blank=False, related_name='prescriptions_given')
	patient        				= models.ForeignKey(PatientProfile, blank=False, related_name='prescriptions_received')
	drug           				= models.ForeignKey(Drug, blank=False)
	
	safety_net_on				= models.BooleanField(default=False)
	with_food      				= models.BooleanField(default=False)
	with_water     				= models.BooleanField(default=False)
	last_edited    				= models.DateTimeField(auto_now=True)
	sig                         = models.CharField(max_length=300)
	note		  				= models.CharField(max_length=300)

	last_contacted_safety_net 	= models.DateTimeField(null=True)

	# Has the prescription been filled at the pharmacy?
	filled						= models.BooleanField(default=False)

class NotificationManager(models.Manager):
	def notifications_at_time(self, now_datetime):
		"""
		Returns all notifications at and before now_datetime
		If there is at least one such notification, also looks ahead REMINDER_MERGE_INTERVAL
		seconds to look for additional notifications

		Arguments:
		now_datetime -- the datetime for which we care about notifications. datetime object
		"""
		notifications_at_time = super(NotificationManager, self).get_query_set().filter(
			Q(active=True) &
			Q(send_time__lte=now_datetime)
		).order_by('to', 'send_time') # order by recipient's full name, then by send_time

		all_notifications_at_time = Notification.objects.none()
		if notifications_at_time.exists():
			for recipient, recipient_group in groupby(notifications_at_time, lambda x: x.to):
				latest_notification = None
				for latest_notification in recipient_group: # get latest notification in group
					pass
				max_send_time_for_batch = latest_notification.send_time + datetime.timedelta(seconds=REMINDER_MERGE_INTERVAL)
				notifications_at_time_for_user = super(NotificationManager, self).get_queryset().filter(
					Q(to=recipient) &
					Q(active=True) &
					Q(send_time__lt=max_send_time_for_batch)
				)
				all_notifications_at_time = all_notifications_at_time | notifications_at_time_for_user
		return all_notifications_at_time

	def create_prescription_notifications(self, to, repeat, prescription):
		"""STUB: Schedule both a refill notification and a medication notification for a prescription"""
		refill_notification = None
		if not prescription.filled:
			refill_notification = Notification.objects.get_or_create(to=to,
														 notification_type=Notification.REFILL,
														 repeat=Notification.DAILY,
														 prescription=prescription)[0]
		med_notification = Notification.objects.get_or_create(to=to,
												  notification_type=Notification.MEDICATION,
												  repeat=Notification.DAILY,
												  prescription=prescription)[0]
		return (refill_notification, med_notification)


	def create_prescription_notifications_from_notification_schedule(self, to, prescription, notification_schedule):
		""" Take a prescription and a notification schedule and schedule a refill notification and medication
			notifications notification_schedule is a list of [repeat, send_time] tuples.
		"""
		refill_notification = None
		if not prescription.filled:
			refill_notification = Notification.objects.get_or_create(to=to,
																 notification_type=Notification.REFILL,
																 repeat=Notification.DAILY,
																 send_time=notification_schedule[0][1],
																 prescription=prescription)[0]
		notification_times = []
		for notification_schedule_entry in notification_schedule:
			notification_time = Notification.objects.create(to=to,
														notification_type=Notification.MEDICATION,
														prescription=prescription,
														repeat=notification_schedule_entry[0],
														send_time=notification_schedule_entry[1])
			notification_times.append(notification_time)

		return (refill_notification, notification_times)

	def create_safety_net_notification(self, to, text):
		safetynet_notification = Notification.objects.get_or_create(to=to, # Minqi: Why is this get or create?
																notification_type=Notification.SAFETY_NET,
																repeat=Notification.ONE_SHOT,
																text=text)[0]
		return safetynet_notification

	def create_consumer_welcome_notification(self, to):
		welcome_notification = Notification.objects.get_or_create(to=to,  # Minqi: Why is this get or create?
			notification_type=Notification.WELCOME, repeat=Notification.ONE_SHOT)[0]
		return welcome_notification

	def create_doctor_initiated_welcome_notification(self, to):
		welcome_notification = Notification.objects.create(to=to,
		    notification_type=Notification.WELCOME, repeat=Notification.ONE_SHOT,
		    send_time=DOCTOR_INITIATED_WELCOME_SEND_TIME)
		return welcome_notification


class Notification(models.Model):
	"""Model for all of the times in a day/week/month/year that a prescription will be sent"""
	# Notification type
	WELCOME     = 'w'
	MEDICATION 	= 'm'
	REFILL 		= 'r'
	SAFETY_NET  = 's'
	REMINDER_TYPE_CHOICES = (
		(WELCOME,    'welcome'),
		(MEDICATION, 'medication'),
		(REFILL,	 'refill'),
		(SAFETY_NET, 'safety_net'),
	)

	# repeat choices i.e., what is the period of this notification time
	ONE_SHOT = 'o'
	DAILY    = 'd'
	WEEKLY   = 'w'
	MONTHLY  = 'm'
	YEARLY   = 'y'
	CUSTOM   = 'c' 
	REPEAT_CHOICES = (
		(ONE_SHOT, 'one_shot'),
		(DAILY,    'daily'),
		(WEEKLY,   'weekly'),
		(MONTHLY,  'monthly'),
		(YEARLY,   'yearly'),
		(CUSTOM,   'custom'),
	)	

	# If value of week_of_month is 5, it means "last day of month" 
	# e.g., last Tuesday of every month
	LAST_WEEK_OF_MONTH = 5

	# required fields:
	to       			= models.ForeignKey(PatientProfile, null=False, blank=False)
	notification_type		= models.CharField(max_length=4,
									   choices=REMINDER_TYPE_CHOICES, null=False, blank=False)
	repeat 				= models.CharField(max_length=2,
									   choices=REPEAT_CHOICES, null=False, blank=False)

	# optional fields:
	send_time			= models.DateTimeField(null=True)
	day_of_week			= models.PositiveIntegerField(null=True) #Monday = 1 Sunday = 7
	day_of_month		= models.PositiveIntegerField(null=True)
	week_of_month		= models.PositiveIntegerField(null=True) # 5 indicates "last week of month"
	day_of_year			= models.PositiveIntegerField(null=True)
	month_of_year		= models.PositiveIntegerField(null=True)

	text            	= models.CharField(max_length=160, null=True, blank=True)
	prescription 		= models.ForeignKey(Prescription, null=True)
	active				= models.BooleanField(default=True) # is the notification still alive?

	objects 			= NotificationManager()

	def __update_one_shot_send_time(self):
		if self.repeat == self.ONE_SHOT:
			pass

	def __update_daily_send_time(self):
		if self.repeat == self.DAILY:
			now = datetime.datetime.now()
			dt = datetime.timedelta(days=1)
			self.send_time += dt
			while self.send_time <= now:
				self.send_time += dt
			self.save()

	def __update_weekly_send_time(self):
		if self.repeat == self.WEEKLY:
			now = datetime.datetime.now()
			dt = datetime.timedelta(days=7)
			self.send_time += dt
			while self.send_time <= now:
				self.send_time += dt
			self.save()

	def __update_monthly_send_time(self):
		if self.repeat == self.MONTHLY:
			now_date = datetime.datetime.now().date()
			next_date = self.send_time.date()
			year = next_date.year
			month = next_date.month
			next_month = next_date.month % 12 + 1
			next_year = next_date.year + next_month / 12
			next_day = min(next_date.day,calendar.monthrange(next_year,next_month)[1])
			next_date = datetime.date(next_year, next_month, next_day)

			while next_date <= now_date:
				next_month = next_date.month % 12 + 1
				next_year = next_date.year + next_month / 12
				next_day = min(next_date.day,calendar.monthrange(next_year,next_month)[1])
				next_date = datetime.date(next_year, next_month, next_day)

			if self.week_of_month == 5:
				cal = calendar.Calendar(0)
				month_week_dates = cal.monthdatescalendar(next_year, next_month)
				lastweek_month = month_week_dates[-1]
				next_date = lastweek_month[self.send_time.weekday()]

			self.send_time = datetime.datetime.combine(next_date, self.send_time.time())
			self.save()

	def __update_yearly_send_time(self):
		if self.repeat == self.YEARLY:
			now_year = datetime.datetime.now().date().year
			date = self.send_time.date()
			year  = date.year
			month = date.month
			day = date.day
			year += 1
			while year <= now_year:
				year += 1

			next_date = datetime.date(year, month, day)
			self.send_time = datetime.datetime.combine(next_date, self.send_time.time())
			self.save()

	def __update_custom_send_time(self):
		if self.notification_type == self.CUSTOM:
			pass

	# update send_time to next send_time based on notification period
	def update_to_next_send_time(self):
		update_periodic_send_time = {
			self.ONE_SHOT: self.__update_one_shot_send_time,
			self.DAILY:    self.__update_daily_send_time,
			self.WEEKLY:   self.__update_weekly_send_time,
			self.MONTHLY:  self.__update_monthly_send_time,
			self.YEARLY:   self.__update_yearly_send_time,
			self.CUSTOM:   self.__update_custom_send_time,
		}
		update_periodic_send_time[self.repeat]()

	# return the optimal time to send notification
	def get_best_send_time(self):
		pass

	# return and set the optimal time to send notification
	def set_best_send_time(self):
		# (placeholder for now)
		if not self.send_time:
			self.send_time = datetime.datetime.now()
		pass

	def __init__(self, *args, **kwargs):
		super(Notification, self).__init__(*args, **kwargs)
		# custom init logic
		# TODO(minqi): write custom initialization checks, e.g. automatically determining send_time
		# by parsing the prescription sig
		if self.id:
			return
		if not self.send_time:
			self.set_best_send_time()

	class Meta:
		get_latest_by = 'send_time'
		# TODO(matt): Note to minqi: Changed name of this permission
		permissions = (
			('view_notification_smartdose', 'View notification'),
			('change_notification_smartdose', 'Change notification'),
		)


class MessageManager(models.Manager):
	def create(self, patient, message_type):
		if message_type in [Message.REFILL, Message.MEDICATION]:
			# Calculate the appropriate message number
			# Number of hours in the past to allow acking of messages.
			expired_time = datetime.datetime.now() - datetime.timedelta(hours=MESSAGE_CUTOFF)
			# Calculate the message number to assign to new message
			new_message_number = 1
			active_messages = self.filter(time_sent__gte=expired_time, patient=patient).exclude(state=Message.ACKED)
			if active_messages:
				# Loop through active messages to find the lowest non-active message number.
				# There should never be too many active_messages for any person (no more than 4 or 5), so this is safe.
				active_message_length = active_messages.count()
				while new_message_number <= active_message_length:
					# If there is no active message with the message_number, then give that message number to the message
					# being created
					if not active_messages.filter(message_number=new_message_number):
						break
					new_message_number += 1
			# Mark all unacked messages with this number as expired
			expired_messages = self.filter(time_sent__lte=expired_time, state=Message.UNACKED)
			expired_messages.update(state=Message.EXPIRED)
		else:
			new_message_number = None
		return super(MessageManager, self).create(patient=patient, message_number=new_message_number, message_type=message_type)

class Message(models.Model):
	"""Model for messages that have been sent to users"""
	class Meta:
		ordering = ['-time_sent']

	UNACKED = 'u'
	ACKED 	= 'a'
	EXPIRED = 'e'
	STATE_CHOICES = (
		(UNACKED, 	'u'),
		(ACKED, 	'a'),
		(EXPIRED,   'e'),
	)

	WELCOME     = 'w'
	MEDICATION 	= 'm'
	REFILL 		= 'r'
	SAFETY_NET  = 's'
	REMINDER_TYPE_CHOICES = (
		(WELCOME,    'welcome'),
		(MEDICATION, 'medication'),
		(REFILL,	 'refill'),
		(SAFETY_NET, 'safety_net'),
	)

	patient         = models.ForeignKey(PatientProfile, blank=False)
	time_sent       = models.DateTimeField(auto_now_add=True)
	message_number  = models.PositiveIntegerField(blank=True, null=True, default=1)
	state           = models.CharField(max_length=2,
											   choices=STATE_CHOICES,
											   default=UNACKED)
	message_type    = models.CharField(
		max_length=4, choices=REMINDER_TYPE_CHOICES, null=False, blank=False)
	
	objects		    = MessageManager()

	def processAck(self):
		self.state = Message.ACKED
		self.save()
		sentreminders = SentReminder.objects.filter(message=self)
		for sentreminder in sentreminders:
			sentreminder.processAck()

class SentReminder(models.Model):
	"""Model for reminders that have been sent"""
	prescription   = models.ForeignKey(Prescription, null=True)
	notification  = models.ForeignKey(Notification, blank=False)
	message 	   = models.ForeignKey(Message)
	time_sent      = models.DateTimeField(auto_now_add=True)
	ack			   = models.BooleanField(default=False)

	class Meta:
		get_latest_by = "time_sent"

	def processAck(self):
		self.ack = True
		self.save()
		if self.notification.notification_type == Notification.REFILL:
			self.prescription.filled = True
			self.prescription.save()
			notifications = self.prescription.notification_set.all()
			# Advance medication reminder send times to a point after the refill reminder is ack'd
			now = datetime.datetime.now()
			for notification in notifications:
				if notification.notification_type == Notification.MEDICATION:
					if notification.send_time < now:
						notification.update_to_next_send_time()
			self.notification.active = False
			self.notification.save()


