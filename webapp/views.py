import datetime, json

from django import forms
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.context_processors import csrf
from django.core.exceptions import ValidationError
from django.core.urlresolvers import resolve
from django.db.models import Q
from django.template.loader import render_to_string
from localflavor.us.forms import USPhoneNumberField
from itertools import groupby

from common.utilities import is_integer, next_weekday, convert_to_e164, sendTextMessageToNumber
from common.registration_services import create_inactive_patientprofile, \
	regprofile_activate_user_phonenumber
from common.models import RegistrationProfile, Drug
from patients.models import PatientProfile, SafetyNetRelationship
from doctors.models import DoctorProfile
from reminders.models import Notification, Prescription, Message

from guardian.shortcuts import assign_perm, remove_perm, get_objects_for_user
from guardian.models import UserObjectPermission, GroupObjectPermission
from lockdown.decorators import lockdown


def landing_page(request):
	return HttpResponse(content="STAY TUNED", content_type="text/plain")


class UserLoginForm(forms.Form):
	primary_phone_number = USPhoneNumberField()
	password = forms.CharField(widget=forms.PasswordInput())

	def clean_primary_phone_number(self):
		primary_phone_number = self.cleaned_data['primary_phone_number'].strip()
		return convert_to_e164(primary_phone_number)


class UserRegistrationForm(forms.Form):
	full_name = forms.CharField(max_length=80) 
	email = forms.EmailField()
	primary_phone_number = USPhoneNumberField()
	password1 = forms.CharField(widget=forms.PasswordInput())
	password2 = forms.CharField(widget=forms.PasswordInput())

	def clean_full_name(self):
		full_name = self.cleaned_data['full_name'].strip()
		if len(full_name) == 0:
			raise ValidationError('No full name provided')
		return full_name

	def clean_primary_phone_number(self):
		primary_phone_number = self.cleaned_data['primary_phone_number'].strip()
		return convert_to_e164(primary_phone_number)

	def clean(self):
		cleaned_data = super(UserRegistrationForm, self).clean()
		password1 = self.cleaned_data.get('password1')
		password2 = self.cleaned_data.get('password2')

		if password1 and password1 != password2:
			raise forms.ValidationError("Passwords don't match")

		return self.cleaned_data


class VerifyMobileForm(forms.Form):
	otp = forms.CharField(min_length=5, max_length=5)

	def clean_otp(self):
		otp = self.cleaned_data['otp'].strip().lower()
		return otp


class CreatePatientForm(forms.Form):
    full_name = forms.CharField(max_length=80)
    primary_phone_number = USPhoneNumberField()

    def clean_full_name(self):
    	full_name = self.cleaned_data['full_name'].strip()
    	if len(full_name) == 0:
    		raise ValidationError('No full name provided')
    	return full_name

    def clean_primary_phone_number(self):
    	primary_phone_number = self.cleaned_data['primary_phone_number'].strip()
    	return convert_to_e164(primary_phone_number)


class UpdatePatientForm(CreatePatientForm):
	p_id = forms.IntegerField()

	def clean_p_id(self):
		p_id = self.cleaned_data['p_id']
		if not PatientProfile.objects.filter(id=p_id).exists():
			raise ValidationError('Patient does not exist')
		return p_id


class DeletePatientForm(forms.Form):
	p_id = forms.IntegerField()

	def clean_p_id(self):
		p_id = self.cleaned_data['p_id']
		if not PatientProfile.objects.filter(id=p_id).exists():
			raise ValidationError('Patient does not exist')
		return p_id


