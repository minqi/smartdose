from django.contrib.auth.models import User
from common.models import UserProfile
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from reminders.models import ReminderTime
from django.db.models.signals import pre_save
from django.dispatch import receiver
from datetime import datetime


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

   		# Schedule a welcome message to new patients
   		if isinstance(sender, PatientProfile):
   			ReminderTime.objects.create_welcome_notification(to=sender)






