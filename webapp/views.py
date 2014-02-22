import datetime

from django import forms
from django.shortcuts import render_to_response, redirect
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.core.context_processors import csrf
from django.core.exceptions import ValidationError
from django.views.generic.base import View
from django.db.models import Q
from localflavor.us.forms import USPhoneNumberField
from itertools import groupby

from common.utilities import next_weekday
from common.models import Drug
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from reminders.models import ReminderTime, Prescription

def landing_page(request):
	return HttpResponse(content="STAY TUNED", content_type="text/plain")

class PatientForm(forms.Form):
    full_name = forms.CharField(max_length=80)
    primary_phone_number = USPhoneNumberField()

class NewReminderForm(forms.Form):
	drug_name = forms.CharField(max_length=80)
	reminder_time = forms.TimeField(required=True)

def fishfood(request):
	c = {}
	c.update(csrf(request))
	c['patient_search_results_list'] = PatientProfile.objects.all().order_by('full_name')

	return render_to_response('fishfood/fishfood.html', c)

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
			primary_phone_number = request.POST['primary_phone_number']
			# create new patient
			try: 
				(patient, created) = PatientProfile.objects.get_or_create(
					first_name=first_name, last_name=last_name, 
					primary_phone_number=primary_phone_number,
				)
			except ValidationError:
				pass
			else:
				if created:
					return render_to_response('fishfood/patient_view.html', {'patient': patient})
			return HttpResponseBadRequest("This patient already exists")
	# if badly formed request
	return HttpResponseBadRequest("")

def retrieve_patient(request, *args, **kwargs):
	if request.GET:
		c = {}
		c.update(csrf(request))

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
				return HttpResponseBadRequest("Something went wrong")
			else:
				patient.first_name = first_name
				patient.last_name = last_name
				patient.primary_phone_number = primary_phone_number
				patient.save()

def delete_patient(request, *args, **kwargs):
	if request.POST:
		p_id = request.POST.get['p_id', None]
		if p_id:
			PatientProfile.objects.filter(id=p_id).delete()

def patient_search_results(request, *args, **kwargs):
	if request.GET:
		q = request.GET['q']
		results = PatientProfile.objects.filter(full_name__icontains=q).order_by('full_name')
		return render_to_response(
			'fishfood/patient_search_results_list.html', 
			{'patient_search_results_list':results}
		)
	else:
		return HttpResponseBadRequest("Something went wrong")

def patient_reminder_list(request, *args, **kwargs):
	reminder_id = request.GET['id']
	(reminder, exists) = ReminderTime.objects.get(id=reminder_id)

def create_reminder(request, *args, **kwargs):
	# update if reminder exists, else create it
	print request
	print request.POST
	if request.POST:
		p_id = request.POST['p_id']
		try:
			patient = PatientProfile.objects.get(id=int(p_id))
		except PatientProfile.DoesNotExist:
			return HttpResponseBadRequest("Something went wrong")
		else:
			dr_smartdose = DoctorProfile.objects.get_or_create(first_name="Smartdose", last_name="", primary_phone_number="+18569067308", birthday=datetime.date(2014, 1, 28))[0]
			drug_name = request.POST['drug_name']
			drug = Drug.objects.get_or_create(name=drug_name)[0]
			prescription = Prescription.objects.get_or_create(
				prescriber=dr_smartdose, patient=patient, drug=drug, filled=False)[0]
			reminder_time_str = request.POST['reminder_time']
			reminder_time = datetime.datetime.strptime(reminder_time_str, '%H:%M').time()
			for idx, day in enumerate(('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')):
				if request.POST.get(day, None):
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
						repeat=ReminderTime.DAILY, 
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

def update_reminder(request, *args, **kwargs):
	pass

def delete_reminder(request, *args, **kwargs):
	pass