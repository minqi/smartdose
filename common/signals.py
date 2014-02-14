from django.contrib.auth.models import User
from common.models import UserProfile
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from reminders.models import ReminderTime
from django.db.models.signals import pre_save
from django.dispatch import receiver
from datetime import datetime
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configs.dev.settings")

@receiver(pre_save)
def setup_new_userprofile(sender, **kwargs):
	if not issubclass(sender, UserProfile):
		return
	obj = kwargs['instance'] 
	if not obj.id:
			# Generate a unique username when creating new 
			# UserProfile instances
			username = UserProfile.get_unique_username(obj)
			obj.username = username

			if issubclass(sender, PatientProfile):
				# Make sure if there's no phone number there is a primary contact
				if obj.primary_phone_number is None and obj.has_primary_contact is False:
					raise ValidationError

				# Schedule a welcome message to new patients
				if isinstance(sender, PatientProfile):
					ReminderTime.objects.create_welcome_notification(to=sender)






