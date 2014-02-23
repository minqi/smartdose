import datetime

from django import forms
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.core.context_processors import csrf
from django.core.exceptions import ValidationError
from django.views.generic.base import View
from django.db.models import Q
from localflavor.us.forms import USPhoneNumberField
from itertools import groupby

from common.utilities import next_weekday, convert_to_e164
from common.models import Drug
from patients.models import PatientProfile, SafetyNetRelationship, PrimaryContactRelationship
from doctors.models import DoctorProfile
from reminders.models import ReminderTime, Prescription, Message, SentReminder

from lockdown.decorators import lockdown

def landing_page(request):
	return HttpResponse(content="STAY TUNED", content_type="text/plain")

class PatientForm(forms.Form):
    full_name = forms.CharField(max_length=80)
    primary_phone_number = USPhoneNumberField()

class NewReminderForm(forms.Form):
	drug_name = forms.CharField(max_length=80)
	reminder_time = forms.TimeField(required=True)

@lockdown()
def fishfood(request):
	c = RequestContext(request)
	c['patient_search_results_list'] = PatientProfile.objects.filter(
		Q(status=PatientProfile.ACTIVE) | Q(status=PatientProfile.NEW)).order_by('full_name')

	return render_to_response('fishfood/fishfood.html', c)

@lockdown()
# create new patient
def create_patient(request, *args, **kwargs):
	# validate form
	if request.POST:
		form = PatientForm(request.POST)
		if form.is_valid():
			full_name = request.POST['full_name']
			name_tokens = full_name.split()
			first_name = name_tokens[0].strip()
			last_name = "".join(name_tokens[1:]).strip()
			primary_phone_number = convert_to_e164(request.POST['primary_phone_number'])
			# create new patient
			try: 
				(patient, created) = PatientProfile.objects.get_or_create(
					first_name=first_name, last_name=last_name, 
					primary_phone_number=primary_phone_number,
				)
			except ValidationError:
				pass
			else:
				c = RequestContext(request)
				c['patient'] = patient
				if not created:
					patient.status = PatientProfile.NEW
					patient.save()
				ReminderTime.objects.create_welcome_notification(to=patient)
				return render_to_response('fishfood/patient_view.html', c)
			return HttpResponseBadRequest("This phone number is already in use.")
	# if badly formed request
	return HttpResponseBadRequest("")

@lockdown()
def retrieve_patient(request, *args, **kwargs):
	if request.GET:
		c = RequestContext(request)

		patient_id = request.GET['p_id']
		patient = PatientProfile.objects.get(id=patient_id)
		c['patient'] = patient

		# get reminders
		reminders = ReminderTime.objects.filter(
			to=patient, reminder_type=ReminderTime.MEDICATION)
		reminders = sorted(reminders, key=lambda x: (x.prescription.drug.name, x.send_time.time()))
		reminder_groups = []
		for drug, outer_group in groupby(reminders, lambda x: x.prescription.drug.name):
			drug_group = {'drug_name':drug, 'schedules':[]}
			for send_time, time_group in groupby(outer_group, lambda y: y.send_time.time()):
				days_of_week = []
				for reminder in time_group:
					days_of_week.append(reminder.day_of_week)
				drug_group['schedules'].append({'time':send_time, 'days_of_week':days_of_week})
			reminder_groups.append(drug_group)
		c['reminder_groups'] = tuple(reminder_groups)
		return render_to_response('fishfood/patient_view.html', c)
	return HttpResponseBadRequest("Something went wrong")

@lockdown()
def update_patient(request, *args, **kwargs):
	if request.POST:
		form = PatientForm(request.POST)
		if form.is_valid():
			full_name = request.POST['full_name']
			name_tokens = full_name.split()
			first_name = name_tokens[0].strip()
			last_name = "".join(name_tokens[1:]).strip()
			primary_phone_number = request.POST['primary_phone_number']
			p_id = request.POST['p_id']
			try:
				patient = PatientProfile.objects.get(id=p_id)
			except PatientProfile.DoesNotExist:
				return HttpResponseBadRequest('Something went wrong')
			else:
				patient.first_name = first_name
				patient.last_name = last_name
				patient.primary_phone_number = primary_phone_number
				patient.save()

@lockdown()
def delete_patient(request, *args, **kwargs):
	if request.POST:
		p_id = request.POST.get('p_id', None)
		if p_id:
			try: 
				patient = PatientProfile.objects.get(id=p_id)
			except PatientProfile.DoesNotExist:
				return HttpResponseBadRequest('Something went wrong')
			else:
				patient.status = PatientProfile.QUIT
				patient.save()

				# Delete patient's Prescriptions, Notifications
				# and also SafetyNetRelationship, PrimaryContactRelationship objects for which
				# the patient is the source_patient
				# Note we keep outstanding Messages and SentReminders
				Prescription.objects.filter(patient=patient).delete()
				ReminderTime.objects.filter(to=patient).delete()
				SafetyNetRelationship.objects.filter(source_patient=patient).delete()
				PrimaryContactRelationship.objects.filter(source_patient=patient).delete()

				return redirect('/fishfood/')
	return HttpResponseBadRequest('Something went wrong')

