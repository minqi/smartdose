from django.db import models
from django.db import transaction
from common.models import UserProfile, UserProfileManager
from django.core.exceptions import ValidationError

class DoctorProfileManager(UserProfileManager):
	"""Manager for performing operations on DoctorProfile records"""


class DoctorProfile(UserProfile):
	"""Model for doctor-specific information"""
	# Doctor specific fields
	#TODO(mgaba): Add doctor specific information: credentials, title, specialty

	# Manager fields
	objects = DoctorProfileManager()

	# Note, code is shared across patient, doctor, and safety net models, so you should update in all places
	def validate_unique(self, *args, **kwargs):
		super(DoctorProfile, self).validate_unique(*args, **kwargs)
		if not self.id:
			if self.__class__.objects.filter(primary_phone_number=self.primary_phone_number, birthday=self.birthday, first_name=self.first_name, last_name=self.last_name).exists():
				raise ValidationError('This patient already exists.')

	def save(self, *args, **kwargs):
		self.validate_unique()
		super(DoctorProfile, self).save(*args, **kwargs)