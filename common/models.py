from django.db import models
from django.db import transaction
from django.contrib.auth.models import User

class Country(models.Model):
	"""Model for countries"""
	iso_code = models.CharField(max_length=2, primary_key=True)
	name     = models.CharField(max_length=64, blank=False)

	def __unicode__(self):
		return self.name

	class Meta:
		verbose_name_plural = "countries"
		ordering = ["name", "iso_code"]

class Address(models.Model):
	"""Model for addresses"""
	address_line1  = models.CharField(max_length=64)
	address_line2  = models.CharField(max_length=64)
	postal_code    = models.CharField(max_length=10)
	city           = models.CharField(max_length=64)
	state_province = models.CharField(max_length=64)
	country        = models.ForeignKey(Country, to_field="iso_code")

	def __unicode__(self):
		return "%s, %s, %s" % (self.city, self.state_province, str(self.country))

	class Meta:
		verbose_name_plural = "addresses"
		# Two users can share an address. I'm going to comment this out. We can decide to
		# remove later.
		# unique_together = ("address_line1", "address_line2", "postal_code",
		#				   "city", "state_province", "country")

class UserManager(models.Manager):
	# Do not call directly, instead call corresponding method from a user type. For example,
	# call patients.models.patientprofile.objects.addPatient()
	@transaction.commit_on_success
	def addUser(self, phone_number, first_name, last_name, primary_contact, user_type,
				address_line1, address_line2, postal_code, city, state_province, country_iso_code,
				email="", password=""):
		#TODO(mgaba): Figure out where to put phone_number validation 
		#TODO(mgaba): Figure out what happens when something fails validation
		#TODO(mgaba): Add logging for when a transaction fails
		user = User.objects.create(username=phone_number, 
								  first_name=first_name, last_name=last_name,
								  email=email, password=password)
		country = Country.objects.get(iso_code=country_iso_code)
		address = Address.objects.create(address_line1=address_line1, address_line2=address_line2,
										postal_code=postal_code, city=city,
										state_province=state_province, country=country)
		user_profile = UserProfile.objects.create(user=user, primary_contact=phone_number, 
												 user_type=user_type, address=address)
		return user_profile

class UserProfile(models.Model):
	"""Model for extending default User model with some common fields"""
	# user types
	DOCTOR  = 'd'
	PATIENT = 'p'
	USER_TYPE_CHOICES = (
		(DOCTOR, 'Doctor'),
		(PATIENT, 'Patient'),
	)

	user            = models.OneToOneField(User)
	#What is primary_contact?
	primary_contact = models.CharField(max_length=32, blank=False)
	user_type       = models.CharField(max_length=32, 
								 choices=USER_TYPE_CHOICES,
								 default=PATIENT)
	address = models.ForeignKey(Address)
	objects = UserManager()

class Drug(models.Model):
	"""Model for all FDA approved drugs and medication"""
	name = models.CharField(max_length=64, blank=False)
	# NEED TO RESEARCH WHICH FIELDS MUST BE ADDED
