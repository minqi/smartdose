from django.db import models
from django.db.models import Q
from doctors.models import DoctorProfile
from common.models import Drug
import datetime
from common.utilities import weekOfMonth, lastWeekOfMonth


class Prescription(models.Model):
	"""Model for prescriptions"""
	prescriber     				= models.ForeignKey(DoctorProfile, blank=False)
	patient        				= models.ForeignKey('patients.PatientProfile', blank=False)
	drug           				= models.ForeignKey(Drug, blank=False)
	safety_net_on				= models.BooleanField(default=False)
	

	with_food      				= models.BooleanField(default=False)
	with_water     				= models.BooleanField(default=False)
	last_edited    				= models.DateTimeField(auto_now=True)
	note		  				= models.CharField(max_length=300)

	total_reminders_sent		= models.PositiveIntegerField(null=False, blank=False, default=0)
	total_reminders_acked		= models.PositiveIntegerField(null=False, blank=False, default=0)
	last_contacted_safety_net 	= models.DateTimeField(null=True)

	def reminderSent(self):
		self.total_reminders_sent += 1
		self.save()

	def reminderAcked(self):
		self.total_reminders_acked +=1
		self.save()

class ReminderManager(models.Manager):
	def reminders_at_time(self, dt, offset):
		"""Returns all reminders from (dt - offset) to dt

		Keyword arguments:
		dt -- the datetime for which we care about reminders. datetime object
		offset -- the amount of time into the past to go to retrieve reminders. python timedelta object
		"""
		t = dt.time()
		day_of_week = dt.isoweekday()
		week_of_month = weekOfMonth(dt)
		day_of_month = dt.day
		day_of_year = dt.timetuple().tm_yday
		last_day_of_week = lastWeekOfMonth(dt)
		
		offset_t = (dt - offset).time()
		offset_day_of_week = (dt-offset).isoweekday()
		offset_week_of_month = weekOfMonth(dt-offset)
		offset_day_of_month = (dt-offset).day
		offset_day_of_year = (dt-offset).timetuple().tm_yday
		offset_last_day_of_week = lastWeekOfMonth(dt-offset)

		if day_of_week == offset_day_of_week:
			# Get all reminders sent between time-offset and time
			reminders_at_time = super(ReminderManager, self).get_query_set().filter(
				(Q(send_time__gte=offset_t) & Q(send_time__lte=t)) &
					((Q(repeat=ReminderTime.DAILY)) | 
					(Q(repeat=ReminderTime.WEEKLY, day_of_week=day_of_week)) | 
					(Q(repeat=ReminderTime.MONTHLY, week_of_month=week_of_month, day_of_week=day_of_week)) |
					(Q(repeat=ReminderTime.MONTHLY, week_of_month=ReminderTime.LAST_WEEK_OF_MONTH, day_of_week=day_of_week)) |
					(Q(repeat=ReminderTime.MONTHLY, day_of_month=day_of_month)) |
					(Q(repeat=ReminderTime.YEARLY, day_of_year=day_of_year))))
			if not last_day_of_week: 
				if week_of_month != 5:
					reminders_at_time = reminders_at_time.exclude(repeat=ReminderTime.MONTHLY, week_of_month=ReminderTime.LAST_WEEK_OF_MONTH, day_of_week=day_of_week)
		else:
			# If the offset causes wrapping, go query previous day and current day
			midnight = datetime.time.min
			dawn = datetime.time.max
			reminders_at_time = super(ReminderManager, self).get_query_set().filter(
				((Q(send_time__gte=midnight) & Q(send_time__lte=t)) &
					((Q(repeat=ReminderTime.DAILY)) | 
					(Q(repeat=ReminderTime.WEEKLY, day_of_week=day_of_week)) | 
					(Q(repeat=ReminderTime.MONTHLY, week_of_month=week_of_month, day_of_week=day_of_week)) |
					(Q(repeat=ReminderTime.MONTHLY, week_of_month=ReminderTime.LAST_WEEK_OF_MONTH, day_of_week=day_of_week)) |
					(Q(repeat=ReminderTime.MONTHLY, day_of_month=day_of_month)) |
					(Q(repeat=ReminderTime.YEARLY, day_of_year=day_of_year)))) | 
				(Q(send_time__gte=offset_t) & Q(send_time__lte=dawn)) &
					((Q(repeat=ReminderTime.DAILY)) | 
					(Q(repeat=ReminderTime.WEEKLY, day_of_week=offset_day_of_week)) | 
					(Q(repeat=ReminderTime.MONTHLY, week_of_month=offset_week_of_month, day_of_week=offset_day_of_week)) |
					(Q(repeat=ReminderTime.MONTHLY, week_of_month=ReminderTime.LAST_WEEK_OF_MONTH, day_of_week=offset_day_of_week)) |
					(Q(repeat=ReminderTime.MONTHLY, day_of_month=offset_day_of_month)) |
					(Q(repeat=ReminderTime.YEARLY, day_of_year=offset_day_of_year))))
			if not last_day_of_week: 
				if week_of_month != 5:
					reminders_at_time = reminders_at_time.exclude((Q(send_time__gte=midnight) & Q(send_time__lte=t)), repeat=ReminderTime.MONTHLY, week_of_month=ReminderTime.LAST_WEEK_OF_MONTH, day_of_week=day_of_week)\
														 .exclude((Q(send_time__gte=offset_t) & Q(send_time__lte=dawn)), repeat=ReminderTime.MONTHLY, week_of_month=ReminderTime.LAST_WEEK_OF_MONTH, day_of_week=offset_day_of_week)
		return reminders_at_time

