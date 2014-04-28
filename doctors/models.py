from django.db import models
from django.db import transaction
from common.models import UserProfile, UserProfileManager
from django.core.exceptions import ValidationError

from common.utilities import convert_to_e164

class DoctorProfileManager(UserProfileManager):
	"""Manager for performing operations on DoctorProfile records"""

class DoctorProfile(UserProfile):
	"""Model for doctor-specific information"""
	# Doctor specific fields

	# Manager fields
	objects = DoctorProfileManager()

# ************ ENCRYPTION START ************
	primary_phone_number 	= models.CharField(max_length=32, blank=True, null=True, unique=True)
	email 					= models.EmailField(blank=False, null=False, unique=True)
# ************ ENCRYPTION END **************

	def __init__(self, *args, **kwargs):
		super(DoctorProfile, self).__init__(*args, **kwargs)
		if self.id:
			return

		if self.primary_phone_number:	
			self.primary_phone_number = convert_to_e164(self.primary_phone_number)

	# Note, code is shared across patient, doctor, and safety net models, so you should update in all places
	def validate_unique(self, *args, **kwargs):
		super(DoctorProfile, self).validate_unique(*args, **kwargs)
		if not self.id:
			if self.__class__.objects.filter(
				primary_phone_number=self.primary_phone_number, birthday=self.birthday, 
				first_name__iexact=self.first_name, last_name__iexact=self.last_name).exists():
				raise ValidationError('This patient already exists.')

	def save(self, *args, **kwargs):
		self.validate_unique()
		super(DoctorProfile, self).save(*args, **kwargs)