class NewReminderForm(forms.Form):
	p_id = forms.IntegerField()
	drug_name = forms.CharField(max_length=80)
	reminder_time = forms.TimeField()
	mon = forms.BooleanField(required=False)
	tue = forms.BooleanField(required=False)
	wed = forms.BooleanField(required=False)
	thu = forms.BooleanField(required=False)
	fri = forms.BooleanField(required=False)
	sat = forms.BooleanField(required=False)
	sun = forms.BooleanField(required=False)
	send_refill_reminder = forms.BooleanField(required=False)

	def clean_p_id(self):
		p_id = self.cleaned_data['p_id']
		if not PatientProfile.objects.filter(id=p_id).exists():
			raise ValidationError('Patient does not exist')
		return p_id

	def clean_drug_name(self):
		drug_name = self.cleaned_data['drug_name']
		drug_name = drug_name.lower().strip()
		if len(drug_name) == 0:
			raise ValidationError('No drug name provided')
		return drug_name

	def clean(self):
		cleaned_data = super(NewReminderForm, self).clean()
		active_days_of_week = (
			self.cleaned_data.get('mon', False),
			self.cleaned_data.get('tue', False),
			self.cleaned_data.get('wed', False),
			self.cleaned_data.get('thu', False),
			self.cleaned_data.get('fri', False),
			self.cleaned_data.get('sat', False),
			self.cleaned_data.get('sun', False),
		)
		self.cleaned_data['active_days_of_week'] = active_days_of_week
		return self.cleaned_data


class DeleteReminderForm(forms.Form):
	p_id = forms.IntegerField()
	drug_name = forms.CharField(max_length=80)
	reminder_time = forms.TimeField(input_formats=('%I:%M %p',))

	def clean_drug_name(self):
		drug_name = self.cleaned_data['drug_name']
		drug_name = drug_name.lower().strip()
		if len(drug_name) == 0:
			raise ValidationError('No drug name provided')
		return drug_name

	def clean(self):
		cleaned_data = super(DeleteReminderForm, self).clean()
		
		p_id = self.cleaned_data.get('p_id')
		patient = PatientProfile.objects.filter(id=p_id)
		if not patient.exists():
			raise ValidationError('Patient does not exist')
		else:
			patient = patient[0]
		drug_name = self.cleaned_data.get('drug_name')

		if not Prescription.objects.filter(patient=patient, drug__name=drug_name):
			raise ValidationError('Reminder does not exist')

		reminders = Notification.objects.filter(
			to=patient, prescription__drug__name__iexact=drug_name, 
			type=Notification.MEDICATION)
		reminders_for_deletion = []
		reminder_time = self.cleaned_data.get('reminder_time')
		for r in reminders:
			if r.send_datetime.time() == reminder_time:
				reminders_for_deletion.append(r)
		if len(reminders_for_deletion) == 0:
			raise ValidationError('Reminder does not exist')

		self.cleaned_data['reminders_for_deletion'] = reminders_for_deletion
		self.cleaned_data['all_deleted'] = False
		if len(reminders_for_deletion) == len(reminders):
			self.cleaned_data['all_deleted'] = True
		return self.cleaned_data


class CreateSafetyNetContactForm(forms.Form):
	p_id = forms.IntegerField()
	full_name = forms.CharField(max_length=80)
	relationship = forms.CharField(max_length=40)
	primary_phone_number = USPhoneNumberField()
	receives_all_reminders = forms.BooleanField(required=False)

	def clean_p_id(self):
		p_id = self.cleaned_data['p_id']
		if not PatientProfile.objects.filter(id=p_id).exists():
			raise ValidationError('Patient does not exist')
		return p_id

	def clean_full_name(self):
		full_name = self.cleaned_data['full_name'].strip()
		if len(full_name) == 0:
			raise ValidationError('No full name provided')
		return full_name

	def clean_primary_phone_number(self):
		primary_phone_number = self.cleaned_data['primary_phone_number'].strip()
		return convert_to_e164(primary_phone_number)


class DeleteSafetyNetContactForm(forms.Form):
	p_id = forms.IntegerField()
	target_p_id = forms.IntegerField()

	def clean_p_id(self):
		p_id = self.cleaned_data['p_id']
		if not PatientProfile.objects.filter(id=p_id).exists():
			raise ValidationError('Patient does not exist')
		return p_id


def user_registration(request):
	c = RequestContext(request)
	if request.method == 'GET':
		return render_to_response('fishfood/user_registration.html', c)

	if request.method == 'POST':
		form = UserRegistrationForm(request.POST)
		if form.is_valid():
			full_name = form.cleaned_data['full_name']
			email = form.cleaned_data['email']
			primary_phone_number = form.cleaned_data['primary_phone_number']
			password = form.cleaned_data['password1']

			if PatientProfile.objects.filter(email=email).exists():
				return HttpResponseBadRequest('This email is already in use')

			if PatientProfile.objects.filter(primary_phone_number=primary_phone_number).exists():
				return HttpResponseBadRequest('This number is already in use')

			(reg_profile, patient) = create_inactive_patientprofile(
				full_name=full_name, 
				email=email, 
				primary_phone_number=primary_phone_number,
				password=password)

			# send user to number verification page
			response = render_to_response('fishfood/verify_mobile.html', c)

			# set cookie
			response.set_cookie('reg_id', reg_profile.id)
			return response

	return HttpResponseBadRequest('Something went wrong.')


