from __future__ import absolute_import

from django.template.loader import render_to_string
from django.db.models import Q

from common.models import UserProfile, RegistrationProfile
from common.utilities import sendTextMessageToNumber
from patients.models import PatientProfile

from guardian.shortcuts import assign_perm, remove_perm
from celery import shared_task


def regprofile_activate_user_phonenumber(regprofile, activation_key):
	if regprofile.phonenumber_activation_key != activation_key:
		return False
	elif not regprofile.phonenumber_activation_key_expired():
		# send email confirmation
		userprofile = regprofile.userprofile
		userprofile.is_active = True
		userprofile.save()
		regprofile.phonenumber_activation_key = RegistrationProfile.ACTIVATED
		regprofile.save()
		return userprofile
	return False


def regprofile_activate_user_email(regprofile, activation_key):
	if regprofile.email_activation_key != activation_key:
		return False
	elif not regprofile.email_activation_key_expired():
		# send email confirmation
		userprofile = regprofile.userprofile
		userprofile.is_active = True
		userprofile.save()
		regprofile.email_activation_key = RegistrationProfile.ACTIVATED
		regprofile.save()
		return userprofile
	return False


def create_inactive_patientprofile(
	email, full_name, primary_phone_number, password):
	"""
	Create a new inactive UserProfile object and associated RegistrationProfile object.
	Also sends a SMS to user to verify user's phone number and email to verify user's
	email.
	"""

	patient = PatientProfile.objects.get_or_create(
		primary_phone_number=primary_phone_number,
		defaults={
			'full_name':full_name,
			'email':email,
			'is_active':False,
			'enroller':None
		}
	)[0]

	patient.num_caregivers += 1
	assign_perm('manage_patientprofile', patient, patient)
	patient.set_password(password)
	patient.save()

	regprofile = create_regprofile_from_userprofile(patient)

	# send verification SMS
	sms_content = render_to_string(
		'messages/verify_mobile.txt', 
		{'otp':regprofile.phonenumber_activation_key})
	sendTextMessageToNumber(to=primary_phone_number, body=sms_content)

	# send verification email
	if email:
		# send email
		pass

	return (regprofile, patient)


def create_regprofile_from_userprofile(userprofile):
	return RegistrationProfile.objects.create(
		userprofile=userprofile)


@shared_task()
def delete_expired_regprofiles():
	for regprofile in RegistrationProfile.objects.all():
		if regprofile.phonenumber_activation_key_expired() \
			or regprofile.email_activation_key_expired():
			try:
				userprofile = regprofile.userprofile
				if not userprofile.is_active:
					userprofile.delete()
					regprofile.delete()
			except UserProfile.DoesNotExist:
				regprofile.delete()
