# Tasks that will be executed by Celery.
from celery import task
from django.template.loader import render_to_string
from reminders.models import ReminderTime
from reminders.models import Message
from reminders.models import SentReminder
from patients.models import PatientProfile
from datetime import datetime

# Send reminders every REMINDER_INTERVAL minutes
REMINDER_INTERVAL = 15

# Takes a patient and the reminders for which the patient will be receiving the text
# TODO(mgaba): Logs and tests
def sendOneReminder(patient, reminder_list):
	dictionary = {'reminder_list': reminder_list}
	message_body = render_to_string('templates/textreminder.txt', dictionary)
	
	success = patient.sendTextMessage(message_body)

	if success:
		# Update database to reflect state of messages and reminders
		message = Message.objects.create(patient=patient)
		for reminder in reminder_list:
			s = SentReminder.objects.create(prescription = reminder.prescription, 
											reminder_num = reminder.reminder_num,
											message=message)
		return True
	else:
		return False

# Called from scheduler. 
# Sends reminders to all users who have a reminder between this time and this time - REMINDER_INTERVAL
@task()
def sendRemindersForNow():
	now = datetime.now()
	reminders_for_now = ReminderTime.objects.reminders_at_time(now, REMINDER_INTERVAL)
	# Get reminders that are distinct by patients
	distinct_reminders = reminders.distinct('prescription__patient')
	# Send a reminder to each patient with the pills they need to take
	for reminder in distinct_reminders:
		p = reminder.prescription.patient
		p_pills = reminders_for_now.filter(prescription__patient=p)
		sendOneReminder(p, p_pills, False)

