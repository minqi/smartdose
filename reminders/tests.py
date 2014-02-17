from django.test import TestCase
from common.models import UserProfile, Drug
from django.template.loader import render_to_string
from django.test import Client
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotFound
from doctors.models import DoctorProfile
from freezegun import freeze_time
from patients.models import PatientProfile
from reminders.models import ReminderTime, Prescription, Message, SentReminder
from reminders import models as reminder_model
from reminders import tasks as reminder_tasks
from reminders import views as reminder_views
from common.utilities import DatetimeStub, SMSLogger
from configs.dev import settings
import os, sys
import datetime
from configs.dev.settings import MESSAGE_CUTOFF
from reminders.notification_center import NotificationCenter

class NotificationCenterTest(TestCase):
	def setUp(self):
		self.nc = NotificationCenter()
		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=date(year=1990, month=8, day=7))
		self.patient2 = PatientProfile.objects.create(first_name="Matt", last_name="Gaba",
								 				  primary_phone_number="2147094720", 
								 				  birthday=date(year=1989, month=10, day=13))
		self.doctor = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher", 
			primary_phone_number="2029163381", birthday=date(1960, 1, 1))
		self.drug1 = Drug.objects.create(name='advil')
		self.prescription1 = Prescription.objects.create(prescriber=self.doctor, 
			patient=self.patient1, drug=self.drug1, filled=True)
		self.prescription2 = Prescription.objects.create(prescriber=self.doctor, 
			patient=self.patient1, drug=self.drug1)

		# create a bunch of medication notifications
		self.now_datetime = datetime.now()
		self.old_send_datetimes = []
		for i in range(5):
			send_datetime = self.now_datetime + timedelta(seconds=i*180)
			self.old_send_datetimes.append(send_datetime)
			ReminderTime.objects.create(to=self.patient1, 
				reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY, send_time=send_datetime)
		self.med_reminders = ReminderTime.objects.filter(
			to=self.patient1, reminder_type=ReminderTime.MEDICATION).order_by('send_time')

		(self.refill_reminder, self.med_reminder) = ReminderTime.objects.create_prescription_reminders(
			to=self.patient2, repeat=ReminderTime.DAILY, prescription=self.prescription2)

		self.safetynet_notification = ReminderTime.objects.create_safety_net_notification(to=self.patient1, text='testing')

	def test_merge_notifications(self):
		merged_reminders = self.nc.merge_notifications(self.med_reminders)
		ground_truth_merged_reminders = []
		reminder_group = []
		for reminder in self.med_reminders:
			reminder_group.append(reminder)
		ground_truth_merged_reminders.append(tuple(reminder_group))
		ground_truth_merged_reminders = tuple(ground_truth_merged_reminders)
		self.assertEqual(merged_reminders, ground_truth_merged_reminders)

	def test_send_message(self):
		self.patient1.status = UserProfile.ACTIVE
		self.nc.send_message(to=self.patient1, notifications=self.med_reminders,
			template='messages/medication_reminder.txt', context={'reminder_list':list(self.med_reminders)})

		# see if the right messages are created
		self.assertEqual(len(Message.objects.filter(patient=self.patient1)), 1)

		# # see if the right book-keeping is performed
		sent_notifications = SentReminder.objects.all()
		self.assertEqual(len(sent_notifications), len(self.med_reminders))
		for n in sent_notifications:
			self.assertTrue(n.reminder_time in self.med_reminders)

		ReminderTime.objects.update()
		self.assertTrue((self.med_reminders[0].send_time.day - datetime.now().day) == 1)

	def test_send_welcome_notifications(self):
		# check that the patient's status is NEW
		self.assertTrue(self.patient1.status == UserProfile.NEW)
		# see if a reminder is sent (shouldn't be)
		self.nc.send_notifications(to=self.patient1, notifications=self.med_reminders)
		self.assertEqual(len(Message.objects.filter(patient=self.patient1)), 0)

		# see if a welcome message is sent
		now_datetime = datetime.now()
		welcome_notification = ReminderTime.objects.create(to=self.patient1, 
			reminder_type=ReminderTime.WELCOME, repeat=ReminderTime.DAILY, send_time=now_datetime)
		self.nc.send_notifications(to=self.patient1, notifications=welcome_notification)

		# see if message is sent
		self.assertEqual(len(Message.objects.filter(patient=self.patient1)), 1)

		# see if the patient's status is changed from NEW to ACTIVE
		self.assertTrue(self.patient1.status == UserProfile.ACTIVE)

		# check that notification is deactivated
		welcome_notification = ReminderTime.objects.filter(pk=welcome_notification.pk)[0]
		self.assertTrue(welcome_notification.active == False)

	def test_send_refill_notifications(self):
		# see if you can send refill notification
		self.assertTrue(self.patient2.status == UserProfile.NEW)
		self.nc.send_notifications(to=self.patient2, notifications=self.refill_reminder)
		self.assertEqual(len(Message.objects.filter(patient=self.patient2)), 0)
		
		# see if refill is sent
		self.patient2.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient2, notifications=self.refill_reminder)
		self.assertEqual(len(Message.objects.filter(patient=self.patient2)), 1)

		# check that send_time is properly incremented
		self.refill_reminder = ReminderTime.objects.get(pk=self.refill_reminder.pk)
		self.assertTrue(self.refill_reminder.send_time.day > datetime.now().day)

	def test_send_medication_notifications(self):
		# see if you can send medication notification
		self.assertTrue(self.patient1.status == UserProfile.NEW)
		self.nc.send_notifications(to=self.patient1, notifications=self.med_reminder)
		self.assertEqual(len(Message.objects.filter(patient=self.patient2)), 0)
		
		# medication notification shouldn't be sent if prescription isn't filled
		self.patient2.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient2, notifications=self.med_reminder)
		self.assertEqual(len(Message.objects.filter(patient=self.patient2)), 0)

		# medication notification should be sent if prescription is filled
		self.prescription2.filled = True
		self.prescription2.save()
		self.nc.send_notifications(to=self.patient2, notifications=self.med_reminder)
		self.assertEqual(len(Message.objects.filter(patient=self.patient2)), 1)
		# # check that send_time is properly incremented
		self.med_reminder = ReminderTime.objects.get(pk=self.med_reminder.pk)
		self.assertTrue(self.med_reminder.send_time.day > datetime.now().day)

	def test_send_safetynet_notifications(self):
		# # see if safetynet notification is sent
		self.patient1.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient1, notifications=self.safetynet_notification)
		self.assertEqual(len(Message.objects.filter(patient=self.patient1)), 1)

		# check that safety-net notification is deactivated
		self.safetynet_notification = ReminderTime.objects.get(pk=self.safetynet_notification.pk)
		self.assertTrue(self.safetynet_notification.active == False)

	def test_send_notifications_deactivated_user(self):
		# Should not send messages to deactivated account
		self.patient1.status = UserProfile.QUIT
		self.patient1.save()
		now_datetime = datetime.now()
		notification = ReminderTime.objects.create(to=self.patient1, 
			reminder_type=ReminderTime.WELCOME, repeat=ReminderTime.DAILY, send_time=now_datetime)

		self.nc.send_notifications(self.patient1, notification)
		self.assertEqual(len(Message.objects.all()), 0)

	def test_send_notifications_activated_user(self):
		# Check that sending a notification to active creates message as expected
		self.patient1.status = UserProfile.ACTIVE
		self.patient1.save()
		now_datetime = datetime.now()
		notification = ReminderTime.objects.create(to=self.patient1, prescription=self.prescription1,
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY, send_time=now_datetime)

		self.nc.send_notifications(self.patient1, notification)
		self.assertEqual(len(Message.objects.all()), 1)

