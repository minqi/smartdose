# Create your views here.
from django.conf import settings
from django.http import HttpResponse
from twilio.rest import TwilioRestClient

# Construct our client for communicating with Twilio service
twilio_client = TwilioRestClient(configs.dev.settings.TWILIO_ACCOUNT_SID, 
								 configs.dev.settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_NUMBER

# An example function to test communictation with Twilio
# def helloTwilio(request):
# 	# Send message
# 	message = twilio_client.sms.messages.create(body="Twilio is working",
# 										to="+12147094720",
# 										from_=twilio_number)
# 	return HttpResponse('')