# Django imports 
from django.conf import settings
from twilio.rest import TwilioRestClient
# Python imports
from datetime import datetime, timedelta
from math import ceil, floor

# Construct our client for communicating with Twilio service
twilio_client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, 
								 settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_NUMBER


def sendTextMessageToNumber(body, to):
	if settings.SEND_TEXT_MESSAGE:
		message = twilio_client.sms.messages.create(body=body, to=to, from_=twilio_number)
	else:
		message = "Sending to " + to + " message " + body 
		print message
	return True


# Returns which week a day of a month falls in. 
# For example, Thursday, May 9th, 2013 is the 2nd Tuesday of the month.
def weekOfMonth(datetime):
	return ceil(datetime.day / 7.0)

# Returns whether the day for the given datetime fall in the last week of the month
def lastWeekOfMonth(datetime):
	next_week = datetime + timedelta(weeks=1)
	if datetime.month == next_week.month:
		return False
	else:
		return True