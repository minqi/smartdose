# Create your views here.
from django.conf import settings
from reminders.models import Message
from reminders.models import SentReminder
from patients.models import PatientProfile
from datetime import datetime,timedelta
from reminders.tasks import REMINDER_INTERVAL

# Number of hours for which a text can be ack'd
ACK_WINDOW = REMINDER_INTERVAL * 4

def isDone(body):
	# Check to see if the body is a number.
	try:
		float(body)
	 	return True
	except ValueError:
		return False

def isQuit(body):
	if body.lower() == "q" or body.lower() == "quit":
		return True
	else:
		return False


def processDone(phone_number, message_number):
	# Find all messages for the given number
	messages = Message.objects.filter(patient__primary_phone_number=phone_number)
	if not messages:
		return False

	# Select messages to ack. It is the message with the appropriate value
	recent_messages = messages.filter(message_number=message_number, state=Message.UNACKED)
	if not recent_messages:
		return False

	for message in recent_messages:
		message.processAck()

	#TODO(mgaba): Send a response to patient to let them know what percentage compliance they are
	return True

def processQuit(number):
	patient = PatientProfile.objects.filter(primary_phone_number=number)
	if not patient:
		return False
	patient.quit()
	return False

#TODO(mgaba): Write code to process unknown
def processUnknown(number):
	return False

def handle_text(request):
	if isDone(request.GET['body']):
		processDone(request.GET['from'], request.GET['body'])
	elif isQuit(request.GET['body']):
		processQuit(request.GET['from'])
	else:
		processUnknown(request.GET['from'])

