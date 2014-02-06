from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from common.models import UserProfile, UserProfileManager
from common.utilities import sendTextMessageToNumber
from reminders.models import Message, SentReminder, ReminderTime
from django.core.exceptions import ValidationError

class SafetyNetRelationship(models.Model):
	patient 				= models.ForeignKey('PatientProfile', related_name='patient_safety_net')
	safety_net 				= models.ForeignKey('PatientProfile', related_name='safety_net_safety_net')
	patient_relationship	= models.CharField(null=False, blank=False, max_length="20")
	#TODO: Add fields for someone who has opted-out of the safety-net relationship

class PatientManager(UserProfileManager):
	"""Manager for performing operations on PatientProfile records"""

class PatientProfile(UserProfile):
	"""Model for patient-specific information"""
	# genders
	MALE = 'm'
	FEMALE = 'f'
	UNKNOWN = ''
	GENDER_CHOICES = (
		(MALE, 'm'),
		(FEMALE, 'f'),
		(UNKNOWN, ''),
	)

	# height units
	INCHES = 'in'
	METERS = 'm'
	HEIGHT_UNIT_CHOICES = (
		(INCHES, 'in'),
		(METERS, 'm'),
	)

	# weight units
	KILOGRAMS = 'kg'
	POUNDS = 'lb'
	WEIGHT_UNIT_CHOICES = (
		(KILOGRAMS, 'kg'),
		(POUNDS, 'lb'),
	)

	# Patient specific fields
	age = models.PositiveIntegerField(default=0)
	gender = models.CharField(max_length=1,
							  choices=GENDER_CHOICES,
							  default=UNKNOWN)
	height = models.PositiveIntegerField(default=0)
	height_unit = models.CharField(max_length=2,
								   choices=HEIGHT_UNIT_CHOICES,
								   default=INCHES)
	weight = models.PositiveIntegerField(default=0)
	weight_unit = models.CharField(max_length=2,
									choices=HEIGHT_UNIT_CHOICES,
									default=POUNDS)
	safety_net_members = models.ManyToManyField("self", through='SafetyNetRelationship', symmetrical=False)
	has_safety_net = models.BooleanField(default=False)
	# Manager fields
	objects = PatientManager()

	def sendTextMessage(self, body):
		# Additional checks/actions to be performed before sending a text to a
		# patient can happen at this step, if any.
		sendTextMessageToNumber(body, self.primary_phone_number)

	# Takes a patient and the reminders for which the patient will be receiving the text
	# @reminder_list is a ReminderTime QuerySet
	def sendReminders(self, reminder_list):
		# Don't send message if patient's account is disabled
		if self.status == PatientProfile.QUIT:
			return

		# Send welcome messages
		welcome_reminder_list = reminder_list.filter(reminder_type=ReminderTime.WELCOME)
		if welcome_reminder_list:
			welcome_reminder = list(welcome_reminder_list.order_by("send_time"))[0]
			message = Message.objects.create(patient=self)
			dictionary = {'patient_first_name':self.first_name}
			message_body = render_to_string('welcome_reminder.txt', dictionary)
			self.sendTextMessage(message_body)
			s = SentReminder.objects.create(reminder_time=welcome_reminder, message=message)
			welcome_reminder.active = False
			self.status = UserProfile.ACTIVE
			self.save()

		# Send refill reminders
		refill_reminder_list = reminder_list.filter(reminder_type=ReminderTime.REFILL)
		if refill_reminder_list:
			# Update database to reflect state of messages and reminders
			refill_reminder_list = refill_reminder_list.order_by("prescription__drug__name")
			message = Message.objects.create(patient=self)
			dictionary = {'reminder_list': refill_reminder_list, 'message_number': message.message_number}
			for reminder in refill_reminder_list:
				s = SentReminder.objects.create(prescription=reminder.prescription,
												reminder_time=reminder,
												message=message)
				reminder.update_to_next_send_time()
			# Send the refill message
			message_body = render_to_string('refill_reminder.txt', dictionary)
			self.sendTextMessage(message_body)

		# Send medication reminders
		medication_reminder_list = reminder_list.filter(reminder_type=ReminderTime.MEDICATION, prescription__filled=True)
		if medication_reminder_list:
			# Update database to reflect state of messages and reminders
			medication_reminder_list = medication_reminder_list.order_by("prescription__drug__name")
			message = Message.objects.create(patient=self)
			dictionary = {'reminder_list': medication_reminder_list, 'message_number': message.message_number}
			for reminder in medication_reminder_list:
				s = SentReminder.objects.create(prescription=reminder.prescription,
												reminder_time=reminder,
												message=message)
				reminder.update_to_next_send_time()
			# Send the medication message
			message_body = render_to_string('medication_reminder.txt', dictionary)
			self.sendTextMessage(message_body)

	def quit(self):
		self.status = PatientProfile.QUIT
		self.save()

	def addSafetyNetMember(self, patient_relationship, first_name, last_name, primary_phone_number, birthday):
		"""Returns a tuple of the safetynetmember and whether the safetynetmember was created or not"""
		#TODO: Figure out what happens when a user adds a safety net member with the same phone number as another member...we should probably present something in the UI to the user and ask them to confirm it is the appropriate person.
		#TODO: Add a way to create a backward-relationship
		created = True
		try: 
			sn = PatientProfile.objects.get(primary_phone_number=primary_phone_number)
			created = False
		except PatientProfile.DoesNotExist:
			sn = PatientProfile.objects.create(primary_phone_number=primary_phone_number,
													   username=primary_phone_number,
													   first_name=first_name,
													   last_name=last_name,
													   birthday=birthday)
		SafetyNetRelationship.objects.create(patient=self, safety_net=sn, patient_relationship=patient_relationship)
		self.has_safety_net = True
		self.save()

		#TODO: Send a message to a safety net member letting them know they've opted in.
		return sn, created

	# Note, code is shared across patient, doctor, and safety net models, so you should update in all places
	def validate_unique(self, *args, **kwargs):
		super(PatientProfile, self).validate_unique(*args, **kwargs)
		if not self.id:
			if self.__class__.objects.filter(primary_phone_number=self.primary_phone_number, birthday=self.birthday, first_name=self.first_name, last_name=self.last_name).exists():
				raise ValidationError('This patient already exists.')

	def save(self, *args, **kwargs):
		self.validate_unique()
		super(PatientProfile, self).save(*args, **kwargs)

