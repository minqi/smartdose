from django.conf import settings
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from common.models import UserProfile, RegistrationProfile
from django.contrib.auth import hashers
import datetime

class SettingsBackend(object):
	def authenticate(self, phone_number=None, email=None, auth_token=None, password=None):
		# Search across emails/phone_numbers and Doctors/patients for user matching authentication parameters       
		user = None
		if email:
			user = DoctorProfile.objects.filter(email=email)
			if not user:
				user = PatientProfile.objects.filter(email=email)
		if not user and phone_number:
			user = DoctorProfile.objects.filter(primary_phone_number=phone_number)
			if not user:
				user = PatientProfile.objects.filter(primary_phone_number=phone_number)
		if not user.exists():
			return None
		else:
			user = user[0]
		# Authenticate user
		if password:
			if user.check_password(password):
				return user
			else:
				return None
		elif auth_token:
			# Check to see if a user is allowed to guess -- They've made fewer than max attempts or they've waited long enough
			now = datetime.datetime.now()
			if user.auth_token_login_attempts < UserProfile.AUTH_TOKEN_MAX_LOGIN_ATTEMPTS or now - user.auth_token_last_login_datetime > datetime.timedelta(minutes=UserProfile.AUTH_TOKEN_WAIT_PERIOD):
				if user.auth_token_last_login_datetime and now - user.auth_token_last_login_datetime > datetime.timedelta(minutes=UserProfile.AUTH_TOKEN_WAIT_PERIOD):
					user.auth_token_login_attempts = 0
				if user.auth_token_active and (now - user.auth_token_datetime < datetime.timedelta(minutes=UserProfile.AUTH_TOKEN_INVALID_TIMEOUT)) and (auth_token == user.auth_token):
						user.auth_token_active = False
						user.save()
						return user
				else:
					user.auth_token_active = False
					user.auth_token_login_attempts += 1
					user.auth_token_last_login_datetime = now
					user.save()
					return None
			else:
				# User has exceeded their number of guesses and needs to wait
				return None
		else:
			return None


	def get_user(self, user_id):
		try:
			return PatientProfile.objects.get(pk=user_id)
		except PatientProfile.DoesNotExist:
			return None
		else:
			try: 
				return DoctorProfile.objects.get(pk=user_id)
			except DoctorProfile.DoesNotExist:
				return None


class RegistrationTokenAuthBackend(object):
	def authenticate(self, regprofile=None, phonenumber=None, email=None):
		if (phonenumber and regprofile.phonenumber_activation_key == RegistrationProfile.ACTIVATED) \
			or (email and regprofile.email_activation_key == RegistrationProfile.ACTIVATED):
			for child_class_name in ('PatientProfile', 'DoctorProfile'):
				try:
					return regprofile.userprofile.__getattribute__(child_class_name.lower())
				except eval(child_class_name).DoesNotExist:
					pass
		return None

	def get_user(self, user_id):
		try:
			return PatientProfile.objects.get(pk=user_id)
		except PatientProfile.DoesNotExist:
			return None
		else:
			try: 
				return DoctorProfile.objects.get(pk=user_id)
			except DoctorProfile.DoesNotExist:
				return None