class WelcomeMessageTest(TestCase):
	def setUp(self):
		self.nc = NotificationCenter()
		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=date(year=1990, month=8, day=7))
		ReminderTime.objects.create_welcome_notification(to=self.patient1)
	def test_welcome_message(self):
		self.assertEqual(self.patient1.status, PatientProfile.NEW)
		
		# make sure welcome message was created
		now_datetime = datetime.now()
		notifications = ReminderTime.objects.reminders_at_time(now_datetime)
		self.assertEqual(len(notifications), 1) 
		self.assertEqual(notifications[0].reminder_type, ReminderTime.WELCOME)
		self.assertEqual(notifications[0].to, self.patient1)

		# after sending welcome, make sure patient is active and 
		# welcome notification is not
		self.nc.send_notifications(self.patient1, notifications)
		welcome_notification = ReminderTime.objects.filter(pk=notifications[0].pk)[0]
		self.assertEqual(welcome_notification.active,  False)
		self.assertEqual(self.patient1.status, PatientProfile.ACTIVE)

class UpdateSendDateTimeTest(TestCase):
	def setUp(self):
		reminder_model.datetime = DatetimeStub()
		self.test_datetime = datetime.now()

		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=date(year=1990, month=8, day=7))
		self.n_daily = ReminderTime(to=self.patient1, repeat=ReminderTime.DAILY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)
		self.n_weekly = ReminderTime(to=self.patient1, repeat=ReminderTime.WEEKLY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)
		self.n_monthly = ReminderTime(to=self.patient1, repeat=ReminderTime.MONTHLY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)
		self.n_yearly = ReminderTime(to=self.patient1, repeat=ReminderTime.YEARLY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)

	def tearDown(self):
		reminder_model.datetime.reset_now()
		
	def test_update_daily_send_time(self):
		future_datetime = self.test_datetime + timedelta(days=1)
		reminder_model.datetime.set_fixed_now(future_datetime)
		self.n_daily.update_to_next_send_time()
		self.n_daily = ReminderTime.objects.get(pk=self.n_daily.pk)
		self.assertTrue((self.n_daily.send_time - future_datetime).days == 1)

	def test_update_weekly_send_time(self):
		future_datetime = self.test_datetime + timedelta(days=7)
		reminder_model.datetime.set_fixed_now(future_datetime)
		self.n_weekly.update_to_next_send_time()
		self.n_weekly = ReminderTime.objects.get(pk=self.n_weekly.pk)
		self.assertTrue((self.n_weekly.send_time - future_datetime).days == 7)

	def test_update_monthly_send_time(self):
		future_datetime = self.test_datetime + timedelta(days=31)
		reminder_model.datetime.set_fixed_now(future_datetime)
		self.n_monthly.update_to_next_send_time()
		self.n_monthly = ReminderTime.objects.get(pk=self.n_monthly.pk)
		self.assertTrue((self.n_monthly.send_time.month - future_datetime.month) == 1)

	def test_update_yearly_send_time(self):
		future_datetime = self.test_datetime + timedelta(days=31)
		reminder_model.datetime.set_fixed_now(future_datetime)
		self.n_yearly.update_to_next_send_time()
		self.n_yearly = ReminderTime.objects.get(pk=self.n_yearly.pk)
		self.assertTrue((self.n_yearly.send_time.year - future_datetime.year) == 1)

