from django.db import models
from django.db import transaction
from common.models import UserProfile

class DoctorProfileManager(models.Manager):
	"""Manager for performing operations on DoctorProfile records"""
	@transaction.commit_on_success
	def addDoctor(self, phone_number, first_name, last_name, primary_contact,
				address_line1, address_line2, postal_code, city, state_province, country_iso_code,
				email="", password=""):
		user_profile = UserProfile.objects.addUser(phone_number, first_name, last_name, 
										   primary_contact, UserProfile.DOCTOR,
										   address_line1, address_line2, postal_code, 
										   city, state_province, country_iso_code, 
										   email, password)
		doctor_profile = DoctorProfile.objects.create(user_profile=user_profile)
		return doctor_profile

class DoctorProfile(models.Model):
	"""Model for doctor-specific information"""
	#TODO(mgaba): Add doctor specific information: credentials, title, specialty
	user_profile = models.OneToOneField(UserProfile)
	objects = DoctorProfileManager()
