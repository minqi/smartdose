# Tasks that will be executed by Celery.
from __future__ import absolute_import

import datetime
import common.datasources as datasources

from celery import shared_task
from django.template.loader import render_to_string
from django.db.models import Q
from reminders.models import ReminderTime, Message, SentReminder
from common.models import UserProfile
from doctors.models import DoctorProfile
from patients.models import PatientProfile, SafetyNetRelationship
from reminders.notification_center import NotificationCenter

FAKE_CSV = False # Use fake patient csv data for 

# @shared_task()
def fetch_new_patient_records(source="fake_csv"):
	"""
	Fetch new patient records from data source
	"""
	if FAKE_CSV:
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
	distinct_reminders = reminders_for_now.distinct('to')

	# Send a reminder to each patient with the pills they need to take
	nc = NotificationCenter()
	for reminder in distinct_reminders:
		p = reminder.to
		p_reminders = reminders_for_now.filter(Q(prescription__patient=p) | Q(to=p))
		nc.send_notifications(to=p, notifications=p_reminders)


def compute_adherence_percentage_by_patients(window_start, window_finish, time, timeout):
	"""
	Returns a list of [patient, missed_dose] tuples for doses missed between window_start and window_finish at time time
	A dose is considered missed if it's gone unacknowledged for longer than timeout.
	"""
	reminders = SentReminder.objects.filter(
		time_sent__gte=window_start,
		time_sent__lte=window_finish,
		reminder_time__reminder_type=ReminderTime.MEDICATION).exclude(time_sent__gte=time - timeout)
	# Cache reminder_time for quick reminder_time__reminder_type and reminder_time__patient lookup
	reminders = reminders.prefetch_related('reminder_time').prefetch_related('reminder_time__prescription')

	patients = PatientProfile.objects.all()
	adherence_percentage_for_patients_list = []
	for patient in patients:
		dose_count = 0
		missed_dose_count = 0
		patient_reminders = reminders.filter(reminder_time__to=patient)
		for patient_reminder in patient_reminders:
			if (patient_reminder.prescription.safety_net_on):
				dose_count += 1
				if (patient_reminder.ack == False):
					missed_dose_count += 1
		adherence_percentage_for_patients_list.append([patient, dose_count/missed_dose_count])


def schedule_safety_net_messages_from_adherence_percentage_list(adherence_percentage_by_patients_list, threshold):
	""" Schedules notifications to safety net members.
		threshold is a threshold we use to calculate the cutoff of the adherence message to a patient
	"""
	for adherence_percentage_by_patient in adherence_percentage_by_patients_list:
		patient = adherence_percentage_by_patient[0]
		adherence_percentage = adherence_percentage_by_patient[1]
		# render prescriptions to template
		dictionary = {
		'adherence_percentage':adherence_percentage,
		'threshold':threshold,
		'patient_first':patient.first_name,
		}
		safety_net_members = patient.safety_net_members.all()
		for safety_net_member in safety_net_members:
			dictionary['patient_relationship'] = SafetyNetRelationship.objects.get(source_patient=patient, target_patient=safety_net_member).patient_relationship
			message_body = render_to_string('templates/messages/safety_net_adherent_message.txt', dictionary)
			ReminderTime.objects.create_safety_net_notification(to=safety_net_member, text=message_body)



def contactSafetyNet(window_start, window_finish, threshold, timeout):
	"""
	Sends a message to a safety net member to notify about missed doses. Safety net member will be notified of the number of
	doses missed between window_start and window_finish. A  medication is considered not taken if it has gone
	unacknowledged for longer than timeout. threshold is a percentage and represents the cutoff between adherence and non adherence
	"""
	adherence_percentage_by_patients_list = compute_adherence_percentage_by_patients(window_start, window_finish, datetime.datetime.now(), timeout)
	schedule_safety_net_messages_from_adherence_percentage_list(adherence_percentage_by_patients_list, threshold)


