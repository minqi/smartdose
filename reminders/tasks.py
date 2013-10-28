# Tasks that will be executed by Celery.
from celery import task
from django.template.loader import render_to_string
from reminders.models import NextReminderPointer
from reminders.models import Message
from reminders.models import MessageReminderRelationship
from common.utilities import sendTextMessage
from patients.models import PatientProfile
from datetime import datetime

# Send reminders every REMINDER_INTERVAL minutes
REMINDER_INTERVAL = 15

# Example task that adds two numbers
# @task()
# def add(x, y):
#  	return x + y

# Accepts a patient and the pills for which the patient will be receiving the reminder
# TODO(mgaba): Logs and tests
def sendOneReminder(patient, reminder_list):
	#TODO(mgaba): Write code to go from reminder_list to list of drug names
	#dictionary = {'med_list': reminder_list}
	#message_body = render_to_string('templates/textreminder.txt', dictionary)
	#success = sendTextMessage(message_body, patient.primary_phone_number)
	#TODO(mgaba): Add database operations:
	# Increment send time for nextreminderpointer
	# Add message record
	# Add sentReminder
	# Add relationship from message to set reminder
	#if success:
	#	message = Message.objects.create(patient=patient)
	#	for med in med_list:
	#return True if success else False

# Called from scheduler. 
# Sends reminders to all users who have a reminder at this time +- REMINDER_INTERVAL
def sendRemindersForNow():
		now = datetime.now()
		earliest_reminder = now.replace(minute=now.minute-REMINDER_INTERVAL)
		latest_reminder = now.replace(minute=now.minute+REMINDER_INTERVAL)
		reminders_for_now_list = NextReminderPointer.objects
									.filter(send_time > earliest_reminder, send_time < latest_reminder)
									.values('username');



"""
@task()
def sendRemindersNow():
	reminders_to_send = Reminder.objects.remindersForNow()

	for reminder_to_send in reminders_to_send:
		reminder_to_send.sendReminder()
"""