class TestHelper():
	@staticmethod
	def advance_test_time_to_end_time_and_emulate_reminder_periodic_task(test, end_time, period):
		""" Advance test.current_time to end_time running sendRemindersForNow every period, where period is a timedelta object
		"""
		while test.current_time < end_time:
			reminder_tasks.sendRemindersForNow()
			test.current_time = test.current_time + period
			test.freezer = freeze_time(test.current_time)
			test.freezer.start()

class TestSMSResponsesToReminders(TestCase):
	#TODO(mgaba): Write tests for SMSResponsesToReminders:
	#TODO(mgaba): Test "hello" response
	#TODO(mgaba): Test number and letter response
	#TODO(mgaba): Test proper acknowledgment
	#TODO(mgaba): Test acknowledgment of just-acknowledged message
	#TODO(mgaba): Test acknowledgment with wrong message number
	#TODO(mgaba): Test a text from an unknown number
	#TODO(mgaba): Test an ack of a pharmacy refill reminder
	#TODO(mgaba): Test opt-out interaction
	def setUp(self):
		return

class TestSafetyNet(TestCase):
	#TODO(mgaba): Write tests for safety net
	#TODO(mgaba): Test case where safety net member is adherent
	#TODO(mgaba): Test case where safety net member is non-adherent
	#TODO(mgaba): Test the adding to safety net SMS
	#TODO(mgaba): Test safety net opt-out message
	def setUp(self):
		return

