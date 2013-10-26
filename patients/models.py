from django.db import models
from common.models import UserProfile

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

	user = models.OneToOneField(UserProfile)
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
