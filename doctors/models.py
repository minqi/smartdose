from django.db import models
from common.models import UserProfile

# Create your models here.
class DoctorProfile(models.Model):
	"""Model for doctor-specific information"""
	user_profile = models.OneToOneField(UserProfile)
