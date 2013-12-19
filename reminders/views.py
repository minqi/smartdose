# Create your views here.
from django.conf import settings
from reminders.models import Message
from reminders.models import SentReminder
from reminders.models import MessageReminderRelationship
from patients.models import PatientProfile
from datetime import datetime,timedelta
from reminders.tasks import REMINDER_INTERVAL

# Number of hours for which a text can be ack'd
ACK_WINDOW = REMINDER_INTERVAL * 4

def isDone(body):
	if body.lower() == "d" or body.lower() == "done":
		return True
	else:
		return False

def isQuit(body):
	if body.lower() == "q" or body.lower() == "quit":
		return True
	else:
		return False

def processDone(number):
	# Find all messages for the given number
	messages = Message.objects.filter(patient__primary_phone_number=number).order_by('-time_sent')
	if not messages:
		return False

	# Select messages to ack. It is either all messages in the last hour OR the most recent message
	recent_time = datetime.now() - timedelta(minutes=ACK_WINDOW)
	recent_messages = messages.filter(time_sent__gte=recent_time)
	if not recent_messages:
		recent_messages = messages[:1]

	for message in recent_messages:
		sent_reminder_keys = MessageReminderRelationship.objects.filter(message=message)
		for sent_reminder in sent_reminder_keys:
			sent_reminder.sent_reminder.processAck()

	#TODO(mgaba): Send a response to patient to let them know what percentage compliance they are
	return True

def processQuit(number):
	patient = PatientProfile.objects.get(primary_phone_number=number)
	patient.quit()
	return False

#TODO(mgaba): Write code to process unknown
def processUnknown(number):
	return False

def handle_text(request):
	if isDone(request.GET['body']):
		processDone(request.GET['from'])
	elif isQuit(request.GET['body']):
		processQuit(request.GET['from'])
	else:
		processUnknown(request.GET['from'])