class ReminderTime(models.Model):
	"""Model for all of the times in a day/week/month/year that a prescription will be sent"""
	# repeat choices i.e., what is the period of this reminder time
	DAILY   = 'd'
	WEEKLY  = 'w'
	MONTHLY = 'm'
	YEARLY  = 'y'
	CUSTOM  = 'c'
	REPEAT_CHOICES = (
		(DAILY,   'd'),
		(WEEKLY,  'w'),
		(MONTHLY, 'm'),
		(YEARLY,  'y'),
		(CUSTOM,  'c'),
	)
	# If value of week_of_month is 5, it means "last day of month" 
	# e.g., last Tuesday of every month
	LAST_WEEK_OF_MONTH = 5

	prescription 	= models.ForeignKey(Prescription, blank=False, null=False)
	repeat 			= models.CharField(max_length=2,
									   choices=REPEAT_CHOICES, blank=False, null=False)
	send_time		= models.TimeField(blank=False, null=False)
	day_of_week		= models.PositiveIntegerField(null=True) #Monday = 1 Sunday = 7
	day_of_month	= models.PositiveIntegerField(null=True)
	# If value of week_of_month is 5, it means "last day of month" 
	# e.g., last Tuesday of every month
	week_of_month	= models.PositiveIntegerField(null=True) 
	day_of_year		= models.PositiveIntegerField(null=True)
	month_of_year	= models.PositiveIntegerField(null=True)
	objects 		= ReminderManager()
	#TODO(mgaba): Write code to store an arbitrary function for "custom" types. Will involve serializing functions, etc.

class MessageManager(models.Manager):
	def create(self, patient):
		# Number of hours in the past to allow acking of messages. (23 hours avoids rounding problems and still gives a full days time to ack)
		MESSAGE_CUTOFF = 23 #hours
		expired_time = datetime.datetime.now() - datetime.timedelta(hours=MESSAGE_CUTOFF)
		
		# Calculate the message number to assign to new message
		new_message_number = 1
		active_messages = self.filter(time_sent__gte=expired_time, patient=patient)
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
		expired_messages = self.filter(message_number=new_message_number, state=Message.UNACKED)
		expired_messages.update(state=Message.EXPIRED)
		return super(MessageManager, self).create(patient=patient, message_number=new_message_number)

class Message(models.Model):
	"""Model for messages that have been sent to users"""
	class Meta:
		ordering = ['-time_sent']

	UNACKED   	= 'u'
	ACKED 		= 'a'
	EXPIRED 	= 'e'
	STATE_CHOICES = (
		(UNACKED, 	'u'),
		(ACKED, 	'a'),
		(EXPIRED,	'e'))

	patient 					= models.ForeignKey('patients.PatientProfile', blank=False)
	time_sent					= models.DateTimeField(auto_now_add=True)
	message_number				= models.PositiveIntegerField(blank=False, null=False, default=1)
	state 						= models.CharField(max_length=2,
												   choices=STATE_CHOICES,
												   default=UNACKED)
	objects						= MessageManager()

	def processAck(self):
		self.state = Message.ACKED
		self.save()
		sentreminders = SentReminder.objects.filter(message=self)
		for sentreminder in sentreminders:
			sentreminder.processAck()

class SentReminderManager(models.Manager):
	def create(self, prescription, reminder_time, message):
		prescription.reminderSent()
		return super(SentReminderManager, self).create(prescription=prescription, reminder_time=reminder_time, message=message)

class SentReminder(models.Model):
	"""Model for reminders that have been sent"""
	prescription 			= models.ForeignKey(Prescription, blank=False)
	reminder_time 			= models.ForeignKey(ReminderTime, blank=False)
	message 				= models.ForeignKey(Message)
	time_sent    			= models.DateTimeField(auto_now_add=True)
	ack						= models.BooleanField(default=False)
	objects					= SentReminderManager()

	def processAck(self):
		self.ack = True
		self.save()
		self.prescription.reminderAcked()


