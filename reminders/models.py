import datetime, calendar
from itertools import groupby
from django.core.exceptions import ValidationError

from django.db import models
from django.db.models import Q

from common.models import UserProfile, Drug
from configs.dev.settings import MESSAGE_CUTOFF, REMINDER_MERGE_INTERVAL, DOCTOR_INITIATED_WELCOME_SEND_TIME
from patients.models import PatientProfile

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
			Q(send_datetime__lte=now_datetime)
		).order_by('to', 'send_datetime') # order by recipient's full name, then by send_time

		all_notifications_at_time = Notification.objects.none()
		if notifications_at_time.exists():
			for recipient, recipient_group in groupby(notifications_at_time, lambda x: x.to):
				latest_notification = None
				for latest_notification in recipient_group: # get latest notification in group
					pass
				max_send_time_for_batch = latest_notification.send_datetime + datetime.timedelta(seconds=REMINDER_MERGE_INTERVAL)
				notifications_at_time_for_user = super(NotificationManager, self).get_queryset().filter(
					Q(to=recipient) &
					Q(active=True) &
					Q(send_datetime__lt=max_send_time_for_batch)
				)
				all_notifications_at_time = all_notifications_at_time | notifications_at_time_for_user
		return all_notifications_at_time

	def create_prescription_notifications(self, to, repeat, prescription):
		"""STUB: Schedule both a refill notification and a medication notification for a prescription"""
		refill_notification = None
		if not prescription.filled:
			refill_notification = Notification.objects.get_or_create(to=to,
			                                             type=Notification.REFILL,
														 repeat=Notification.DAILY,
														 prescription=prescription)[0]
		med_notification = Notification.objects.get_or_create(to=to,
		                                          type=Notification.MEDICATION,
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
			                                                     type=Notification.REFILL,
																 repeat=Notification.DAILY,
																 send_datetime=notification_schedule[0][1],
																 prescription=prescription)[0]
		notification_times = []
		for notification_schedule_entry in notification_schedule:
			notification_time = Notification.objects.create(to=to,
			                                            type=Notification.MEDICATION,
														prescription=prescription,
														repeat=notification_schedule_entry[0],
														send_datetime=notification_schedule_entry[1])
			notification_times.append(notification_time)

		return (refill_notification, notification_times)

	def create_consumer_welcome_notification(self, to, enroller):
		welcome_reminder = Notification.objects.get_or_create(to=to, enroller=enroller,
			type=Notification.WELCOME, repeat=Notification.NO_REPEAT)[0]
		return welcome_reminder

