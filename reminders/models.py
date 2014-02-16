import datetime, calendar

from django.db import models
from django.db.models import Q
from doctors.models import DoctorProfile
from common.models import Drug
from common.utilities import weekOfMonth, lastWeekOfMonth
from configs.dev.settings import MESSAGE_CUTOFF, REMINDER_MERGE_INTERVAL

class Prescription(models.Model):
	"""Model for prescriptions"""
	prescriber     				= models.ForeignKey(DoctorProfile, blank=False)
	patient        				= models.ForeignKey('patients.PatientProfile', blank=False)
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

class ReminderManager(models.Manager):
	def reminders_at_time(self, now_datetime):
		"""
		Returns all notifications at and before now_datetime
		If there is at least one such reminder, also looks ahead REMINDER_MERGE_INTERVAL
		seconds to look for additional notifications

		Arguments:
		now_datetime -- the datetime for which we care about reminders. datetime object
		"""
		reminders_at_time = super(ReminderManager, self).get_query_set().filter(
			Q(active=True) &
			Q(send_time__lte=now_datetime)
		)
		latest_reminder = None
		if reminders_at_time.exists():
			latest_reminder = reminders_at_time.latest()
		if latest_reminder:
			max_send_time_for_batch = latest_reminder.send_time + datetime.timedelta(seconds=REMINDER_MERGE_INTERVAL)
			reminders_at_time = super(ReminderManager, self).get_queryset().filter(
				Q(active=True) &
				Q(send_time__lt=max_send_time_for_batch)
			)

		print "found reminders for " + str([r.to.first_name for r in reminders_at_time]) + "..."
		return reminders_at_time

	def create_prescription_reminders(self, to, repeat, prescription):
		"""Schedule both a refill reminder and a medication reminder for a prescription"""
		refill_reminder = ReminderTime.objects.get_or_create(to=to, 
													 reminder_type=ReminderTime.REFILL, 
												     repeat=repeat, 
													 prescription=prescription)[0]
		med_reminder = ReminderTime.objects.get_or_create(to=to, 
												  reminder_type=ReminderTime.MEDICATION, 
										  		  repeat=repeat, 
										  		  prescription=prescription)[0]
		return (refill_reminder, med_reminder)

	def create_safety_net_notification(self, to, text):
		safetynet_reminder = ReminderTime.objects.get_or_create(to=to, 
														reminder_type=ReminderTime.SAFETY_NET,
														repeat=ReminderTime.ONE_SHOT, 
														text=text)[0]
		return safetynet_reminder

	def create_welcome_notification(self, to):
		welcome_reminder = ReminderTime.objects.get_or_create(to=to, 
			reminder_type=ReminderTime.WELCOME, repeat=ReminderTime.ONE_SHOT)[0]
		return welcome_reminder

class ReminderTime(models.Model):
	"""Model for all of the times in a day/week/month/year that a prescription will be sent"""
	# Reminder type
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

	# repeat choices i.e., what is the period of this reminder time
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
	#TODO(mgaba): Write code to store an arbitrary function for "custom" types; 
	# may involve serializing functions

	# If value of week_of_month is 5, it means "last day of month" 
	# e.g., last Tuesday of every month
	LAST_WEEK_OF_MONTH = 5

	# required fields:
	to       			= models.ForeignKey('patients.PatientProfile', null=False, blank=False)
	reminder_type		= models.CharField(max_length=4,
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
	active				= models.BooleanField(default=True) # is the reminder still alive?

	objects 			= ReminderManager()

	def __update_one_shot_send_time(self):
		if self.repeat == self.ONE_SHOT:
			pass

	def __update_daily_send_time(self):
		if self.repeat == self.DAILY:
			now = datetime.datetime.now()
			dt = datetime.timedelta(days=1)
			while self.send_time <= now:
				self.send_time += dt
			self.save()

	def __update_weekly_send_time(self):
		if self.repeat == self.WEEKLY:
			now = datetime.datetime.now()
			dt = datetime.timedelta(days=7)
			while self.send_time <= now:
				self.send_time += dt
			self.save()

	def __update_monthly_send_time(self):
		if self.repeat == self.MONTHLY:
			now_date = datetime.datetime.now().date()
			next_date = self.send_time.date()
			year = next_date.year
			month = next_date.month
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
			while year <= now_year:
				year += 1

			next_date = datetime.date(year, month, day)
			self.send_time = datetime.datetime.combine(next_date, self.send_time.time())
			self.save()

	def __update_custom_send_time(self):
		if self.reminder_type == self.CUSTOM:
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

	# return the optimal time to send reminder
	def get_best_send_time(self):
		pass

	# return and set the optimal time to send reminder 
	def set_best_send_time(self):
		# (placeholder for now)
		if not self.send_time:
			self.send_time = datetime.datetime.now()
		pass

	def __init__(self, *args, **kwargs):
		super(ReminderTime, self).__init__(*args, **kwargs)
		# custom init logic
		# TODO(minqi): write custom initialization checks, e.g. automatically determining send_time
		# by parsing the prescription sig
		if not self.send_time:
			self.set_best_send_time()

	class Meta:
		get_latest_by = 'send_time'


class MessageManager(models.Manager):
	def create(self, patient):
		# Calculate the appropriate message number
		# Number of hours in the past to allow acking of messages. 
		# (MESSAGE_CUTOFF == 23 hours avoids rounding problems and still gives a full days time to ack)
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
		return super(MessageManager, self).create(patient=patient, message_number=new_message_number)

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
		(EXPIRED,	'e'))

	patient        = models.ForeignKey('patients.PatientProfile', blank=False)
	time_sent      = models.DateTimeField(auto_now_add=True)
	message_number = models.PositiveIntegerField(blank=False, null=False, default=1)
	state          = models.CharField(max_length=2,
											   choices=STATE_CHOICES,
											   default=UNACKED)
	objects		   = MessageManager()

	def processAck(self):
		self.state = Message.ACKED
		self.save()
		sentreminders = SentReminder.objects.filter(message=self)
		for sentreminder in sentreminders:
			sentreminder.processAck()

class SentReminder(models.Model):
	"""Model for reminders that have been sent"""
	prescription   = models.ForeignKey(Prescription, null=True)
	reminder_time  = models.ForeignKey(ReminderTime, blank=False)
	message 	   = models.ForeignKey(Message)
	time_sent      = models.DateTimeField(auto_now_add=True)
	ack			   = models.BooleanField(default=False)

	class Meta:
		get_latest_by = "time_sent"

	def processAck(self):
		self.ack = True
		self.save()
		if self.reminder_time.reminder_type == ReminderTime.REFILL:
			self.prescription.filled = True
			self.prescription.save()
			self.reminder_time.active = False
			self.reminder_time.save()