class TestPrimaryContact(TestCase):
	#TODO(mgaba): Write tests for primary contact
	#TODO(mgaba): Test signing-up primary contact
	#TODO(mgaba): Test case where primary contact receives messages
	def setUp(self):
		return

class TestReminderDelivery(TestCase):
	def setUp(self):
		self.vitamin = Drug.objects.create(name="vitamin")
		self.bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",
										   primary_phone_number="2029163381",
										   username="2029163381",
										   birthday=datetime.date(year=1960, month=10, day=20),
										   address_line1="4262 Cesar Chavez", postal_code="94131",
										   city="San Francisco", state_province="CA", country_iso_code="US")
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
												  primary_phone_number="8569067308",
												  birthday=datetime.date(year=1990, month=4, day=21),
												  gender=PatientProfile.MALE,
												  address_line1="4266 Cesar Chavez",
												  postal_code="94131",
												  city="San Francisco", state_province="CA", country_iso_code="US")
		# Set the time the test should begin
		self.current_time = datetime.datetime(year=2013, month=10, day=13, hour=11, minute=0)
		self.freezer = freeze_time(self.current_time)
		self.freezer.start()
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = codecs.open(settings.MESSAGE_LOG_FILENAME, 'w', settings.SMS_ENCODING) # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close()
	def tearDown(self):
		self.freezer.stop()

	# TEST 1: Test that a refill reminder is delivered daily.
	def test_daily_delivery(self):
		# Minqi is signed up for his daily vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
    												patient=self.minqi,
													drug=self.vitamin,
													note="To make you strong")
		expected_delivery_time = self.current_time + datetime.timedelta(hours=3)
		reminder_schedule = [[ReminderTime.DAILY, expected_delivery_time]]
		ReminderTime.objects.create_prescription_reminders_from_reminder_schedule(to=self.minqi,
																				  prescription=prescription,
																				  reminder_schedule=reminder_schedule)
		# Emulate the scheduler task and make sure no reminders are sent
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now expected_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, expected_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Advance time by a day
		old_delivery_time = expected_delivery_time
		expected_delivery_time = expected_delivery_time + datetime.timedelta(hours=24)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		# Make sure no reminders were sent in that time
		self.assertEqual(message.datetime_sent, old_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Time is now expected_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, expected_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)

	# TEST 2: Test that a prescription reminder is delivered bi-weekly.
	def test_biweekly_delivery(self):
		# Minqi is signed up for his biweekly vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           filled=True) # Mark as filled to avoid refill reminders
		sunday_delivery_time = self.current_time + datetime.timedelta(hours=3)
		tuesday_delivery_time = sunday_delivery_time + datetime.timedelta(days=2)
		reminder_schedule = [[ReminderTime.WEEKLY, sunday_delivery_time], [ReminderTime.WEEKLY, tuesday_delivery_time]]
		ReminderTime.objects.create_prescription_reminders_from_reminder_schedule(to=self.minqi,
		                                                                          prescription=prescription,
		                                                                          reminder_schedule=reminder_schedule)
		# Test the first weeks worth of messages
		# Emulate the scheduler task and make sure no reminders are sent
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, sunday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now sunday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, sunday_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Next sunday's delivery time is a week away
		old_delivery_time = sunday_delivery_time
		sunday_delivery_time = sunday_delivery_time + datetime.timedelta(weeks=1)
		# Advance to tuesday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, tuesday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message.datetime_sent, old_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Time is now tuesday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, tuesday_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)

		# Test the second weeks worth of messages
		# Next Tuesday's delivery time is a week away, so increment
		old_delivery_time = tuesday_delivery_time
		tuesday_delivery_time = tuesday_delivery_time + datetime.timedelta(weeks=1)
		# Advance to second week, sunday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, sunday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message.datetime_sent, old_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Time is now sunday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, sunday_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Advance to tuesday_delivery_time
		old_delivery_time = sunday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, tuesday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message.datetime_sent, old_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# This time, we should send the message at the appropriate time
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, tuesday_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)

	# TEST 3: Test that a prescription reminder is delivered monthly
	def test_monthly_delivery(self):
		#TODO(mgaba): SHORT CIRCUIT THE TEST FOR NOW UNTIL THE MONTHLY CODE GETS PUSHED
		return True
		# Minqi is signed up for his daily vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           filled=True) # Mark as filled to avoid refill reminders
		day_13_delivery_time = self.current_time + datetime.timedelta(hours=3)
		reminder_schedule = [[ReminderTime.MONTHLY, day_13_delivery_time]]
		ReminderTime.objects.create_prescription_reminders_from_reminder_schedule(to=self.minqi,
		                                                                          prescription=prescription,
		                                                                          reminder_schedule=reminder_schedule)
		# Test the first months message
		# Emulate the scheduler task and make sure no reminders are sent
		while current_time < day_13_delivery_time:
			reminder_tasks.sendRemindersForNow()
			current_time = current_time + datetime.timedelta(hours=1)
			freezer = freeze_time(current_time)
			freezer.start()
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, day_13_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now day_13_delivery_time, so make sure the message is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, day_13_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Advance to next month
		old_delivery_time = day_13_delivery_time
		day_13_delivery_time = day_13_delivery_time + datetime.timedelta(months=1)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, day_13_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message.datetime_sent, old_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		# Time is now day_13_delivery_time, so make sure the message is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, day_13_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)

	# TEST 4: Test the behavior after a user acks a refill reminder
	def test_refill_ack_and_medication_reminder(self):
		# Minqi is signed up for his daily vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong")
		delivery_time = self.current_time + datetime.timedelta(hours=3)
		reminder_schedule = [[ReminderTime.DAILY, delivery_time]]
		ReminderTime.objects.create_prescription_reminders_from_reminder_schedule(to=self.minqi,
		                                                                          prescription=prescription,
		                                                                          reminder_schedule=reminder_schedule)
		# Emulate the scheduler task and make sure no reminders are sent until it's time to send a reminder
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is delivery_time so make sure a refill reminder is sent
		refill_content = "It's important you fill your " + self.vitamin.name + " prescription as soon as possible. Reply '1' when you've received your medicine."
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message.datetime_sent, delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		self.assertEqual(message.content, refill_content)
		# User acknowledges they have received their prescription an hour after receiving refill reminder
		self.current_time = self.current_time + datetime.timedelta(hours=1)
		self.freezer = freeze_time(self.current_time)
		self.freezer.start()
		c = Client()
		c.get('/textmessage_response/', {'from': self.minqi.primary_phone_number, 'body': '1'})
		# Advance time another day and be sure no reminders are sent
		old_delivery_time = delivery_time
		delivery_time = delivery_time + datetime.timedelta(hours=24)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message.datetime_sent, old_delivery_time)
		self.assertEqual(message.to, self.minqi.primary_phone_number)
		self.assertEqual(message.content, refill_content)
		# Time is now delivery_time, so be sure the appropriate medication reminder is sent
		medicine_content = "Time to take your " + self.vitamin.name + ". Reply '1' when you finish."
		reminder_tasks.sendRemindersForNow()
		# Test the two most recent messages to be sure the med reminder was sent and a new refill reminder did not slip in there.
		messages = SMSLogger.getLastNSentMessages(2)
		self.assertEqual(messages[1].datetime_sent, delivery_time)
		self.assertEqual(messages[1].to, self.minqi.primary_phone_number)
		self.assertEqual(messages[1].content, medicine_content)
		self.assertEqual(messages[0].datetime_sent, old_delivery_time)
		self.assertEqual(messages[0].to, self.minqi.primary_phone_number)
		self.assertEqual(messages[0].content, refill_content)
