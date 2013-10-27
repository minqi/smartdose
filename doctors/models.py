from django.db import models
from django.db import transaction
from common.models import UserProfile

class DoctorProfileManager(models.Manager):
	"""Manager for performing operations on DoctorProfile records"""


class DoctorProfile(UserProfile):
	"""Model for doctor-specific information"""
	# Doctor specific fields
	#TODO(mgaba): Add doctor specific information: credentials, title, specialty


	# Manager fields
	objects = DoctorProfileManager()