@lockdown()
def patient_search_results(request, *args, **kwargs):
	if request.GET:
		q = request.GET['q']
		results = PatientProfile.objects.filter(
			Q(full_name__icontains=q) &
			(Q(status=PatientProfile.ACTIVE) | Q(status=PatientProfile.NEW))
		).order_by('full_name')
		return render_to_response(
			'fishfood/patient_search_results_list.html', 
			{'patient_search_results_list':results}
		)
	else:
		return HttpResponseBadRequest("Something went wrong")

@lockdown()
def patient_reminder_list(request, *args, **kwargs):
	reminder_id = request.GET['id']
	(reminder, exists) = ReminderTime.objects.get(id=reminder_id)

@lockdown()
def create_reminder(request, *args, **kwargs):
	# update if reminder exists, else create it
	if request.POST:
		p_id = request.POST['p_id']
		try:
			patient = PatientProfile.objects.get(id=int(p_id))
		except PatientProfile.DoesNotExist:
			return HttpResponseBadRequest("Something went wrong")
		else:
			dr_smartdose = DoctorProfile.objects.get_or_create(
				first_name="Smartdose", last_name="", 
				primary_phone_number="+18569067308", 
				birthday=datetime.date(2014, 1, 28))[0]
			drug_name = request.POST['drug_name'].strip().lower()
			drug = Drug.objects.get_or_create(name=drug_name)[0]
			prescription = Prescription.objects.get_or_create(
				prescriber=dr_smartdose, patient=patient, drug=drug)[0]
			reminder_time_str = request.POST['reminder_time']
			reminder_time = datetime.datetime.strptime(reminder_time_str, '%H:%M').time()
			existing_reminders = ReminderTime.objects.filter(
				to=patient, prescription__drug__name__iexact=drug_name)

			# check if it's a daily reminder
			is_daily_reminder = True
			days = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
			for day in days:
				if not request.POST.get(day, None):
					is_daily_reminder = False
					break
			med_reminder = None
			if is_daily_reminder:
				send_datetime = datetime.datetime.combine(today.date(), reminder_time)
				med_reminder = ReminderTime.objects.get_or_create(
					to=patient, 
					reminder_type=ReminderTime.MEDICATION,
					send_time = send_datetime, 
					repeat=ReminderTime.DAILY, 
					prescription=prescription)[0]
				med_reminder.update_to_next_send_time()

			# otherwise, schedule weekly reminders
			else:
				for idx, day in enumerate(days):
					if request.POST.get(day, None):
						existing_reminders_for_day = existing_reminders.filter(day_of_week=idx+1)
						skip_day = False
						for r in existing_reminders_for_day:
							if r.send_time.hour == reminder_time.hour and r.send_time.minute == reminder_time.minute:
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
							med_reminder = ReminderTime.objects.get_or_create(
								to=patient, 
								reminder_type=ReminderTime.MEDICATION,
								send_time = send_datetime, 
								repeat=ReminderTime.WEEKLY, 
								prescription=prescription)[0]
							med_reminder.day_of_week = idx + 1
							med_reminder.save()
			# create a refill reminder for the patient
			refill_reminder = ReminderTime.objects.get_or_create(
				to=patient, 
				reminder_type=ReminderTime.REFILL, 
				repeat=ReminderTime.DAILY, 
				prescription=prescription)[0]
			return HttpResponse('')
	else:
		raise Http404

@lockdown()
def update_reminder(request, *args, **kwargs):
	pass

@lockdown()
def delete_reminder(request, *args, **kwargs):
	if request.POST:
		p_id = request.POST['p_id']
		try:
			patient = PatientProfile.objects.get(id=int(p_id))
		except PatientProfile.DoesNotExist:
			return HttpResponseBadRequest('Something went wrong')
		else:
			drug_name = request.POST['drug_name']
			reminder_time = request.POST['reminder_time'].replace(' ', '').strip()
			reminder_time = datetime.datetime.strptime(reminder_time, '%I:%M%p').time()
			reminders = ReminderTime.objects.filter(
				to=patient, prescription__drug__name__iexact=drug_name, 
				reminder_type=ReminderTime.MEDICATION)
			num_med_reminders = len(reminders)
			reminders_for_deletion = []
			for r in reminders:
				if r.send_time.time() == reminder_time:
					reminders_for_deletion.append(r)
			if len(reminders_for_deletion) == num_med_reminders:
				# if no more reminders for this drug, also delete any refill reminders for it
				ReminderTime.objects.filter(
					to=patient, prescription__drug__name__iexact=drug_name, 
					reminder_type=ReminderTime.REFILL).delete()
			for r in reminders_for_deletion:
				r.delete()
			
			return HttpResponse('')
	return HttpResponseBadRequest('Something went wrong')

