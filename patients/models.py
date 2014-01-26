from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from common.models import UserProfile, UserProfileManager
from common.utilities import sendTextMessageToNumber
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
		if self.status == PatientProfile.ACTIVE:
			sendTextMessageToNumber(body, self.primary_phone_number)
			return True
		else:
			return False

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



		


