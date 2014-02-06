# Django imports 
from configs.dev import settings
# Twilio imports
from twilio.rest import TwilioRestClient
# Python imports
import datetime as datetime_orig
from datetime import timedelta
from math import ceil, floor
from configs.dev.settings import REMINDER_SWEEP_OFFSET

# Construct our client for communicating with Twilio service
twilio_client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, 
								 settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_NUMBER


def sendTextMessageToNumber(body, to):
	if not settings.DEBUG:
		message = twilio_client.sms.messages.create(body=body, to=to, from_=twilio_number)

	log_body = body.replace('\n', '|') # Replace '\n' with '|' in the logs so that '\n' will only be used to serialize messages
	f = open(settings.MESSAGE_LOG_FILENAME, 'a')
	f.write(to + ": " + log_body + "\n")
	f.close()
	return True

def getLastSentMessageContent():
	"""Content in format "<number>: <message body>" 
		Note: Newline (\n) are replaced with the '|' symbol """
	if not settings.DEBUG:
		raise Exception("getLastSentMessageContent should only be used in test setting")

	f = open(settings.MESSAGE_LOG_FILENAME, 'r')
	# Iterate through file until we get to last line of file
	message = ""
	for message in f:pass
	f.close()
	return message.rstrip('\n')

def getLastNSentMessageContent(n):
	"""Content in format "<number>: <message body>"
		Note: Newline (\n) are replaced with the '|' symbol """

	if not settings.DEBUG:
		raise Exception("getLastNSentMessageContent should only be used in test setting")
	l = []
	f = open(settings.MESSAGE_LOG_FILENAME, 'r')
	# Iterate through file until we get to last line of file
	for message in f: l.append(message.rstrip('\n'))
	f.close()
	l = l[-n:] # reverse array so most recently sent message is first
	return l

def weekOfMonth(dt):
	"""Returns which week a day of a month falls in. 
	For example, Thursday, May 9th, 2013 is the 2nd Tuesday of the month"""
	return ceil(dt.day / 7.0)

def lastWeekOfMonth(dt):
	"""Returns whether the day for the given datetime fall in the last week of the month"""
	next_week = dt + timedelta(weeks=1)
	if dt.month == next_week.month:
		return False
	else:
		return True

def is_today(dt): #TODO(minqi):test
	"""Return True if dt is a time in today"""
	dt_time = dt.date()
	today = datetime_orig.datetime.now().date()
	return dt_time == today

# def is_within_timeframe_past(dt): #TODO(minqi):test
# 	"""Return True if dt is a time within REMINDER_SWEEP_OFFSET minutes"""
# 	now_time = datetime_orig.datetime.now()
# 	minutes = (now_time - dt).seconds/60.0

# 	return minutes < REMINDER_SWEEP_OFFSET

class DatetimeStub(object):
	"""
	A datetimestub object to replace methods and classes from 
	the datetime module. 
	"""
	fixed_now = None; 
	class datetime(datetime_orig.datetime):
		@classmethod      
		def now(self):
			if DatetimeStub.fixed_now:
				return DatetimeStub.fixed_now;
			else:
				return datetime_orig.datetime.now();
	
	@classmethod
	def set_fixed_now(self, dt):
		self.fixed_now = dt;
	@classmethod
	def reset_now(self):
		self.fixed_now = None;

	def __getattr__(self, attr):
		"""Get the default implementation for the classes and methods
		from datetime that are not replaced
		"""
		return getattr(datetime_orig, attr)
