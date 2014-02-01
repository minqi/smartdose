from django.contrib.auth.models import User
from common.models import UserProfile
from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save)
def my_callback(sender, **kwargs):
	if not issubclass(sender, UserProfile):
		return
	obj = kwargs['instance'] 
	if not obj.id:
   		username = UserProfile.get_unique_username(obj)
   		obj.username = username