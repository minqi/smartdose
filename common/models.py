from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver

class Country(models.Model):
	"""Model for mapping country_iso_code to country name"""
	iso_code = models.CharField(max_length=2, primary_key=True)
	name     = models.CharField(max_length=64, blank=False)

	def __unicode__(self):
		return self.name

	class Meta:
		verbose_name_plural = "countries"
		ordering = ["name", "iso_code"]

class UserProfileManager(models.Manager):
	"""Manager for performing operations on UserProfile records"""
	
# Models that implement UserProfile
# doctors.models.DoctorProfile
# patients.models.PatientProfile
# patients.models.SafetyNetMemberProfile
class UserProfile(User):
	"""Model for extending default User model with some common fields"""
	
	class Meta:
		# Do not create a table for UserProfile. 
		abstract = True

	# status
	NEW     = 'n'
	ACTIVE	= 'a'
	QUIT 	= 'q'
	STATUS_CHOICES = (
		(NEW,    'n'),
		(ACTIVE, 'a'),
		(QUIT,   'q'),
	)

	# by default, new UserProfile instances are 'NEW'
	status = models.CharField(max_length=2,
						  choices=STATUS_CHOICES,
						  default=NEW)

	# User specific fields
	primary_phone_number 	= models.CharField(max_length=32, blank=False, null=False)
	birthday = models.DateField(blank=False, null=False)

	# Address fields
	address_line1  		= models.CharField(max_length=64)
	address_line2  		= models.CharField(max_length=64)
	postal_code    		= models.CharField(max_length=10)
	city          		= models.CharField(max_length=64)
	state_province 		= models.CharField(max_length=64)
	country_iso_code	= models.CharField(max_length=2)
	objects				= UserProfileManager()

	def __unicode__(self):
		return self.primary_phone_number

	@staticmethod
	def get_unique_username(obj):
		original_username = str(hash(obj.first_name + obj.last_name + obj.primary_phone_number + str(obj.birthday)))
		username = original_username
		for i in range(0, 10000): #aribtrarily choose max range to be 10000 on the assumption that there will not be more than 10,000 collisions.
			try:
				User.objects.get(username=username)
				username = original_username+str(i) # If there's a collision, add another integeter and begin incrementing
			except User.DoesNotExist:
				return username
		raise UsernameCollisionError


class Drug(models.Model):
	"""Model for all FDA approved drugs and medication"""
	name = models.CharField(max_length=64, blank=False)
	# AI(minqi): add appropriate fields



