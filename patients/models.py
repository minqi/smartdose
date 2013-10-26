from django.db import models
from django.db import transaction
from common.models import UserProfile


class PatientManager(models.Manager):
	"""Manager for performing operations on PatientProfile records"""
	@transaction.commit_on_success
	def addPatient(self, phone_number, first_name, last_name, primary_contact,
				address_line1, address_line2, postal_code, city, state_province, country_iso_code,
				gender, age=0, height=0, height_unit='in', weight=0, weight_unit='lb',
				email="", password=""):
		#TODO(mgaba): Figure out where to put phone_number validation 
		#TODO(mgaba): Figure out what happens when something fails validation
		#TODO(mgaba): Add logging for when a transaction fails
		user_profile = UserProfile.objects.addUser(phone_number, first_name, last_name, 
										   primary_contact, 'p', #'p' is the user_type for patient
										   address_line1, address_line2, postal_code, 
										   city, state_province, country_iso_code, 
										   email, password)
		patient_profile = PatientProfile.objects.create(user_profile=user_profile, age=age,
														gender=gender, 
														height=height, height_unit=height_unit,
														weight=weight, weight_unit=weight_unit)
		return patient_profile

class PatientProfile(models.Model):
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

	user_profile = models.OneToOneField(UserProfile)
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
	objects = PatientManager()