def verify_mobile(request):
	c = RequestContext(request)

	if request.method == 'POST':
		form = VerifyMobileForm(request.POST)
		if form.is_valid() and request.COOKIES.has_key('reg_id'):
			reg_id = request.COOKIES['reg_id']
			regprofile = RegistrationProfile.objects.get(id=reg_id)

			# get otp
			otp = form.cleaned_data['otp']
			if regprofile_activate_user_phonenumber(regprofile, otp):
				patient = authenticate(regprofile=regprofile, phonenumber=True)
				login(request, patient)
				patient.status = PatientProfile.ACTIVE
				patient.save()
				return redirect('/fishfood/')

			response = HttpResponse('Unauthorized')
			response.status_code = 401
			return response

	return HttpResponseBadRequest('Something went wrong')


def resend_mobile_verification_code(request):
	c = RequestContext(request)

	if request.method == 'GET':
		reg_id = request.COOKIES['reg_id']
		regprofile = RegistrationProfile.objects.get(id=reg_id)
		regprofile.set_phonenumber_activation_key()
		regprofile.save()

		c['otp'] = regprofile.phonenumber_activation_key
		body = render_to_string('messages/verify_mobile.html', c)
		sendTextMessageToNumber(
			to=regprofile.userprofile.primary_phone_number,
			body=body)
		return HttpResponse('')

	return HttpResponseBadRequest('Something went wrong')


# @lockdown
def user_login(request):
	c = RequestContext(request)
	if request.method == 'GET':
		return render_to_response('fishfood/user_login.html', c)

	if request.method == 'POST':
		form = UserLoginForm(request.POST)
		if form.is_valid():
			primary_phone_number = form.cleaned_data['primary_phone_number']
			password = form.cleaned_data['password']
			user = authenticate(phone_number=primary_phone_number, password=password)
			if user is not None:
				if user.is_active:
					login(request, user)
					return redirect('/fishfood/')
				else:
					HttpResponseBadRequest('This user account is disabled.')
		else:
			HttpResponseBadRequest('Login is invalid.')
	return HttpResponseBadRequest('Something went wrong.')


@login_required
def user_logout(request):
	c = RequestContext(request)
	if request.method == 'POST':
		logout(request)

		# need to delete cookie here
		return redirect('/fishfood/')

	return HttpResponseBadRequest('')


@login_required
def fishfood(request):
	if request.method == 'GET':
		c = RequestContext(request)
		user = request.user

		results = get_objects_for_user(user, 'patients.manage_patient_profile')
		# results = PatientProfile.objects.all()
		results = results.filter(
			Q(status=PatientProfile.ACTIVE) | Q(status=PatientProfile.NEW)).order_by('full_name')

		c['patient_search_results_list'] = results
		return render_to_response('fishfood/fishfood.html', c)
	return HttpResponseBadRequest('Something went wrong.')


@login_required
def dashboard(request):
	pass


# create new patient
@login_required
def create_patient(request, *args, **kwargs):
	# validate form
	if request.POST:
		form = CreatePatientForm(request.POST)
		if form.is_valid():
			full_name = form.cleaned_data['full_name']
			primary_phone_number = form.cleaned_data['primary_phone_number']

			# does and actively managed patient with this number exist?
			q = PatientProfile.objects.filter(
				primary_phone_number=primary_phone_number, 
				num_caregivers__gt=0)
			
			request_user_patient = PatientProfile.objects.get(pk=request.user.pk)
			if q.exists():
				# is the patient the request user?
				if request.user.primary_phone_number == primary_phone_number:
					if request.user.full_name == full_name:
						return HttpResponseBadRequest('You are already in the system.')
						# add request user as primary safety net for new patient
					else:
						patient = PatientProfile.objects.create(
							full_name=full_name, primary_contact=request_user_patient)
				else:
					# TODO(minqi): send request to become caregiver
					return HttpResponseBadRequest('This user is already under management.')	
			else:
				# create patient profile
				(patient, created) = PatientProfile.objects.get_or_create(
					primary_phone_number=primary_phone_number,
					defaults={'full_name':full_name}
				)
				patient.full_name = full_name

			# add permissions
			assign_perm('view_patient_profile', request.user, patient)
			assign_perm('manage_patient_profile', request.user, patient)

			# add request user as a safety net contact
			patient.add_safety_net_contact(
				target_patient=request_user_patient, relationship='other',
				receives_all_reminders=True)

			patient.status = PatientProfile.NEW
			patient.num_caregivers += 1
			Notification.objects.create_consumer_welcome_notification(
				to=patient, enroller=request_user_patient)
			patient.save()

			c = RequestContext(request)
			c['patient'] = patient
			return render_to_response('fishfood/patient_view.html', c) # change to redirect

	return HttpResponseBadRequest("Something went wrong.")