class Notification(models.Model):
	"""
	A Notification marks a point in time for when an outgoing message needs to be sent to a user.
	A Notification has a repeat field specifying how frequently the user should be notified.
	Notifications are periodically grouped into Messages and sent to users."""

	# Notification type
	MEDICATION 	    = 'm'
	REFILL 		    = 'r'
	WELCOME         = 'w'
	SAFETY_NET      = 'sn'
	NON_ADHERENT    = 'n'
	STATIC_ONE_OFF  = 'sof'
	REPEAT_MESSAGE  = 'rm'

	NOTIFICATION_TYPE_CHOICES = (
		(MEDICATION, 'medication'),
		(REFILL,	 'refill'),
		(WELCOME,    'welcome'),
		(SAFETY_NET, 'safety_net'),
		(NON_ADHERENT, 'non_adherent'),
		(STATIC_ONE_OFF, 'static_one_off')
	)

	@classmethod
	def is_valid_type(cls, type):
		for choice in cls.NOTIFICATION_TYPE_CHOICES:
			if type == choice[0]:
				return True
		return False

	# repeat choices i.e., what is the period of this notification time
	NO_REPEAT = 'nr'
	DAILY    = 'd'
	WEEKLY   = 'w'
	MONTHLY  = 'm'
	YEARLY   = 'y'
	CUSTOM   = 'c' 
	REPEAT_CHOICES = (
		(NO_REPEAT, 'no_repeat'),
		(DAILY,    'daily'),
		(WEEKLY,   'weekly'),
		(MONTHLY,  'monthly'),
		(YEARLY,   'yearly'),
		(CUSTOM,   'custom'),
	)	

	type            	= models.CharField(max_length=4,
	                                            choices=NOTIFICATION_TYPE_CHOICES, null=False, blank=False)
	to       			= models.ForeignKey(PatientProfile, null=False, blank=False)
	repeat 				= models.CharField(max_length=2,
	                                         choices=REPEAT_CHOICES, null=False, blank=False)
	send_datetime		= models.DateTimeField(null=False, blank=False)
	active				= models.BooleanField(default=True) # is the notification still alive?

	objects 			= NotificationManager()

	day_of_week         = models.PositiveSmallIntegerField(null=True, blank=True)

	times_sent          = models.PositiveIntegerField(default=0)

	# Required types: REFILL, MEDICATION
	prescription        = models.ForeignKey(Prescription, null=True, blank=True)

	# Required type: STATIC_ONE_OFF
	content             = models.CharField(max_length=160, null=True, blank=True) #Required type: STATIC_ONE_OFF

	# Required type: SAFETY_NET
	patient_of_safety_net   = models.ForeignKey(PatientProfile, related_name="patient_of_safety_net", null=True, blank=True)
	adherence_rate          = models.PositiveSmallIntegerField(null=True, blank=True)

	# Required type: REPEAT_MESSAGE
	message             = models.ForeignKey('Message', null=True, blank=True, related_name="repeat_message")

	# Required type: WELCOME
	enroller            = models.ForeignKey(UserProfile, null=True, blank=True, related_name="enroller")



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

		if not self.send_datetime:
			self.set_best_send_time()

		if self.type in [Notification.REFILL, Notification.MEDICATION]:
			if self.prescription is None:
				raise ValidationError("This type of notification requires a foreign-key to a prescription")

		if self.type in [Notification.STATIC_ONE_OFF]:
			if self.content is None:
				raise ValidationError("This type of notification requires predefined content")

		if self.type in [Notification.SAFETY_NET]:
			if self.patient_of_safety_net is None or self.adherence_rate is None:
				raise ValidationError("This type of notification requires patient of safety net member and adherence rate "
				                      "information")

		if self.type in [Notification.REPEAT_MESSAGE]:
			if self.message is None:
				raise ValidationError("This type of notification requires a message pointer")

		if self.type in [Notification.WELCOME]:
			if self.enroller is None:
				raise ValidationError("This type of notification requires an enroller")

		if self.repeat == "":
			raise ValidationError("All notifications require a repeat value")

		if self.repeat == self.WEEKLY:
			self.day_of_week = self.send_datetime.isoweekday()


	# update send_time to next send_time based on notification period
	def update_to_next_send_time(self):
		update_periodic_send_time = {
		self.NO_REPEAT: self.__update_one_shot_send_time,
		self.DAILY:    self.__update_daily_send_time,
		self.WEEKLY:   self.__update_weekly_send_time,
		self.MONTHLY:  self.__update_monthly_send_time,
		self.YEARLY:   self.__update_yearly_send_time,
		self.CUSTOM:   self.__update_custom_send_time,
		}
		self.times_sent += 1
		update_periodic_send_time[self.repeat]()

	# return the optimal time to send notification
	def get_best_send_time(self):
		pass

	# return and set the optimal time to send notification
	def set_best_send_time(self):
		# (placeholder for now)
		if not self.send_datetime:
			self.send_datetime = datetime.datetime.now()
		pass


	def __update_one_shot_send_time(self):
		if self.repeat == self.NO_REPEAT:
			self.active = False
			self.save()

	def __update_daily_send_time(self):
		if self.repeat == self.DAILY:
			now = datetime.datetime.now()
			dt = datetime.timedelta(days=1)
			self.send_datetime += dt
			while self.send_datetime <= now:
				self.send_datetime += dt
			self.save()

	def __update_weekly_send_time(self):
		if self.repeat == self.WEEKLY:
			now = datetime.datetime.now()
			dt = datetime.timedelta(days=7)
			self.send_datetime += dt
			while self.send_datetime <= now:
				self.send_datetime += dt
			self.save()

	def __update_monthly_send_time(self):
		if self.repeat == self.MONTHLY:
			now_date = datetime.datetime.now().date()
			next_date = self.send_datetime.date()
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

			self.send_datetime = datetime.datetime.combine(next_date, self.send_datetime.time())
			self.save()

	def __update_yearly_send_time(self):
		if self.repeat == self.YEARLY:
			now_year = datetime.datetime.now().date().year
			date = self.send_datetime.date()
			year  = date.year
			month = date.month
			day = date.day
			year += 1
			while year <= now_year:
				year += 1

			next_date = datetime.date(year, month, day)
			self.send_datetime = datetime.datetime.combine(next_date, self.send_datetime.time())
			self.save()

	def __update_custom_send_time(self):
		if self.type == self.CUSTOM:
			pass

