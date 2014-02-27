import datetime

from django.db import models
from django.db import transaction
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth import hashers
from django.core.exceptions import ValidationError
from django.dispatch import receiver

from common.utilities import convert_to_e164

class Country(models.Model):
	"""Model for mapping country_iso_code to country name"""
	iso_code = models.CharField(max_length=2, primary_key=True)
	name     = models.CharField(max_length=64, blank=False)

	def __unicode__(self):
		return self.name

	class Meta:
		verbose_name_plural = "countries"
		ordering = ["name", "iso_code"]

class UserProfileManager(BaseUserManager):
	"""Manager for performing operations on UserProfile records"""
	def create_user(self, first_name, last_name, password=None):
		if not first_name or not last_name:
			raise ValueError('Users must have a first and last name')

		user = self.model(first_name=first_name, last_name=last_name)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, first_name, last_name, password=None):
		user = self.create_user(first_name, last_name, password)
		user.is_admin = True
		user.save(using=self._db)
		return user

# Models that implement UserProfile
# doctors.models.DoctorProfile
# patients.models.PatientProfile
class UserProfile(AbstractBaseUser):
	"""Model for implementing custom base User model"""
	
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
	username 				= models.CharField(max_length=40, unique=True)
	first_name				= models.CharField(max_length=40, null=False, blank=False)
	last_name				= models.CharField(max_length=40, null=False, blank=False)
	full_name               = models.CharField(max_length=80, null=False, blank=False)
	birthday 				= models.DateField(blank=True, null=True)
	is_admin				= models.BooleanField(default=False)
	join_datetime			= models.DateTimeField(auto_now_add=True)

	# Formula for computing probability that at least one of N users accounts with password of CHAR_SPACE are compromised in T minutes. 
	# 1 - ((1-1/CHAR_SPACE^AUTH_TOKEN_LENGTH)^(AUTH_TOKEN_MAX_LOGIN_ATTEMPTS*T/AUTH_TOKEN_WAIT_PERIOD))^N
	# Substituting T=60, N=10000, CHAR_SPACE = 10, AUTH_TOKEN_LENGTH = 4, AUTH_TOKEN_MAX_LOGIN_ATTEMPTS = 2, AUTH_TOKEN_WAIT_PERIOD = 10
	# 1 - ((1-1/10^4)^(2*60/10))^10000 = .99994
	# Substituting, T=60, N=10000, CHAR_SPACE=31, AUTH_TOKEN_LENGTH = 4, AUTH_TOKEN_MAX_LOGIN_ATTEMPTS = 2, AUTH_TOKEN_WAIT_PERIOD = 10
	# 1 - ((1-1/31^4)^(2*60/10))^10000 = .122
	# Substituting T=60, N=10000, CHAR_SPACE=31, AUTH_TOKEN_LENGTH = 5, AUTH_TOKEN_MAX_LOGIN_ATTEMPTS = 2, AUTH_TOKEN_WAIT_PERIOD = 10
	# 1 - ((1-1/31^5)^(2*60/10))^10000 = .0042
	# Substituting T=60*24, N=10000, CHAR_SPACE=31, AUTH_TOKEN_LENGTH=5, AUTH_TOKEN_MAX_LOGIN_ATTEMPTS = 2, AUTH_TOKEN_WAIT_PERIOD = 10
	# 1 - ((1-1/31^5)^(2*60*24/10))^10000 = .0957

	AUTH_TOKEN_LENGTH				= 5
	AUTH_TOKEN_MAX_LOGIN_ATTEMPTS 	= 2
	AUTH_TOKEN_WAIT_PERIOD			= 10 # minutes -- The time a user must wait after number of guesses exceed AUTH_TOKEN_MAX_LOGIN_ATTEMPTS
	AUTH_TOKEN_INVALID_TIMEOUT		= 2 # minutes -- The time it takes from when an auth token is issued to when it is no longer useable
	auth_token						= models.CharField(max_length=128)
	auth_token_active				= models.BooleanField(default=False)
	auth_token_datetime				= models.DateTimeField(null=True, blank=True)
	auth_token_login_attempts 		= models.IntegerField(default=0)
	auth_token_last_login_datetime 	= models.DateTimeField(null=True, blank=True)

	has_password			= models.BooleanField(default=False)

	USERNAME_FIELD = 'username'
	REQUIRED_FIELDS = ['first_name', 'last_name']

	# Address fields
	address_line1  		= models.CharField(max_length=64)
	address_line2  		= models.CharField(max_length=64)
	postal_code    		= models.CharField(max_length=10)
	city          		= models.CharField(max_length=64)
	state_province 		= models.CharField(max_length=64)
	country_iso_code	= models.CharField(max_length=2)
	objects				= UserProfileManager()

	def get_full_name(self):
		return self.first_name + " " + self.last_name

	def get_short_name(self):
		return self.first_name

	def __unicode__(self):
		return self.get_full_name()

	def __init__(self, *args, **kwargs):
		super(UserProfile, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.username = self.get_unique_username(self)
		self.full_name = self.get_full_name()
		self.primary_phone_number = convert_to_e164(self.primary_phone_number)

	def save(self, *args, **kwargs):
		if len(self.first_name) == 0:
			raise ValidationError('UserProfile must have a first name')
		super(UserProfile, self).save(*args, **kwargs)

	@staticmethod
	def get_unique_username(obj):
		original_username = str(hash(obj.first_name + obj.last_name + str(datetime.datetime.now())))
		username = original_username
		for i in range(0, 10000): #aribtrarily choose max range to be 10000 on the assumption that there will not be more than 10,000 collisions.
			try:
				UserProfile.objects.get(username=username)
			except UserProfile.DoesNotExist:
				return username
			else:
				username = original_username+str(i) # If there's a collision, add another integeter and begin incrementing
		raise UsernameCollisionError

	def generate_auth_token(self):
		self.auth_token_datetime = datetime.datetime.now()
		self.auth_token_active = True
		self.auth_token = UserProfile.objects.make_random_password(length=UserProfile.AUTH_TOKEN_LENGTH, allowed_chars='abcdefghjkmnpqrstuvwxyz23456789')
		self.save()

class Drug(models.Model):
	"""Model for all FDA approved drugs and medication"""
	name = models.CharField(max_length=64, blank=False, unique=True)
	# AI(minqi): add appropriate fields

	def __init__(self, *args, **kwargs):
		super(Drug, self).__init__(*args, **kwargs)
		if self.id:
			return
		self.name = self.name.lower()
