"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import random
import string
from django.test import SimpleTestCase, TestCase
from django.template import Context, Template
from configs.dev import settings
from common.utilities import weekOfMonth, lastWeekOfMonth, DatetimeStub, sendTextMessageToNumber, getLastSentMessageContent, getLastNSentMessageContent
from django.contrib.auth import authenticate
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from django.core.exceptions import ValidationError
from freezegun import freeze_time
import datetime




class baseUserTest(TestCase):
	def test_create_user(self):
		# UserProfile is abstract so we'll test creating patients and doctors
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		self.assertEqual(PatientProfile.objects.all().count(), 1) # Make sure record is added to database
		self.assertNotEqual(p.username, "")
		# Add a distinct user (doctor) with the same number and names. This can happen if this user is both a doctor and a patient.
		d = DoctorProfile.objects.create(email="dr.gaba@ucsf.edu", primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		self.assertEqual(DoctorProfile.objects.all().count(), 1) # Make sure record is added to database
		self.assertNotEqual(d.username, "")

		# Creating another patient with the same number should yield a validation error
		with self.assertRaises(ValidationError): 
			PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))

		# Creating another doctor should yield a validation error
		with self.assertRaises(ValidationError): 
			DoctorProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))

class templateFilterTest(TestCase):
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

class messageUtilitiesTest(TestCase):
	def setUp(self):
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close() 

	def tearDown(self):
			f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file.
			f.close() 

	def test_last_sent_message(self):
		# Send random text messages and assert that the random text messages are validly retrieved from a call to getLastSentMessageContent() and getLastNSentMessageContent()
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

class datetimeUtilitiesTest(TestCase):
	def test_week_of_month(self):
		testtime = datetime.datetime(year=2013, month=11, day=17)
		# 11/17/2013 is the third Sunday of the month
		self.assertEqual(weekOfMonth(testtime), 3)
		testtime = datetime.datetime(year=2013, month=1, day=1)
		self.assertEqual(weekOfMonth(testtime), 1)
		testtime = datetime.datetime(year=2013, month=1, day=31)
		self.assertEqual(weekOfMonth(testtime), 5)
		testtime = datetime.datetime(year=2013, month=2, day=28)
		self.assertEqual(weekOfMonth(testtime), 4)
	def test_last_week_of_month(self):
		testtime = datetime.datetime(year=2013, month=11, day=17)
		self.assertFalse(lastWeekOfMonth(testtime)) # 11/17/2013 is the third Sunday of the month
		testtime = datetime.datetime(year=2013, month=1, day=1)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime.datetime(year=2013, month=1, day=21)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime.datetime(year=2013, month=2, day=21)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime.datetime(year=2013, month=5, day=24)
		self.assertFalse(lastWeekOfMonth(testtime))
		testtime = datetime.datetime(year=2013, month=2, day=22)
		self.assertTrue(lastWeekOfMonth(testtime))
		testtime = datetime.datetime(year=2013, month=2, day=28)
		self.assertTrue(lastWeekOfMonth(testtime))
		testtime = datetime.datetime(year=2013, month=5, day=31)
		self.assertTrue(lastWeekOfMonth(testtime))
	def test_datetime_stub(self):
		dtstub = DatetimeStub.datetime(year=2013, month=11, day=3)
		# Assert dtstub possesses datetime attributes
		self.assertEqual(dtstub.year, 2013)
		self.assertEqual(dtstub.month, 11)
		self.assertEqual(dtstub.day, 3)
		# Assert dtstub returns the default value for now()
		dtstub_now = dtstub.now()
		datetime_now = datetime.datetime.now()
		self.assertEqual(dtstub_now.year, datetime_now.year)
		self.assertEqual(dtstub_now.month, datetime_now.month)
		self.assertEqual(dtstub_now.day, datetime_now.day)
		self.assertEqual(dtstub_now.minute, datetime_now.minute)
		self.assertEqual(dtstub_now.second, datetime_now.second)
		# Set a new now() value and test if behaves as expected
		arbitrary_datetime = datetime.datetime(year=2012, month=11, day=3)
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
		datetime_now = datetime.datetime.now()
		self.assertEqual(dtstub_now.year, datetime_now.year)
		self.assertEqual(dtstub_now.month, datetime_now.month)
		self.assertEqual(dtstub_now.day, datetime_now.day)
		self.assertEqual(dtstub_now.minute, datetime_now.minute)
		self.assertEqual(dtstub_now.second, datetime_now.second)








