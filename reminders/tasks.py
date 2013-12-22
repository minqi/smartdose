# Tasks that will be executed by Celery.
from __future__ import absolute_import

from celery import shared_task
from django.template.loader import render_to_string
from reminders.models import ReminderTime
from reminders.models import Message
from reminders.models import SentReminder
from patients.models import PatientProfile
import datetime

# Send reminders every REMINDER_INTERVAL minutes
REMINDER_INTERVAL = 15

# Takes a patient and the reminders for which the patient will be receiving the text
def sendOneReminder(patient, reminder_list):
	# Update database to reflect state of messages and reminders
	reminder_list = reminder_list.order_by("prescription__drug__name")
	message = Message.objects.create(patient=patient)
	for reminder in reminder_list:
		s = SentReminder.objects.create(prescription = reminder.prescription, 
										reminder_time = reminder,
										message=message)

	dictionary = {'reminder_list': reminder_list, 'message_number': message.message_number}
	message_body = render_to_string('templates/textreminder.txt', dictionary)
	
	success = patient.sendTextMessage(message_body)

# Called from scheduler. 
# Sends reminders to all users who have a reminder between this time and this time - REMINDER_INTERVAL
@shared_task()
def sendRemindersForNow():
	now = datetime.datetime.now()
	reminders_for_now = ReminderTime.objects.reminders_at_time(now, datetime.timedelta(minutes=REMINDER_INTERVAL))
	# Get reminders that are distinct by patients
	distinct_reminders = reminders_for_now.distinct('prescription__patient')
	# Send a reminder to each patient with the pills they need to take
	for reminder in distinct_reminders:
		p = reminder.prescription.patient
		p_reminders = reminders_for_now.filter(prescription__patient=p)
		sendOneReminder(p, p_reminders)