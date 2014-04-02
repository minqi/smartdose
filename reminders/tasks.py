# Tasks that will be executed by Celery.
from __future__ import absolute_import

import datetime
import common.datasources as datasources

from django.conf import Settings
from django.template.loader import render_to_string
from django.db.models import Q

from common.models import UserProfile
from doctors.models import DoctorProfile
from patients.models import PatientProfile, SafetyNetRelationship
from reminders.models import Notification, Message
from reminders.notification_center import NotificationCenter
from reminders.safety_net_center import SafetyNetCenter

from celery import shared_task

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
	reminders_for_now = Notification.objects.notifications_at_time(now)
	# Get reminders that are distinct by patients
	distinct_reminders = reminders_for_now.distinct('to')

	# if not distinct_reminders:
	# 	print "No reminders"

	# Send a reminder to each patient with the pills they need to take
	nc = NotificationCenter()
	for reminder in distinct_reminders:
		p = reminder.to
		p_reminders = reminders_for_now.filter(to=p)
		# for p_reminder in p_reminders:
		# 	print "Type: ", p_reminder._type
		# 	if p_reminder.prescription != None: print "Name: ", p_reminder.prescription.drug.name
		# 	print "To: ", p_reminder.to
		nc.send_notifications(to=p, notifications=p_reminders)


@shared_task()
def schedule_safety_net_messages():
	"""
	Called weekly from schedule.
	Schedules safety net messages to safety net members for all patients
	"""
	snc = SafetyNetCenter()
	now = datetime.datetime.now()
	snc.schedule_safety_net_messages(
		window_start=now - snc.window, 
		window_finish=now, 
		threshold=snc.threshold, 
		timeout=snc.timeout)