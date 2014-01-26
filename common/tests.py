"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import random
import string
from django.test import SimpleTestCase
from django.template import Context, Template
from configs.dev import settings
from datetime import datetime, date
from common.utilities import weekOfMonth, lastWeekOfMonth, DatetimeStub, sendTextMessageToNumber, getLastSentMessageContent, getLastNSentMessageContent
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from django.core.exceptions import ValidationError

class baseUserTest(SimpleTestCase):
	def test_create_user(self):
		# UserProfile is abstract so we'll test creating patients and doctors
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=date(year=2013, month=10, day=13))
		self.assertEqual(PatientProfile.objects.all().count(), 1) # Make sure record is added to database
		self.assertNotEqual(p.username, "")
		# Add a distinct user (doctor) with the same number and names. This can happen if this user is both a doctor and a patient. Also, if the hash in generateUsername() results in a collision, we still want to add the record and this tests for that case as well. Note that uniqueness is enforced at the doctor and patient model level.
		d = DoctorProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=date(year=2013, month=10, day=13))
		self.assertEqual(DoctorProfile.objects.all().count(), 1) # Make sure record is added to database
		self.assertNotEqual(d.username, "")

		# Creating another patient should yield a validation error
		with self.assertRaises(ValidationError): 
			PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=date(year=2013, month=10, day=13))

		# Creating another doctor should yield a validation error
		with self.assertRaises(ValidationError): 
			DoctorProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=date(year=2013, month=10, day=13))

class templateFilterTest(SimpleTestCase):
	def test_divide_filter(self):
		context = Context({'value':10 })
		t = Template('{% load utilities %}{{ value|divide:20 }}')
		self.assertEqual(t.render(context), '0.5')
		
		context = Context({'value':1 })
		t = Template('{% load utilities %}{{ value|divide:7|floatformat:2 }}')
		self.assertEqual(t.render(context), '0.14')

		with self.assertRaises(ValueError):
			context = Context({'value':'Hello' })
			t = Template('{% load utilities %}{{ value|divide:20 }}')
			t.render(context)

	def test_multiply_filter(self): 
		context = Context({'value':10 })
		t = Template('{% load utilities %}{{ value|multiply:20 }}')
		self.assertEqual(t.render(context), '200.0')
		
		context = Context({'value':1 })
		t = Template('{% load utilities %}{{ value|multiply:.5 }}')
		self.assertEqual(t.render(context), '0.5')

		with self.assertRaises(ValueError):
			context = Context({'value':'Hello' })
			t = Template('{% load utilities %}{{ value|multiply:20 }}')
			t.render(context)

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
		self.assertEquals(getLastSentMessageContent(), "2147094720: " + message1)
		message2 = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(20)) # a random message
		sendTextMessageToNumber(message2, "2147094720")
		self.assertEquals(getLastSentMessageContent(), "2147094720: " + message2)
		self.assertIn("2147094720: " + message1, getLastNSentMessageContent(2)) 
		self.assertIn("2147094720: " + message2, getLastNSentMessageContent(2))
		self.assertNotIn("2147094720: " + message1, getLastNSentMessageContent(1))

		message3 = message1 + '\n' + message2 # a random message
		sendTextMessageToNumber(message3, "2147094720")
		self.assertEquals(getLastSentMessageContent(), "2147094720: " + message1 + '|' + message2)

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