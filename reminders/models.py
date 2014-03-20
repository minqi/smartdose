import datetime, calendar
from itertools import groupby

from django.db import models
from django.db.models import Q

from common.models import UserProfile, Drug
from configs.dev.settings import MESSAGE_CUTOFF, REMINDER_MERGE_INTERVAL, DOCTOR_INITIATED_WELCOME_SEND_TIME
from patients.models import PatientProfile

#==============NOTIFICATION RELATED CLASSES=======================

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





#==============NOTIFICATION RELATED CLASSES=======================

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
			refill_notification = RefillNotification.objects.get_or_create(to=to,
														 repeat=Notification.DAILY,
														 prescription=prescription)[0]
		med_notification = MedicationNotification.objects.get_or_create(to=to,
												  repeat=Notification.DAILY,
												  prescription=prescription)[0]
		return (refill_notification, med_notification)


	def create_prescription_notifications_from_notification_schedule(self, to, prescription, notification_schedule):
		""" Take a prescription and a notification schedule and schedule a refill notification and medication
			notifications notification_schedule is a list of [repeat, send_time] tuples.
		"""
		refill_notification = None
		if not prescription.filled:
			refill_notification = RefillNotification.objects.get_or_create(to=to,
																 repeat=Notification.DAILY,
																 send_time=notification_schedule[0][1],
																 prescription=prescription)[0]
		notification_times = []
		for notification_schedule_entry in notification_schedule:
			notification_time = MedicationNotification.objects.create(to=to,
														prescription=prescription,
														repeat=notification_schedule_entry[0],
														send_time=notification_schedule_entry[1])
			notification_times.append(notification_time)

		return (refill_notification, notification_times)