@login_required
def retrieve_patient(request, *args, **kwargs):
	if request.GET:
		c = RequestContext(request)
		url_name = resolve(request.path_info).url_name
		c['url_name'] = url_name

		patient_id = request.GET.get('p_id', None)
		if not is_integer(patient_id):
			pass
		else:
			try:
				patient = PatientProfile.objects.get(id=int(patient_id))
			except PatientProfile.DoesNotExist:
				pass
			else:
				if not request.user.has_perm('patients.manage_patient_profile', patient):
					return HttpResponseBadRequest("You don't have access to this user's profile")

				c['patient'] = patient

				# get reminders
				reminders = Notification.objects.filter(
					to=patient, type=Notification.MEDICATION)
				reminders = sorted(reminders, key=lambda x: (x.prescription.drug.name, x.send_datetime.time()))
				reminder_groups = []
				for drug, outer_group in groupby(reminders, lambda x: x.prescription.drug.name):
					drug_group = {'drug_name':drug, 'schedules':[]}
					for send_datetime, time_group in groupby(outer_group, lambda y: y.send_datetime.time()):
						days_of_week = []
						for reminder in time_group:
							days_of_week.append(reminder.day_of_week)
						drug_group['schedules'].append({'time':send_datetime, 'days_of_week':days_of_week})
					reminder_groups.append(drug_group)
				c['reminder_groups'] = tuple(reminder_groups)

				# get caregivers
				safety_net_relations = SafetyNetRelationship.objects.filter(source_patient=patient)
				c['safety_net_relations'] = safety_net_relations

				return render_to_response('fishfood/patient_view.html', c)
		return HttpResponseBadRequest("This user already exists.")
	return HttpResponseBadRequest("Something went wrong.")


@login_required
def update_patient(request, *args, **kwargs):
	if request.POST:
		form = UpdatePatientForm(request.POST)
		if form.is_valid():
			p_id = form.cleaned_data['p_id']
			patient = PatientProfile.objects.get(id=p_id)

			if not request.user.has_perm('patients.manage_patient_profile', patient):
				return HttpResponseBadRequest("You don't have access to this user's profile")

			full_name = form.cleaned_data['full_name']
			name_tokens = full_name.split()
			first_name = name_tokens[0].strip()
			last_name = "".join(name_tokens[1:]).strip()
			primary_phone_number = form.cleaned_data['primary_phone_number']
			patient.first_name = first_name
			patient.last_name = last_name
			patient.full_name = full_name
			patient.primary_phone_number = primary_phone_number
			patient.save()
			result = {
				'first_name':first_name,
				'last_name':last_name,
				'primary_phone_number':primary_phone_number,
			}
			return HttpResponse(json.dumps(result), content_type='application/json')
	return HttpResponseBadRequest('Something went wrong')


