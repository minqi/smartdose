from configs.dev import settings
import twilio
from twilio.rest import TwilioRestClient
import datetime as datetime_orig
import codecs
from datetime import timedelta
from math import ceil, floor
from django.db import models
import phonenumbers

# Construct our client for communicating with Twilio service
twilio_client = TwilioRestClient(settings.TWILIO_ACCOUNT_SID, 
								 settings.TWILIO_AUTH_TOKEN)
twilio_number = settings.TWILIO_NUMBER

class SMSLogger():
	""" Used to log sent SMS content to a file and read back SMS content from file
	"""
	# See Unicode private use areas: http://en.wikipedia.org/wiki/Private_Use_Areas
	DATETIME_DELIMITER = u'\uE000'
	TO_NUMBER_DELIMITER = u'\uE001'
	CONTENT_DELIMITER = u'\uE002'
	NEWLINE_ENCODER = u'\uE003'
	@staticmethod
	def _decode_log(string):
		if string == "" or string == None or string == "\n":
			return None
		# Decode datetime from log
		datetime_sent = datetime_orig.datetime.strptime(string[0:string.index(SMSLogger.DATETIME_DELIMITER)], '%Y-%m-%d %H:%M:%S')
		# Decode to number from log
		to = string[string.index(SMSLogger.DATETIME_DELIMITER)+1:string.index(SMSLogger.TO_NUMBER_DELIMITER)]
		# Decode content from log
		content = string[string.index(SMSLogger.TO_NUMBER_DELIMITER)+1:string.index(SMSLogger.CONTENT_DELIMITER)]
		message_log_entry = type('message_log_entry', (object,),
			{'datetime_sent':datetime_sent, 'to':to, 'content':content})()
		return message_log_entry
	@staticmethod
	def getLastSentMessage():
		if not settings.DEBUG:
			raise Exception("getLastSentMessageContent should only be used in test setting")

		f = codecs.open(settings.MESSAGE_LOG_FILENAME, 'r', encoding=settings.SMS_ENCODING)
		# Iterate through file until we get to last line of file
		line = ""
		for line in f:
			pass
		f.close()
		return SMSLogger._decode_log(line)
	@staticmethod
	def getLastNSentMessages(n):
		if not settings.DEBUG:
			raise Exception("getLastNSentMessageContent should only be used in test setting")
		l = []
		f = codecs.open(settings.MESSAGE_LOG_FILENAME, 'r', encoding=settings.SMS_ENCODING)
		# Iterate through file until we get to last line of file
		for message in f: l.append(message.rstrip('\n'))
		f.close()
		l = l[-n:] # reverse array so most recently sent message is first
		messages = []
		for line in l:
			messages.append(SMSLogger._decode_log(line))
		return messages
	@staticmethod
	def log(to_number, content, datetime_sent):
		log_body = content.replace('\n', SMSLogger.NEWLINE_ENCODER) # Replace '\n' with "Information seperator four" in the logs so that '\n' will only be used to serialize messages
		f = codecs.open(settings.MESSAGE_LOG_FILENAME, 'a', encoding=settings.SMS_ENCODING)
		f.write(str(datetime_sent) + SMSLogger.DATETIME_DELIMITER + to_number + SMSLogger.TO_NUMBER_DELIMITER + log_body + SMSLogger.CONTENT_DELIMITER + "\n")
		f.close()

def sendTextMessageToNumber(body, to):
	if not settings.DEBUG:
		try: 
			# just send first 160 char for now; plan to support concatenation in the future
			body = body[:settings.TWILIO_MAX_SMS_LEN] #
			message = twilio_client.messages.create(body=body, to=to, from_=twilio_number)
		except twilio.TwilioRestException as e:
			print e

	SMSLogger.log(to, body, datetime_orig.datetime.now())
	return True

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

def is_integer(s):
	try:
		int(s)
		return True
	except ValueError:
		return False

def list_to_queryset(l):
	"""
	Takes a list of instances all of the same Model subclass
	and returns a QuerySet. Note this function assumes all
	QuerySet objects are represented within the database.
	"""
	if l:
		class_name = l[0].__class__.__name__
		class_object = l[0].__class__
		for item in l:
			if item.__class__.__name__ != class_name:
				return None
			if not isinstance(item, models.Model):
				return None

		item_pks = set([item.pk for item in l])
		return class_object.objects.filter(pk__in=item_pks)
	return None

def convert_to_e164(raw_phone):
	"""
	Convert a raw phone number string to E.164 format
	"""
	if not raw_phone:
		return

	if raw_phone[0] == '+':
		# Phone number may already be in E.164 format.
		parse_type = None
	else:
		# If no country code information present, assume it's a US number
		parse_type = "US"

	phone_representation = phonenumbers.parse(raw_phone, parse_type)

	return phonenumbers.format_number(phone_representation,
		phonenumbers.PhoneNumberFormat.E164)

def next_weekday(d, weekday):
	"""
	Get datetime of next day after datetime <d> that is a <weekday>
	"""
	days_ahead = weekday - d.weekday()
	if days_ahead <= 0: # Target day already happened this week
		days_ahead += 7
	return d + datetime_orig.timedelta(days_ahead)