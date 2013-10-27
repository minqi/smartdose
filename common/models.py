from django.db import models
from django.db import transaction
from django.contrib.auth.models import User

class Country(models.Model):
	"""Model for mapping country_iso_code to country name"""
	iso_code = models.CharField(max_length=2, primary_key=True)
	name     = models.CharField(max_length=64, blank=False)

	def __unicode__(self):
		return self.name

	class Meta:
		verbose_name_plural = "countries"
		ordering = ["name", "iso_code"]

class UserManager(models.Manager):
	"""Manager for performing operations on UserProfile records"""




# Models that implement UserProfile
# doctors.models.DoctorProfile
# patients.models.PatientProfile
class UserProfile(User):
	"""Model for extending default User model with some common fields"""
	
	# Do not create a table for UserProfile. 
	class Meta:
		abstract = True

	# User specific fields
	primary_phone_number 	= models.CharField(max_length=32, blank=False, null=False)

	# Address fields
	address_line1  		= models.CharField(max_length=64)
	address_line2  		= models.CharField(max_length=64)
	postal_code    		= models.CharField(max_length=10)
	city          		= models.CharField(max_length=64)
	state_province 		= models.CharField(max_length=64)
	country_iso_code	= models.CharField(max_length=2)

	# Manager fields
	objects = UserManager()

class Drug(models.Model):
	"""Model for all FDA approved drugs and medication"""
	name = models.CharField(max_length=64, blank=False)
	# NEED TO RESEARCH WHICH FIELDS MUST BE ADDED
