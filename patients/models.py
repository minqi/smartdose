from django.db import models
from django.contrib.auth.models import User

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
	KILOGRAMS = 'kg'
	POUNDS = 'lb'
	HEIGHT_UNIT_CHOICES = (
		(KILOGRAMS, 'kg'),
		(POUNDS, 'lb'),
	)

	# weight units
	INCHES = 'in'
	METERS = 'm'
	WEIGHT_UNIT_CHOICES = (
		(INCHES, 'in'),
		(METERS, 'm'),
	)

	user = models.OneToOneField(User)
	age = models.PositiveIntegerField(default=0)
	gender = models.CharField(max_length=1,
							  choices=GENDER_CHOICES,
							  default=UNKNOWN)
	height = models.PositiveIntegerField(default=0)
	height_unit = models.CharField(max_length=2,
								   choices=HEIGHT_UNIT_CHOICES,
								   default=POUNDS)
	weight = models.PositiveIntegerField(default=0)
	weight_unit = models.CharField(max_length=2,
									choices=HEIGHT_UNIT_CHOICES,
									default=METERS)
