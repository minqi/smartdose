import datetime

from django.db import models
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

from common.utilities import InterpersonalRelationship, convert_to_e164
from common.models import UserProfile, UserProfileManager


class SafetyNetRelationship(models.Model):
	# The patient
	source_patient = models.ForeignKey('PatientProfile', related_name='target_patient_safety_net')
	# The safety net member/primary contact
	target_patient = models.ForeignKey('PatientProfile', related_name='source_patient_safety_nets')

	# what the patient calls this safety net contact
	source_to_target_relationship = \
		models.CharField(null=False, blank=False, max_length=20, 
			choices=InterpersonalRelationship.RELATIONSHIP_CHOICES)

	target_to_source_relationship = \
		models.CharField(null=False, blank=False, max_length=20, 
			choices=InterpersonalRelationship.RELATIONSHIP_CHOICES)

	receives_all_reminders = models.BooleanField(default=False)
	opt_out	               = models.BooleanField(default=False)

	class Meta:
		unique_together = (('source_patient', 'target_patient'),)


class PatientManager(UserProfileManager):
	"""Manager for performing operations on PatientProfile records"""
	pass


class PatientProfile(UserProfile):
	"""Model for patient-specific information"""
	# genders
	MALE = 'm'
	FEMALE = 'f'
	UNKNOWN = ''
	GENDER_CHOICES = (
		(MALE, 'male'),
		(FEMALE, 'female'),
		(UNKNOWN, 'unknown'),
	)

	# height units
	INCHES = 'in'
	METERS = 'm'
	HEIGHT_UNIT_CHOICES = (
		(INCHES, 'inches'),
		(METERS, 'meters'),
	)

	# weight units
	KILOGRAMS = 'kg'
	POUNDS = 'lb'
	WEIGHT_UNIT_CHOICES = (
		(KILOGRAMS, 'kilograms'),
		(POUNDS, 'pounds'),
	)

	# Patient specific fields
	mrn			= models.PositiveIntegerField(default=0) 
	age 		= models.PositiveIntegerField(default=0)
	gender 		= models.CharField(null=False, blank=False,
	                            max_length=1,
							    choices=GENDER_CHOICES,
							    default=UNKNOWN)
	height 		= models.PositiveIntegerField(default=0)
	height_unit = models.CharField(max_length=2,
								   choices=HEIGHT_UNIT_CHOICES,
								   default=INCHES)
	weight 		= models.PositiveIntegerField(default=0)
	weight_unit = models.CharField(max_length=2,
									choices=HEIGHT_UNIT_CHOICES,
									default=POUNDS)

	# If enroller is None it means the patient enrolled themselves
	enroller    = models.ForeignKey(UserProfile, 
		default=None, related_name='enroller', null=True, blank=True)
	
	safety_net_contacts 	= models.ManyToManyField('self', 
		through='SafetyNetRelationship', symmetrical=False, related_name='safety_net')

	# need to have this separately in patient and doctor so patient/doctor accounts can 
	# use same phone number
	primary_phone_number 	= models.CharField(max_length=32, blank=True, null=True, unique=True)
	email 					= models.EmailField(blank=True, null=True, unique=True)
	
	# number of people with access to the patient's profile
	num_caregivers			= models.IntegerField(default=0)

	# someone who receives messages on this patient's behalf
	primary_contact         = models.ForeignKey('self', null=True)

	# The time from when a user requests to quit that they can confirm the quit to unenroll
	QUIT_RESPONSE_WINDOW    = 60 #minutes
	quit_request_datetime   = models.DateTimeField(blank=True, null=True)

	# Manager fields
	objects = PatientManager()

	class Meta:
		ordering = ['full_name']
		permissions = (
			('view_patientprofile', 'Manage patient profile'),
			('manage_patientprofile', 'Manage patient profile'),
		)

	def __init__(self, *args, **kwargs):
		super(PatientProfile, self).__init__(*args, **kwargs)
		if self.id:
			return
		valid = True

		if self.primary_phone_number:
			self.primary_phone_number = convert_to_e164(self.primary_phone_number)
		
		if not self.primary_phone_number and not self.primary_contact:
			valid = False
		if not valid:
			raise ValidationError('Must provide either a primary phone number or primary contact')

	def quit(self):
		self.status = PatientProfile.QUIT
		self.record_quit_request()
		self.save()

	def pause(self):
		self.status = PatientProfile.QUIT
		self.save()

	def resume(self):
		self.status = PatientProfile.ACTIVE
		self.save()

	def add_safety_net_contact(self, target_patient, relationship, 
		receives_all_reminders=False):
		reverse_relationship = \
			InterpersonalRelationship.lookup_backwards_relationship(relationship, self)
		defaults = {
			'source_to_target_relationship':relationship, 
			'target_to_source_relationship':reverse_relationship,
			'receives_all_reminders':receives_all_reminders}
		try:
			sn_relation = SafetyNetRelationship.objects.get(
				source_patient=self, target_patient=target_patient)
		except SafetyNetRelationship.DoesNotExist:
			defaults.update({'source_patient':self, 'target_patient':target_patient})
			sn_relation = SafetyNetRelationship(**defaults)
			sn_relation.save()
			
		for key, value in defaults.iteritems():
			setattr(sn_relation, key, value)
		sn_relation.save()

	def save(self, *args, **kwargs):
		self.validate_unique()
		super(PatientProfile, self).save(*args, **kwargs)

	def did_request_quit_within_quit_response_window(self):
		""" 
		Returns True if the patient initiated a quit message 
		more recently than QUIT_RESPONSE_WINDOW
		"""
		time_diff = datetime.datetime.now() - \
			datetime.timedelta(minutes=PatientProfile.QUIT_RESPONSE_WINDOW)
		if self.quit_request_datetime and self.quit_request_datetime > time_diff:
			return True
		else:
			return False

	def record_quit_request(self):
		self.quit_request_datetime = datetime.datetime.now()
		self.save()

	def did_quit(self):
		if self.status == PatientProfile.QUIT:
			return True
		else:
			return False


