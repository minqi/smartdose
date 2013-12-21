"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import random
import string
from django.test import SimpleTestCase
from configs.dev import settings
from datetime import datetime
from common.utilities import weekOfMonth, lastWeekOfMonth, DatetimeStub, sendTextMessageToNumber, getLastSentMessageContent, getLastNSentMessageContent

class messageUtilitiesTest(SimpleTestCase):
	def setUp(self):
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close() 

	def tearDown(self):
			f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file.
			f.close() 

	def test_last_sent_message(self):
		self.assertEqual(getLastSentMessageContent(), "")
		message1 = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(8)) # a random message
		sendTextMessageToNumber(message1, "2147094720")
		self.assertEquals(getLastSentMessageContent(), "2147094720: " + message1 + "\n")
		message2 = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(20)) # a random message
		sendTextMessageToNumber(message2, "2147094720")
		self.assertEquals(getLastSentMessageContent(), "2147094720: " + message2 + "\n")
		self.assertIn("2147094720: " + message1 + "\n", getLastNSentMessageContent(2))
		self.assertIn("2147094720: " + message2 + "\n", getLastNSentMessageContent(2))
		self.assertNotIn("2147094720: " + message1 + "\n", getLastNSentMessageContent(1))

class datetimeUtilitiesTest(SimpleTestCase):
	def test_week_of_month(self):
		testtime = datetime(year=2013, month=11, day=17)
		# 11/17/2013 is the third Sunday of the month
		self.assertEqual(weekOfMonth(testtime), 3)
		testtime = datetime(year=2013, month=1, day=1)
		self.assertEqual(weekOfMonth(testtime), 1)
		testtime = datetime(year=2013, month=1, day=31)
		self.assertEqual(weekOfMonth(testtime), 5)
		testtime = datetime(year=2013, month=2, day=28)
		self.assertEqual(weekOfMonth(testtime), 4)
	def test_last_week_of_month(self):
		testtime = datetime(year=2013, month=11, day=17)
		self.assertFalse(lastWeekOfMonth(testtime)) # 11/17/2013 is the third Sunday of the month
		testtime = datetime(year=2013, month=1, day=1)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=1, day=21)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=2, day=21)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=5, day=24)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=2, day=22)
		self.assertTrue(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=2, day=28)
		self.assertTrue(lastWeekOfMonth(testtime))
		testtime = datetime(year=2013, month=5, day=31)
		self.assertTrue(lastWeekOfMonth(testtime))
	def test_datetime_stub(self):
		dtstub = DatetimeStub.datetime(year=2013, month=11, day=3)
		# Assert dtstub possesses datetime attributes
		self.assertEqual(dtstub.year, 2013)
		self.assertEqual(dtstub.month, 11)
		self.assertEqual(dtstub.day, 3)
		# Assert dtstub returns the default value for now()
		dtstub_now = dtstub.now()
		datetime_now = datetime.now()
		self.assertEqual(dtstub_now.year, datetime_now.year)
		self.assertEqual(dtstub_now.month, datetime_now.month)
		self.assertEqual(dtstub_now.day, datetime_now.day)
		self.assertEqual(dtstub_now.minute, datetime_now.minute)
		self.assertEqual(dtstub_now.second, datetime_now.second)
		# Set a new now() value and test if behaves as expected
		arbitrary_datetime = datetime(year=2012, month=11, day=3)
		DatetimeStub.set_fixed_now(arbitrary_datetime)
		dtstub_now = dtstub.now()
		self.assertEqual(dtstub_now.year, arbitrary_datetime.year)
		self.assertEqual(dtstub_now.month, arbitrary_datetime.month)
		self.assertEqual(dtstub_now.day, arbitrary_datetime.day)
		self.assertEqual(dtstub_now.minute, arbitrary_datetime.minute)
		self.assertEqual(dtstub_now.second, arbitrary_datetime.second)
		# What happens when we reset the fixed now?
		DatetimeStub.reset_now()
		dtstub_now = dtstub.now()
		datetime_now = datetime.now()
		self.assertEqual(dtstub_now.year, datetime_now.year)
		self.assertEqual(dtstub_now.month, datetime_now.month)
		self.assertEqual(dtstub_now.day, datetime_now.day)
		self.assertEqual(dtstub_now.minute, datetime_now.minute)
		self.assertEqual(dtstub_now.second, datetime_now.second)