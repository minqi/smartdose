from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from common.models import UserProfile
from common.utilities import sendTextMessageToNumber


class PatientManager(models.Manager):
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

	# status
	ACTIVE	= 'a'
	QUIT 	= 'q'
	STATUS_CHOICES = (
		(ACTIVE, 'a'),
		(QUIT, 'q'),
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
	status = models.CharField(max_length=2,
							  choices=STATUS_CHOICES,
							  default=ACTIVE)

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
		


