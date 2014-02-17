# Create your views here.
from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from reminders.models import Message
from reminders.models import SentReminder
from patients.models import PatientProfile
from datetime import datetime,timedelta

# Number of hours for which a text can be ack'd
ACK_WINDOW = 24

def isAck(body):
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

def processAck(phone_number, message_number):
	# Find all messages for the given number
	messages = Message.objects.filter(patient__primary_phone_number=phone_number)
	if not messages:
		return HttpResponseNotFound()

	# Select messages to ack. It is the message with the appropriate value
	recent_messages = messages.filter(message_number=message_number, state=Message.UNACKED)
	if not recent_messages:
		return HttpResponse(content="Whoops--there is no reminder with number '" + message_number + "' that needs a response.", content_type="text/plain")

	for message in recent_messages:
		message.processAck()

	#TODO(mgaba): Send a response to patient to let them know what percentage compliance they are
	#TODO(mgaba): Write a module that will choose a random message from a set of good responses. Options:
	#	Social: how this person compares to other people
	#	Stats: how well this person is doing on their compliance
	#	Stats: how much less likely is a person to go to the hospital
	#	Stats: how much less is this person going to cost their healthplan/economy
	#	Encouragement: this person can get better
	#	Education: what is happening to this person for taking their medicine, if they don't take their medicine
	return HttpResponse(content="Your family will be happy to know that you're taking care of your health :)", content_type="text/plain")

def processQuit(number):
	patient = PatientProfile.objects.filter(primary_phone_number=number)
	if not patient:
		return HttpResponseNotFound()
	patient.quit()
	return HttpResponse(content="You've been unenrolled from Smartdose. Please let us know why you quit, so we can improve our service for other patients.", content_type="text/plain")

#TODO(mgaba): Write code to process unknown
def processUnknown(number):
	patient = PatientProfile.objects.filter(primary_phone_number=number)
	if not patient: 
		return HttpResponseNotFound()
	return HttpResponse(content="We did not understand your message. Reply 'help' for a list of available commands.")

def handle_text(request):
	if isAck(request.GET['Body']):
		return processAck(request.GET['From'], request.GET['Body'])
	elif isQuit(request.GET['Body']):
		return processQuit(request.GET['From'])
	else:
		return processUnknown(request.GET['From'])