class Notification(models.Model):
	"""
	A Notification marks a point in time for when an outgoing message needs to be sent to a user.
	A Notification has a repeat field specifying how frequently the user should be notified.
	Notifications are periodically grouped into Messages and sent to users."""

	# Notification type
	MEDICATION 	    = 'm'
	REFILL 		    = 'r'
	WELCOME         = 'w'
	SAFETY_NET      = 's'
	NON_ADHERENT    = 'n'
	STATIC_ONE_OFF  = 'o'

	NOTIFICATION_TYPE_CHOICES = (
		(MEDICATION, 'medication'),
		(REFILL,	 'refill'),
		(WELCOME,    'welcome'),
		(SAFETY_NET, 'safety_net'),
		(NON_ADHERENT, 'non_adherent'),
		(STATIC_ONE_OFF, 'static_one_off')
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

	notification_type	= models.CharField(max_length=4,
	                                            choices=NOTIFICATION_TYPE_CHOICES, null=False, blank=False)
	to       			= models.ForeignKey(PatientProfile, null=False, blank=False)
	repeat 				= models.CharField(max_length=2,
	                                         choices=REPEAT_CHOICES, null=False, blank=False)
	send_time			= models.DateTimeField(null=False, blank=False)
	active				= models.BooleanField(default=True) # is the notification still alive?

	objects 			= NotificationManager()

	class Meta:
		get_latest_by = 'send_time'
		permissions = (
		('view_notification_smartdose', 'View notification'),
		('change_notification_smartdose', 'Change notification'),
		)

	def __init__(self, *args, **kwargs):
		super(Notification, self).__init__(*args, **kwargs)
		# custom init logic
		# TODO(minqi): write custom initialization checks, e.g. automatically determining send_time
		# by parsing the prescription sig
		if self.id:
			return
		if not self.send_time:
			self.set_best_send_time()

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

class MedicationNotification(Notification):
	"""A notification for a user to take a particular dose of medicine"""
	prescription	= models.ForeignKey(Prescription)
	parent          = models.OneToOneField(Notification, parent_link=True, primary_key=True)

	def __init__(self, *args, **kwargs):
		super(MedicationNotification, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.notification_type = Notification.MEDICATION

class RefillNotification(Notification):
	"""A notification for a user to fill/refill his prescriptions."""
	prescription	= models.ForeignKey(Prescription)

	def __init__(self, *args, **kwargs):
		super(RefillNotification, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.notification_type = Notification.REFILL

class WelcomeNotification(Notification):
	"""A notification that welcomes a user to Smartdose"""

	def __init__(self, *args, **kwargs):
		super(WelcomeNotification, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.notification_type = Notification.WELCOME
		self.repeat            = Notification.ONE_SHOT

class SafetyNetNotification(Notification):
	"""A notification that goes out to a safety net member about the patient's adherence rates"""
	safety_net_member   = models.ForeignKey(PatientProfile)
	adherence_rate      = models.PositiveSmallIntegerField()

	def __init__(self, *args, **kwargs):
		super(SafetyNetNotification, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.notification_type  = Notification.SAFETY_NET
		self.repeat             = Notification.ONE_SHOT

class NonAdherentNotification(Notification):
	"""A notification that goes out to a user when he's been non-adherent"""

	def __init__(self, *args, **kwargs):
		super(NonAdherentNotification, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.notification_type = Notification.NON_ADHERENT

class StaticOneOffNotification(Notification):
	"""A notification for sending a one-off message with static content"""

	content  = models.CharField(max_length=160)

	def __init__(self, *args, **kwargs):
		super(StaticOneOffNotification, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.notification_type = Notification.STATIC_ONE_OFF





#==============MESSAGE RELATED CLASSES=======================

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
		ordering = ['-datetime_sent']

	UNACKED = 'u'
	ACKED 	= 'a'
	EXPIRED = 'e'
	STATE_CHOICES = (
		(UNACKED, 	'u'),
		(ACKED, 	'a'),
		(EXPIRED,   'e'),
	)

	# All of the types of messages
	MEDICATION 	                = 'm'
	MEDICATION_ACK              = 'ma'
	MEDICATION_QUESTIONNAIRE    = 'mq'
	REFILL 		                = 'r'
	REFILL_QUESTIONNAIRE        = 'rq'
	MED_INFO                    = 'mi'
	NON_ADHERENT                = 'na'
	NON_ADHERENT_QUESTIONNAIRE  = 'naq'
	OPEN_ENDED_QUESTION         = 'oeq'
	WELCOME                     = 'w'
	SAFETY_NET                  = 'sn'
	STATIC_ONE_OFF              = 'sof'

	MESSAGE_TYPE_CHOICES = (
		(MEDICATION,                'medicationmessage'),
		(MEDICATION_ACK,            'medicationackmessage'),
		(MEDICATION_QUESTIONNAIRE,  'medicationquestionnairemessage'),
		(REFILL,	                'refillmessage'),
		(REFILL_QUESTIONNAIRE,      'refillquestionnairemessage'),
		(MED_INFO,                  'medinfomessage'),
		(NON_ADHERENT,              'nonadherentmessage'),
		(NON_ADHERENT_QUESTIONNAIRE,'nonadherentquestionnairemessage'),
		(OPEN_ENDED_QUESTION,       'openendedquestionmessage'),
		(WELCOME,                   'welcomemessage'),
		(SAFETY_NET,                'safetynetmessage'),
		(STATIC_ONE_OFF,            'staticoneoffmessage'),
	)

	MESSAGE_TYPE_TO_CHILD = dict(MESSAGE_TYPE_CHOICES)

	to                  = models.ForeignKey(PatientProfile, blank=False)
	datetime_sent       = models.DateTimeField(blank=True, null=True)
	responded           = models.BooleanField(default=False)
	datetime_responded  = models.DateTimeField(blank=True, null=True)
	message_type        = models.CharField(
			max_length=4, choices=MESSAGE_TYPE_CHOICES, null=False, blank=False)
	
	objects		    = MessageManager()

	def __init__(self, *args, **kwargs):
		super(Message, self).__init__(*args, **kwargs)
		self.did_send = False


	def prepare_to_send(self):
		if self._meta.object_name == 'Message':
			# Code executed here is executed when Message.prepare_to_send is called
			# Call prepare_to_send method of appropriate ChildMessage
			if hasattr(self, Message.MESSAGE_TYPE_TO_CHILD[self.message_type]):
				return getattr(self, Message.MESSAGE_TYPE_TO_CHILD[self.message_type]).prepare_to_send()
			else:
				raise Exception('this message has an invalid message_type')
		else:
			# Code executed here is executed when super(ChildMessage, self).prepare_to_send() is called
			if self.did_send:
				raise Exception("Message can only be sent once per instantiation")
			self.did_send = True

	def process_response(self):
		#TODO(mgaba):Write process response code here
		pass

	def processAck(self):
		self.state = Message.ACKED
		self.save()
		sentreminders = SentReminder.objects.filter(message=self)
		for sentreminder in sentreminders:
			sentreminder.processAck()

class MedicationMessageManager(models.Manager):
	def create(self, **kwargs):
		today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
		todays_messages = self.filter(datetime_sent__gte=today)
		if todays_messages:
			nth_message_of_day = todays_messages.first().nth_message_of_day + 1
		else:
			nth_message_of_day = 0
		super(MedicationMessageManager,self).create(nth_message_of_day=nth_message_of_day, **kwargs)

class MedicationMessage(Message):
	MESSAGE_TEMPLATE = 'messages/medication_reminder.txt'

	notifications = models.ManyToManyField(MedicationNotification)
	#medication_feedbacks = models.ManyToManyField("MedicationFeedback")
	nth_message_of_day = models.PositiveSmallIntegerField(default=0)

	#objects = MedicationMessageManager()

	def __init__(self, *args, **kwargs):
		super(MedicationMessage, self).__init__(*args, **kwargs)
		self.message_type = Message.MEDICATION


	def prepare_to_send(self):
		super(MedicationMessage, self).prepare_to_send()
		self.datetime_sent = datetime.datetime.now()

		for notification in self.notifications.all():
			MedicationFeedback.objects.create(prescription=notification.prescription)
			notification.update_to_next_send_time()

		return "Time to take your medicine!"
		pass

	def process_response(self):
		#TODO(mgaba):Write MedicationMessage response code
		pass

class MedicationAckMessage(Message):
	def __init__(self, *args, **kwargs):
		super(MedicationAckMessage,self).__init__(*args,**kwargs)
		self.message_type = Message.MEDICATION_ACK

	def prepare_to_send(self):
		#TODO(mgaba):Write MedicationAckMessage send code
		pass

	def process_response(self):
		#TODO(mgaba):Write MedicationAckMessage response code
		pass

class MedicationQuestionnaireMessage(Message):
	#TODO(mgaba): Add feedback key after implementing the feedback class
	#medication_feedbacks = models.ForeignKey(MedicationFeedback)

	def __init__(self, *args, **kwargs):
		super(MedicationQuestionnaireMessage,self).__init__(*args,**kwargs)
		self.message_type = Message.MEDICATION_QUESTIONNAIRE

	def prepare_to_send(self):
		#TODO(mgaba):Write MedicationQuestionnaireMessage send code
		pass

	def process_response(self):
		#TODO(mgaba):Write MedicationQuestionnaireMessage response code
		pass

class RefillMessage(Message):
	notifications = models.ManyToManyField(RefillNotification)
	#TODO(mgaba): Add feedback key after implementing the feedback class
	#refill_feedbacks = models.ManyToManyField(RefillFeedback)
	def __init__(self, *args, **kwargs):
		super(RefillMessage,self).__init__(*args,**kwargs)
		self.message_type = Message.REFILL

	def prepare_to_send(self):
		#TODO(mgaba):Write RefillMessage send code
		pass

	def process_response(self):
		#TODO(mgaba):Write RefillMessage response code
		#TODO(mgaba): Take code below and make it fit as response code
		"""
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
		pass
		"""

class WelcomeMessage(Message):
	def __init__(self, *args, **kwargs):
		super(WelcomeMessage,self).__init__(*args,**kwargs)
		self.message_type = Message.WELCOME

	def prepare_to_send(self):
		#TODO(mgaba):Write WelcomeMessage send code
		pass

	def process_response(self):
		#TODO(mgaba):Write WelcomeMessage response code
		pass

class SafetyNetMessage(Message):
	patient         = models.ForeignKey(PatientProfile)
	adherence_rate  = models.PositiveSmallIntegerField()
	def __init__(self, *args, **kwargs):
		super(SafetyNetMessage,self).__init__(*args,**kwargs)
		self.message_type = Message.SAFETY_NET

	def prepare_to_send(self):
		#TODO(mgaba):Write SafetyNetMessage send code
		pass

	def process_response(self):
		#TODO(mgaba):Write SafetyNetMessage response code
		pass

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

class Feedback(models.Model):
	"""Records information on a patients feedback for a given event tied to a notification
	(e.g., taking a drug, filling a prescription, general nonadherence)"""
	time_sent      = models.DateTimeField(auto_now_add=True)
	time_responded = models.DateTimeField(blank=True, null=True)
	note           = models.CharField(max_length=320)

	class Meta:
		get_latest_by = "time_sent"

	def setNote(self, note):
		self.note = note

class MedicationFeedback(Feedback):
	"""Feedback for a medication notification"""
	taken        = models.BooleanField(default=False)
	prescription = models.ForeignKey(Prescription)

	def setTaken(self):
		self.taken = True
		self.time_responded = datetime.datetime.now()
		self.save()

class RefillFeedback(Feedback):
	"""Feedback for a refill notification"""
	filled       = models.BooleanField(default=False)
	prescription = models.ForeignKey(Prescription)

	def setFilled(self):
		self.filled = True
		self.time_responded = datetime.datetime.now()
		self.save()

