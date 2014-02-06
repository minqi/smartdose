# Tasks that will be executed by Celery.
from __future__ import absolute_import

import datetime
import common.datasources as datasources

from celery import shared_task
from django.template.loader import render_to_string
from django.db.models import Q
from reminders.models import ReminderTime, Message, SentReminder
from common.models import UserProfile
from patients.models import PatientProfile, SafetyNetRelationship
from doctors.models import DoctorProfile

FAKE_CSV = False # Use fake patient csv data for 

# @shared_task()
def fetch_new_patient_records(source="fake_csv"):
	"""
	Fetch new patient records from data source
	"""
	print "Fetching new patient records..."
	datasources.load_patient_data(source)
	print "Fetched new patient records"

@shared_task()
def sendRemindersForNow():
	"""
	Called from scheduler. 
	Sends reminders to all users who have a reminder between this time and this time - REMINDER_INTERVAL
	"""
	now = datetime.datetime.now()
	reminders_for_now = ReminderTime.objects.reminders_at_time(now)
	# Get reminders that are distinct by patients
	distinct_reminders = reminders_for_now.distinct('prescription__patient')
	# Send a reminder to each patient with the pills they need to take
	for reminder in distinct_reminders:
		p = reminder.prescription.patient
		p_reminders = reminders_for_now.filter(Q(prescription__patient=p) | Q(to=p))
		p.sendReminders(p_reminders)


def contactSafetyNet(window_start, window_finish, threshold, timeout):
	"""
	Sends a message to a safety net member to notify about a missed dose. Safety net member will be notified if the patient 
	takes fewer than threshold (a ratio of taken medications to total medications) between window_start, window_finish. A 
	medication is considered not taken if it has gone unacknowledged for longer than timeout.
	"""
	# Get all acked reminders in the timeframe
	acked_reminders = SentReminder.objects.filter(time_sent__gte=window_start, time_sent__lte=window_finish, ack=True)
	# Get all expired reminders in the timeframe
	expired_reminders = SentReminder.objects.filter(time_sent__gte=window_start, time_sent__lte=window_finish, ack=False).exclude(time_sent__gte=datetime.datetime.now() - timeout)
	# Get all prescriptions with expired reminders
	prescription_reminders = expired_reminders.distinct('prescription')
	
	# for each prescription with a safety net compile a list of adherent and non-adherent prescriptions
	patient_nonadherent_dict = {}
	patient_adherent_dict = {}
	for prescription_reminder in prescription_reminders:
		prescription = prescription_reminder.prescription
		if not prescription.safety_net_on:
			continue
		# compute expired / acked+expired reminders
		expired_count = expired_reminders.filter(prescription=prescription).count()
		acked_count = acked_reminders.filter(prescription=prescription).count()
		total_count = expired_count + acked_count
		ratio = acked_count / total_count
		# if the computed number is less than threshold add it to the dictionary
		if ratio < threshold:
			patient_nonadherent_dict.setdefault(prescription.patient, []).append((prescription, acked_count, total_count)) # Use setdefault to avoid KeyError
			prescription.last_contacted_safety_net = datetime.datetime.now()
			prescription.save()
		else:
			patient_adherent_dict[prescription.patient].append((prescription, acked_count, total_count))

	# Send messages for non-adherence to safety net members
	for patient, prescriptions in patient_nonadherent_dict.iteritems():
		# render prescriptions to template
		dictionary = {'prescriptions':prescriptions, 'patient_first':patient.first_name, 'patient_last':patient.last_name, 'window_start':window_start, 'window_finish':window_finish}
		safety_net_members = patient.safety_net_members.all()
		for safety_net_member in safety_net_members:
			dictionary['patient_relationship'] = SafetyNetRelationship.objects.get(patient=patient, safety_net=safety_net_member).patient_relationship
			message_body = render_to_string('safety_net_nonadherent_message.txt', dictionary)
			# send the message to the safety net
			safety_net_member.sendTextMessage(message_body)

	# Send messages for adherence to safety net members
	for patient, prescriptions in patient_adherent_dict.iteritems():
		# render prescriptions to template
		dictionary = {'prescriptions':prescriptions, 'patient_first':patient.first_name, 'patient_last':patient.last_name, 'window_start':window_start, 'window_finish':window_finish}
		safety_net_members = patient.safety_net_members.all()
		for safety_net_member in safety_net_members:
			dictionary['patient_relationship'] = SafetyNetRelationship.objects.get(patient=patient, safety_net=safety_net_member).patient_relationship
			message_body = render_to_string('safety_net_adherent_message.txt', dictionary)
			# send the message to the safety net
			safety_net_member.sendTextMessage(message_body)





