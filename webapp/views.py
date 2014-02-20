from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.views.generic.base import View
from django.db.models import Q
from localflavor.us.forms import USPhoneNumberField

from patients.models import PatientProfile
from django import forms

def landing_page(request):
	return HttpResponse(content="STAY TUNED", content_type="text/plain")

class NewPatientForm(forms.Form):
    full_name = forms.CharField(max_length=80)
    primary_phone_number = USPhoneNumberField()

def fishfood(request):
	results = PatientProfile.objects.all()
	return render_to_response(
		'fishfood/fishfood.html', {'patient_search_results_list':results}
	)

class FishfoodPatientView(View):
	"""
	Class-based views for creating/getting/updating/deleting patients 
	"""
	def get(self, request, *args, **kwargs):
		patient_id = request.GET['id'];
		patient = PatientProfile.objects.get(id=patient_id)
		print patient.id
		print patient.full_name
		return render_to_response(
			'fishfood/patient_view.html', 
			{'patient':patient}
		)

	def post(self, request, *args, **kwargs):
		pass

def patient_search_results(request, *args, **kwargs):
	if request.GET:
		q = request.GET['q']
		results = PatientProfile.objects.filter(full_name__icontains=q).order_by('full_name')
		return render_to_response(
			'fishfood/patient_search_results_list.html', 
			{'patient_search_results_list':results}
		)
	else:
		raise Http404