class authenticationTest(TestCase):
    # TEST 1: User creation and valid auth token login-----------------
	def test_valid_token_authentication(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# A user clicks the link to get authenticated and log in, 45 seconds after receiving the message
		current_time = current_time+datetime.timedelta(seconds=45)
		freezer = freeze_time(current_time)
		freezer.start()
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=p.auth_token)
		self.assertEqual(authenticated_p, p)
		self.assertTrue(authenticated_p.is_authenticated())
		freezer.stop()

	# TEST 2: Attack simple scenario where attacker is guessing token-----------------
	def test_invalid_token_authentication(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba",
		                                  birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		current_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# An attacker guesses to get authenticated and log in, 45 seconds after receiving the message
		current_time = current_time+datetime.timedelta(seconds=45)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = 'u69zw'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		freezer.stop()

	# TEST 3: Test scenario where token is invalidated and user signs in after token invalidation
	def test_auth_token_invalidation(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# An attacker guesses token to get authenticated and log in, 45 seconds after receiving the message
		current_time = current_time+datetime.timedelta(seconds=45)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = 'u69zw'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		# A user clicks link to sign in 15 seconds later
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		# User clicks the link
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=p.auth_token)
		# User fails authentication because token was rendered invalid by guess
		self.assertEqual(authenticated_p, None)
		# A new token is generated when the authentication fails
		p.generate_auth_token()
		# 10 seconds later, user clicks link
		current_time = current_time+datetime.timedelta(seconds=10)
		freezer = freeze_time(current_time)
		freezer.start()
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=p.auth_token)
		self.assertEqual(authenticated_p, p)
		self.assertTrue(authenticated_p.is_authenticated())
		freezer.stop()

	# TEST 4: Test scenario where user tries signing-in more than two minutes after generating token
	def test_token_timeout(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# A user clicks the link to get authenticated and log in, 121 seconds after receiving the message
		current_time = current_time+datetime.timedelta(seconds=121)
		freezer = freeze_time(current_time)
		freezer.start()
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=p.auth_token)
		self.assertEqual(authenticated_p, None)
		freezer.stop()

	# TEST 5: Test scenario where user tries signing-in just before token expires
	def test_almost_token_timeout(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# A user clicks the link to get authenticated and log in, 119 seconds after receiving the message
		current_time = current_time+datetime.timedelta(seconds=119)
		freezer = freeze_time(current_time)
		freezer.start()
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=p.auth_token)
		self.assertEqual(authenticated_p, p)
		freezer.stop()

	# TEST 6: Test scenario where attacker tries using same token after user has signed in
	def test_invalidation_on_authentication(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# A user clicks the link to get authenticated and log in, 15 seconds after receiving the message
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=p.auth_token)
		self.assertEqual(authenticated_p, p)
		# Attacker tries signing in as user 1 second after user has signed in
		current_time = current_time+datetime.timedelta(seconds=1)
		freezer = freeze_time(current_time)
		freezer.start()
		attacker_p = authenticate(phone_number=p.primary_phone_number, auth_token=p.auth_token)
		self.assertEqual(attacker_p, None)
		freezer.stop()

	# Test 7: Test scenario where attacker tries guessing and is locked out of the account
	def test_invalid_guess_limit(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# An attacker makes a guess, then generates a new auth token
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = '18feZ'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		p = PatientProfile.objects.get(pk=p.pk)
		p.generate_auth_token()
		# An attacker makes another guess, then generates a new auth token
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = '1aaz9'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		p = PatientProfile.objects.get(pk=p.pk)
		p.generate_auth_token()
		# An attacker makes another, correct guess
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = p.auth_token
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		freezer.stop()

	# Test 8: Test scenario where user incorrectly types token, waits, and then successfully logs in
	def test_invalid_guess_limit(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		p.generate_auth_token()
		# A user incorrectly types the token
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = '18feZ'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		p = PatientProfile.objects.get(pk=p.pk)
		p.generate_auth_token()
		# A user incorrectly types the token
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = '1aaz9'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		p = PatientProfile.objects.get(pk=p.pk)
		p.generate_auth_token()
		# A user correctly types the token, but has exceeded number of guesses
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = p.auth_token
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		p = PatientProfile.objects.get(pk=p.pk)
		p.generate_auth_token()
		# A user waits ten minutes and incorrectly types the token
		current_time = current_time+datetime.timedelta(minutes=10)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = '10va2'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, None)
		p = PatientProfile.objects.get(pk=p.pk)
		p.generate_auth_token()
		# A user finally gets it right and should be authenticated
		current_time = current_time+datetime.timedelta(seconds=15)
		freezer = freeze_time(current_time)
		freezer.start()
		token_guess = p.auth_token
		authenticated_p = authenticate(phone_number=p.primary_phone_number, auth_token=token_guess)
		self.assertEqual(authenticated_p, p)
		freezer.stop()

	# TEST 9: User creation and valid password login
	def test_valid_password_authentication(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		user_password = 'hello'
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		p.set_password(user_password)
		p.save()
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		authenticated_p = authenticate(phone_number=p.primary_phone_number, password=user_password)
		self.assertEqual(authenticated_p, p)
		self.assertTrue(authenticated_p.is_authenticated())
		freezer.stop()

	# TEST 10: User creation and invalid password login
	def test_invalid_password_authentication(self):
		# A user signs up for our system at 2/11/2014:00:00:00
		current_time = datetime.datetime(year=2014, month=2, day=11)
		freezer = freeze_time(current_time)
		freezer.start()
		user_password = 'hello'
		p = PatientProfile.objects.create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday=datetime.date(year=2013, month=10, day=13))
		p.set_password(user_password)
		p.save()
		# A user gets sent an upsale link with an auth token 20 minutes after signing up.
		curent_time = current_time+datetime.timedelta(minutes=20)
		freezer = freeze_time(current_time)
		freezer.start()
		wrong_password = 'helli'
		authenticated_p = authenticate(phone_number=p.primary_phone_number, password=wrong_password)
		self.assertEqual(authenticated_p, None)
		freezer.stop()