@login_required
def delete_patient(request, *args, **kwargs):
	if request.POST:
		form = DeletePatientForm(request.POST)
		if form.is_valid():
			p_id = form.cleaned_data['p_id']
			patient = PatientProfile.objects.get(id=p_id)

			if not request.user.has_perm('patients.manage_patient_profile', patient):
				return HttpResponseBadRequest("You don't have access to this user's profile")

			# patient loses a caregiver
			patient.num_caregivers -= 1

			# if patient is request user, delete the patient 
			if request.user == patient:
				patient.num_caregivers = 0

			# If patient has no more caregivers, delete patient's Prescriptions, Notifications
			# and also SafetyNetRelationship, PrimaryContactRelationship objects for which
			# the patient is the source_patient
			# Note we keep outstanding Messages and SentReminders
			if patient.num_caregivers == 0:
				Prescription.objects.filter(patient=patient).delete()
				Notification.objects.filter(to=patient).delete()
				SafetyNetRelationship.objects.filter(source_patient=patient).delete()
				# delete permissions
				filters = Q(content_type=ContentType.objects.get_for_model(patient), 
			    	object_pk=patient.pk)
				UserObjectPermission.objects.filter(filters).delete()
				GroupObjectPermission.objects.filter(filters).delete()
				patient.quit()

			patient.save()

			# remove request user from safety net
			request_user_patient = PatientProfile.objects.get(pk=request.user.pk)
			SafetyNetRelationship.objects.filter(
				target_patient__id=request.user.id,
				source_patient=patient).delete()
			
			# don't show the patient in the request user's patient list anymore
			remove_perm('view_patient_profile', request.user, patient)

			return redirect('/fishfood/')

	return HttpResponseBadRequest('Something went wrong')


@login_required
def patient_search_results(request, *args, **kwargs):
	if request.GET:
		q = request.GET['q']

		results = get_objects_for_user(request.user, 'patients.manage_patient_profile')
		results = results.filter( 
			Q(full_name__icontains=q) &
			(Q(status=PatientProfile.ACTIVE) | Q(status=PatientProfile.NEW))
		).order_by('full_name')

		return render_to_response(
			'fishfood/patient_search_results_list.html', 
			{'patient_search_results_list':results}
		)
	else:
		return HttpResponseBadRequest("Something went wrong")


@login_required
def create_reminder(request, *args, **kwargs):
	# update if reminder exists, else create it'
	if request.POST:
		form = NewReminderForm(request.POST)
		if form.is_valid():
			active_days_of_week = form.cleaned_data['active_days_of_week']
			if not True in active_days_of_week:
				return HttpResponseBadRequest('Must select at least one day.') 

			p_id = form.cleaned_data['p_id']
			patient = PatientProfile.objects.get(id=p_id)

			if not request.user.has_perm('patients.manage_patient_profile', patient):
				return HttpResponseBadRequest("You don't have access to this user's profile")
			
			drug_name = form.cleaned_data['drug_name']
			drug = Drug.objects.get_or_create(name=drug_name)[0]

			(prescription, prescription_created) = Prescription.objects.get_or_create(
				prescriber=request.user, patient=patient, drug=drug)

			reminder_time = form.cleaned_data['reminder_time']
			existing_reminders = Notification.objects.filter(
				to=patient, prescription__drug__name__iexact=drug_name)

			# check if it's a daily reminder
			new_reminders = []
			is_daily_reminder = False not in active_days_of_week
			med_reminder = None
			if is_daily_reminder:
				# remove all other reminders at this time, and replace with single daily reminder
				for r in existing_reminders:
					if r.send_datetime.time() == reminder_time:
						r.delete()
				send_datetime = datetime.datetime.combine(
					datetime.datetime.today().date(), reminder_time)
				med_reminder = Notification.objects.get_or_create(
					to=patient, 
					type=Notification.MEDICATION,
					send_datetime = send_datetime,
					repeat=Notification.DAILY,
					prescription=prescription)[0]
				new_reminders.append(med_reminder)
				med_reminder.update_to_next_send_time()
				med_reminder.day_of_week = 8
				med_reminder.save()

			# otherwise, schedule weekly reminders
			else:
				for idx, active_day in enumerate(active_days_of_week):
					if active_day:
						skip_day = False # skip day if already reminder at this time
						existing_reminders_for_day = existing_reminders.filter( 
							Q(day_of_week=idx+1) | Q(repeat=Notification.DAILY)
						)
						for r in existing_reminders_for_day:
							if r.send_datetime.time() == reminder_time:
								skip_day = True
								break
						if not skip_day:
							today = datetime.datetime.today()
							if today.weekday() == idx:
								send_datetime = datetime.datetime.combine(today.date(), reminder_time)
							else:
								send_datetime = datetime.datetime.combine(
									next_weekday(today.date(), idx), reminder_time
								)
							med_reminder = Notification.objects.get_or_create(
								to=patient, 
								type=Notification.MEDICATION,
								send_datetime = send_datetime,
								repeat=Notification.WEEKLY,
								prescription=prescription)[0]
							new_reminders.append(med_reminder)
							med_reminder.day_of_week = idx + 1
							med_reminder.save()
			# create a refill reminder for the patient if prescription is not filled
			send_refill_reminder = form.cleaned_data['send_refill_reminder']
			if send_refill_reminder and not prescription.filled:
				refill_reminder = Notification.objects.get_or_create(
					to=patient, 
					type=Notification.REFILL,
					repeat=Notification.DAILY,
					prescription=prescription)[0]
				new_reminders.append(refill_reminder)
			elif not send_refill_reminder and prescription_created:
				prescription.filled = True
				prescription.save()
			for r in new_reminders:
				assign_perm('view_notification_smartdose', request.user, r)
				assign_perm('change_notification_smartdose', request.user, r)
			return HttpResponse('')
	return HttpResponseBadRequest()


