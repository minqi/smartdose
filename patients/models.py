from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from common.models import UserProfile, UserProfileManager
from common.utilities import sendTextMessageToNumber
from reminders.models import Message, SentReminder, ReminderTime, Prescription
from django.core.exceptions import ValidationError
# from reminders.notification_center import NotificationCenter

class SafetyNetRelationship(models.Model):
	#TODO: Add fields for someone who has opted-out of the safety-net relationship
	source_patient 				= models.ForeignKey('PatientProfile', related_name='target_patient_safety_net')
	target_patient 				= models.ForeignKey('PatientProfile', related_name='source_patient_safety_nets')
	patient_relationship		= models.CharField(null=False, blank=False, max_length="20")

class PrimaryContactRelationship(models.Model):
	source_patient 				= models.ForeignKey('PatientProfile', related_name='target_patient_primary_contacts')
	target_patient 				= models.ForeignKey('PatientProfile', related_name='source_patient_primary_contacts')
	patient_relationship		= models.CharField(null=False, blank=False, max_length="20")

class PatientManager(UserProfileManager):
	"""Manager for performing operations on PatientProfile records"""

class PatientProfile(UserProfile):
	"""Model for patient-specific information"""
	# genders
	MALE = 'm'
	FEMALE = 'f'
	UNKNOWN = ''
	GENDER_CHOICES = (
		(MALE, 'male'),
		(FEMALE, 'female'),
		(UNKNOWN, 'unknown'),
	)

	# height units
	INCHES = 'in'
	METERS = 'm'
	HEIGHT_UNIT_CHOICES = (
		(INCHES, 'inches'),
		(METERS, 'meters'),
	)

	# weight units
	KILOGRAMS = 'kg'
	POUNDS = 'lb'
	WEIGHT_UNIT_CHOICES = (
		(KILOGRAMS, 'kilograms'),
		(POUNDS, 'pounds'),
	)

	# Patient specific fields
	age 		= models.PositiveIntegerField(default=0)
	gender 		= models.CharField(max_length=1,
							  choices=GENDER_CHOICES,
							  default=UNKNOWN)
	height 		= models.PositiveIntegerField(default=0)
	height_unit = models.CharField(max_length=2,
								   choices=HEIGHT_UNIT_CHOICES,
								   default=INCHES)
	weight 		= models.PositiveIntegerField(default=0)
	weight_unit = models.CharField(max_length=2,
									choices=HEIGHT_UNIT_CHOICES,
									default=POUNDS)
	
	safety_net_members 		= models.ManyToManyField("self", 
		through='SafetyNetRelationship', symmetrical=False, related_name='safety_net')
	primary_contact_members = models.ManyToManyField("self", 
		through='PrimaryContactRelationship', symmetrical=False, related_name='primary_contact')
	has_safety_net 			= models.BooleanField(default=False)
	has_primary_contact 	= models.BooleanField(default=False)

	primary_phone_number 	= models.CharField(max_length=32, blank=True, null=True, unique=True)
	email 					= models.EmailField(blank=True, null=True, unique=True)

	# Manager fields
	objects = PatientManager()

	def __init__(self, *args, **kwargs):
		super(PatientProfile, self).__init__(*args, **kwargs)
		if self.id:
			return
		if self.primary_phone_number is None and self.has_primary_contact is False:
			raise ValidationError('Must provide either a primary phone number or primary contact')

	def quit(self):
		self.status = PatientProfile.QUIT
		self.save()

	def add_safetynet_member(self, patient_relationship, first_name, last_name, primary_phone_number, birthday):
		"""Returns a tuple of the safety_net_member and whether the safety_net_member was created or not"""
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
		SafetyNetRelationship.objects.create(source_patient=self, target_patient=sn, patient_relationship=patient_relationship)
		self.has_safety_net = True
		self.save()

		#TODO: Send a message to a safety net member letting them know they've opted in.
		return sn, created
	
	def add_primary_contact_member(self, patient_relationship, first_name, last_name, primary_phone_number, birthday):
		"""Returns a tuple of the primary_contact_member and whether the primary_contact_member was created or not"""
		#TODO: Figure out what happens when a user adds a primary contact member with the same phone number as another member...we should probably present something in the UI to the user and ask them to confirm it is the appropriate person.
		#TODO: Add a way to create a backward-relationship
		created = True
		try: 
			pc = PatientProfile.objects.get(primary_phone_number=primary_phone_number)
			created = False
		except PatientProfile.DoesNotExist:
			pc = PatientProfile.objects.create(primary_phone_number=primary_phone_number,
													   username=primary_phone_number,
													   first_name=first_name,
													   last_name=last_name,
													   birthday=birthday)
		PrimaryContactRelationship.objects.create(source_patient=self, target_patient=pc, patient_relationship=patient_relationship)
		self.has_primary_contact = True
		self.save()

		#TODO: Send a message to a primary contact member letting them know they've opted in.
		return pc, created

	# Note, code is shared across patient, doctor, and safety net models, so you should update in all places
	def validate_unique(self, *args, **kwargs):
		super(PatientProfile, self).validate_unique(*args, **kwargs)
		if not self.id:
			if self.__class__.objects.filter(primary_phone_number=self.primary_phone_number, birthday=self.birthday, first_name=self.first_name, last_name=self.last_name).exists():
				raise ValidationError('This patient already exists.')

	def save(self, *args, **kwargs):
		self.validate_unique()
		super(PatientProfile, self).save(*args, **kwargs)

