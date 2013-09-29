from django.db import models

class UserProfile(models.Model):
	"""Model for extending default User model with some common fields"""
	# user types
	DOCTOR = 'd'
	PATIENT = 'p'
	USER_TYPE_CHOICES = (
		(DOCTOR, 'Doctor'),
		(PATIENT, 'Patient'),
	)

	user = models.OneToOneField(User)
	primary_contact = models.CharField(max_length=32, blank=False)
	user_type = models.CharField(max_length=32, 
								 choices=USER_TYPE_CHOICES,
								 default=PATIENT)
	address = models.ForeignKey(Address)

class Address(models.Model):
	"""Model for addresses"""
	address_line1 = models.CharField(max_length=64)
	address_line2 = models.CharField(max_length=64)
	postal_code = models.CharField(max_length=10)
	city = models.CharField(max_length=64)
	state_province = models.CharField(max_length=64)
	country = models.ForeignKey(Country, to_field="iso_code")

	def __unicode__(self):
		return "%s, %s, %s" % (self.city, self.state_province, str(self.country))

	class Meta:
		verbose_name_plural = "addresses"
		unique_together = ("address_line1", "address_line2", "postal_code",
						   "city", "state_province", "country")

class Country(models.Model):
	"""Model for countries"""
	iso_code = models.CharField(max_length=2, primary_key=True)
	name = models.CharField(max_length=64, blank=False)

	def __unicode__(self):
		return self.name

	class Meta:
		verbose_name_plural = "countries"
		ordering = ["name", "iso_code"]

class Drug(models.Model):
	"""Model for all FDA approved drugs and medication"""
	name = models.CharField(max_length=64, blank=False)
	# NEED TO RESEARCH WHICH FIELDS MUST BE ADDED