@login_required
def update_reminder(request, *args, **kwargs):
	pass


@login_required
def delete_reminder(request, *args, **kwargs):
	if request.POST:
		form = DeleteReminderForm(request.POST)
		if form.is_valid():
			p_id = form.cleaned_data['p_id']
			patient = PatientProfile.objects.get(id=p_id)
			
			if not request.user.has_perm('patients.manage_patient_profile', patient):
				return HttpResponseBadRequest("You don't have access to this user's profile")

			drug_name = form.cleaned_data['drug_name']
			if form.cleaned_data['all_deleted']: # delete all reminder objects
				Notification.objects.filter(
					to=patient, prescription__drug__name__iexact=drug_name, 
					type=Notification.REFILL).delete()
			for r in form.cleaned_data['reminders_for_deletion']: 
				r.delete()
			return HttpResponse('')
	return HttpResponseBadRequest('Something went wrong')


@login_required
def create_safety_net_contact(request):
	if request.POST:
		form = CreateSafetyNetContactForm(request.POST)
		if form.is_valid():
			# create safety net
			p_id = form.cleaned_data['p_id']
			patient = PatientProfile.objects.get(id=p_id)

			if not request.user.has_perm('patients.manage_patient_profile', patient):
				return HttpResponseBadRequest("You don't have access to this user's profile")

			full_name = form.cleaned_data['full_name']
			relationship = form.cleaned_data['relationship']
			primary_phone_number = form.cleaned_data['primary_phone_number']
			receives_all_reminders = form.cleaned_data.get(
				'receives_all_reminders', False)

			target_patient = PatientProfile.objects.get_or_create(
				primary_phone_number=primary_phone_number,
				defaults={'full_name':full_name}
			)[0]
			patient.add_safety_net_contact(
				target_patient=target_patient,
				relationship=relationship, 
				receives_all_reminders=receives_all_reminders)

			# give the safety-net contact permission to see/manage patient
			assign_perm('view_patient_profile', target_patient, patient)
			assign_perm('manage_patient_profile', target_patient, patient)

			return HttpResponse('')

	return HttpResponseBadRequest('Something went wrong')


@login_required
def delete_safety_net_contact(request):
	if request.POST:
		form = DeleteSafetyNetContactForm(request.POST)
		if form.is_valid():
			# delete safety net
			p_id = form.cleaned_data['p_id']
			patient = PatientProfile.objects.get(id=p_id)

			target_p_id = form.cleaned_data['target_p_id']

			if not request.user.has_perm('patients.manage_patient_profile', patient):
				return HttpResponseBadRequest("You don't have access to this user's profile")

			q = SafetyNetRelationship.objects.filter(
				source_patient__id=p_id, target_patient__id=target_p_id)
			if q.exists():
				q.delete()
				target_patient = PatientProfile.objects.get(id=target_p_id)
				remove_perm('view_patient_profile', target_patient, patient)
				remove_perm('manage_patient_profile', target_patient, patient)
				return HttpResponse('')
			else:
				return HttpResponseBadRequest('This safety-net relationship does not exist')

	return HttpResponseBadRequest('something went wrong')


@login_required
def dashboard(request):
	# stub
	return render_to_response('fishfood/dashboard.html')
