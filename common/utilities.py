# This file contains utility functions. For example, sending text messages
from django.conf import settings
from twilio.rest import TwilioRestClient

# Construct our client for communicating with Twilio service
twilio_client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, 
								 settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_NUMBER


def sendTextMessage(body, to):
	message = twilio_client.sms.messages.create(body=body, to=to, from_=twilio_number)
	return True