#==============MESSAGE RELATED CLASSES=======================

class MessageManager(models.Manager):
	def create(self, **kwargs):
		# Set correct value for nth_message_of_day_of_type
		if 'nth_message_of_day_of_type' in kwargs:
			return super(MessageManager, self).create(**kwargs)
		if 'type' in kwargs:
			type = kwargs['type']
		else:
			return super(MessageManager, self).create(**kwargs)

		today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
		todays_messages = self.filter(datetime_sent__gte=today, type=type)
		if todays_messages:
			nth_message_of_day_of_type = todays_messages.first().nth_message_of_day_of_type + 1
		else:
			nth_message_of_day_of_type = 0
		return super(MessageManager, self).create(nth_message_of_day_of_type=nth_message_of_day_of_type, **kwargs)

	def get_last_sent_message_requiring_response(self, to):
		today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
		message = self.filter(to=to, datetime_sent__gte=today, type__in=Message.REQUIRE_RESPONSE_MESSAGES,
		                      datetime_responded=None)
		if message:
			message = message[0]
		else:
			message = None
		return message


class Message(models.Model):
	"""Model for messages that have been sent to users"""
	class Meta:
		ordering = ['-datetime_sent']

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

	NOTIFICATION_MESSAGES = [MEDICATION, REFILL, NON_ADHERENT, WELCOME, SAFETY_NET, STATIC_ONE_OFF]
	RESPONSE_MESSAGES = [MEDICATION_ACK, MEDICATION_QUESTIONNAIRE, REFILL_QUESTIONNAIRE, MED_INFO,
	                     NON_ADHERENT_QUESTIONNAIRE, OPEN_ENDED_QUESTION]

	# Messages requiring a response
	REQUIRE_RESPONSE_MESSAGES = [MEDICATION, MEDICATION_QUESTIONNAIRE, REFILL, REFILL_QUESTIONNAIRE, MED_INFO, NON_ADHERENT,
	                   NON_ADHERENT_QUESTIONNAIRE, OPEN_ENDED_QUESTION]

	MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY = {'a':'Haven\'t gotten the chance',
	                                               'b':'Need to refill',
	                                               'c':'Side effects',
	                                               'd':'Meds don\'t work',
	                                               'e':'Prescription changed',
	                                               'f':'I feel sad :(',
	                                               'g':'Other'}

	REFILL_QUESTIONNAIRE_RESPONSE_DICTIONARY = {'a':'Haven\'t gotten the chance',
	                                                'b':'Too expensive',
	                                                'c':'Concerned about side effects',
	                                                'd':'Other'}

	MESSAGE_TYPE_CHOICES = (                                            # Non-standard required fields:
		(MEDICATION,                'medication'),                      ## notifications, feedbacks, nth_message_of_day_of_type
		(MEDICATION_ACK,            'medication_ack'),                  ## previous_message, content
		(MEDICATION_QUESTIONNAIRE,  'medication_questionnaire'),        ## feedbacks, previous_message
		(REFILL,	                'refill'),                          ## notifications, feedbacks
		(REFILL_QUESTIONNAIRE,      'refill_questionnaire'),            ## feedbacks, previous_message
		(MED_INFO,                  'med_info'),                        ## previous_message
		(NON_ADHERENT,              'non_adherent'),                    ## notifications, feedbacks
		(NON_ADHERENT_QUESTIONNAIRE,'non_adherent_questionnaire'),      ## feedbacks, previous_message
		(OPEN_ENDED_QUESTION,       'open_ended_question'),             ## feedbacks, previous_message
		(WELCOME,                   'welcome'),                         ## N/A
		(SAFETY_NET,                'safety_net'),                      ## notifications
		(STATIC_ONE_OFF,            'static_one_off'),                  ## content
	)

	@classmethod
	def is_valid_type(cls, type):
		for choice in cls.MESSAGE_TYPE_CHOICES:
			if type == choice[0]:
				return True
		return False

	to                  = models.ForeignKey(PatientProfile, blank=False)
	type                = models.CharField(max_length=4, choices=MESSAGE_TYPE_CHOICES, null=False, blank=False)

	datetime_responded  = models.DateTimeField(blank=True, null=True)
	datetime_sent       = models.DateTimeField(auto_now_add=True)

	objects		    = MessageManager()

	content             = models.CharField(max_length=160)

	# Required types: MEDICATION, REFILL, NON_ADHERENT, SAFETY_NET
	notifications       = models.ManyToManyField(Notification, blank=True, null=True, related_name='notifications')

	# Required types: MEDICATION, MEDICATION_QUESTIONNAIRE, REFILL, REFILL_QUESTIONNAIRE
	#                 NON_ADHERENT, NON_ADHERENT_QUESTIONNAIRE, OPEN_ENDED_QUESTION
	feedbacks           = models.ManyToManyField('Feedback', blank=True, null=True)

	# Required types: RESPONSE_MESSAGES
	previous_message    = models.ForeignKey('Message', blank=True, null=True)


	# Required types: MEDICATION
	nth_message_of_day_of_type = models.PositiveSmallIntegerField(blank=True, null=True)

	def __init__(self, *args, **kwargs):
		super(Message, self).__init__(*args, **kwargs)

		if self.type in Message.RESPONSE_MESSAGES:
			if self.previous_message is None:
				raise ValidationError("A messages sent as a response requires a pointer to a previous message")

		if self.type in [Message.MEDICATION]:
			if self.nth_message_of_day_of_type is None:
				raise ValidationError("This type of message needs to know how many messages like it have been sent"
									  "today (nth_message_of_day_of_type)")



class Feedback(models.Model):
	"""Records information on a patients feedback for a given event tied to a notification
	(e.g., taking a drug, filling a prescription, general nonadherence)"""

	# All of the types of feedback
	MEDICATION 	                = 'm'
	REFILL 		                = 'r'

	FEEDBACK_TYPE_CHOICES = (
		(MEDICATION,                'medication'),
		(REFILL,	                'refill'),
	)

	@classmethod
	def is_valid_type(cls, type):
		for choice in cls.FEEDBACK_TYPE_CHOICES:
			if type == choice[0]:
				return True
		return False

	type           = models.CharField(max_length=4, choices=FEEDBACK_TYPE_CHOICES)
	notification   = models.ForeignKey(Notification)
	prescription   = models.ForeignKey(Prescription)

	datetime_sent      = models.DateTimeField(auto_now_add=True)

	datetime_responded = models.DateTimeField(blank=True, null=True)
	note           = models.CharField(max_length=320)

	completed      = models.BooleanField(default=False)

	class Meta:
		get_latest_by = "time_sent"

