import codecs
from django.test import TestCase
from common.models import UserProfile, Drug
from django.test import Client
from doctors.models import DoctorProfile
from freezegun import freeze_time
from patients.models import PatientProfile
from reminders.models import ReminderTime, Prescription, Message, SentReminder
from reminders import tasks as reminder_tasks
from common.utilities import SMSLogger
from configs.dev import settings
import datetime


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
		# Minqi is signed up for his daily vitamin reminder. He'll receive refill reminders
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong")
		expected_delivery_time = self.current_time + datetime.timedelta(hours=3)
		reminder_schedule = [[ReminderTime.DAILY, expected_delivery_time]]
		ReminderTime.objects.create_prescription_reminders_from_reminder_schedule(to=self.minqi,
		                                                                          prescription=prescription,
		                                                                          reminder_schedule=reminder_schedule)
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		# Emulate the scheduler task and make sure no reminders are sent
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now expected_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Advance time by a day
		old_delivery_time = expected_delivery_time
		expected_delivery_time = expected_delivery_time + datetime.timedelta(hours=24)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		# Make sure no reminders were sent in that time
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now expected_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

	# TEST 2: Test that a prescription reminder is delivered bi-weekly.
	def test_biweekly_delivery(self):
		# Minqi is signed up for his biweekly vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           filled=True) # Mark as filled to receive medication reminders
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
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
		self.assertEqual(message['datetime_sent'], sunday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Next sunday's delivery time is a week away
		old_delivery_time = sunday_delivery_time
		sunday_delivery_time = sunday_delivery_time + datetime.timedelta(weeks=1)
		# Advance to tuesday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, tuesday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now tuesday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], tuesday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

		# Test the second weeks worth of messages
		# Next Tuesday's delivery time is a week away, so increment
		old_delivery_time = tuesday_delivery_time
		tuesday_delivery_time = tuesday_delivery_time + datetime.timedelta(weeks=1)
		# Advance to second week, sunday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, sunday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now sunday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], sunday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Advance to tuesday_delivery_time
		old_delivery_time = sunday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, tuesday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# This time, we should send the message at the appropriate time
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], tuesday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

	# TEST 3: Test that a prescription reminder is delivered monthly
	def test_monthly_delivery(self):
		# Minqi is signed up for his daily vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           filled=True) # Mark as filled to avoid refill reminders
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		expected_delivery_time = self.current_time + datetime.timedelta(hours=3)
		reminder_schedule = [[ReminderTime.MONTHLY, expected_delivery_time]]
		ReminderTime.objects.create_prescription_reminders_from_reminder_schedule(to=self.minqi,
		                                                                          prescription=prescription,
		                                                                          reminder_schedule=reminder_schedule)
		# Test the first months message
		# Emulate the scheduler task and make sure no reminders are sent
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now expected_delivery_time, so make sure the message is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Advance to next month
		old_delivery_time = expected_delivery_time
		# First reminder is sent on 10/13/2013. Second reminder will be sent a month later on 11/13/2013
		expected_delivery_time = datetime.datetime.combine(datetime.date(year=2013, month=11, day=13), expected_delivery_time.time())
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now expected_delivery_time, so make sure the message is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

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
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		# Emulate the scheduler task and make sure no reminders are sent until it's time to send a reminder
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is delivery_time so make sure a refill reminder is sent
		refill_content = "It's important you fill your " + self.vitamin.name + " prescription as soon as possible. Reply '1' when you've received your medicine."
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		self.assertEqual(message['content'], refill_content)
		# User acknowledges they have received their prescription an hour after receiving refill reminder
		self.current_time = self.current_time + datetime.timedelta(hours=1)
		self.freezer = freeze_time(self.current_time)
		self.freezer.start()
		c = Client()
		c.get('/textmessage_response/', {'From': self.minqi.primary_phone_number, 'Body': '1'})
		# Advance time another day and be sure no reminders are sent
		old_delivery_time = delivery_time
		delivery_time = delivery_time + datetime.timedelta(hours=24)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		self.assertEqual(message['content'], refill_content)
		# Time is now delivery_time, so be sure the appropriate medication reminder is sent
		medicine_content = "Time to take your " + self.vitamin.name + ". Reply '1' when you finish."
		reminder_tasks.sendRemindersForNow()
		# Test the two most recent messages to be sure the med reminder was sent and a new refill reminder did not slip in there.
		messages = SMSLogger.getLastNSentMessages(2)
		self.assertEqual(messages[1]['datetime_sent'], delivery_time)
		self.assertEqual(messages[1]['to'], self.minqi.primary_phone_number)
		self.assertEqual(messages[1]['content'], medicine_content)
		self.assertEqual(messages[0]['datetime_sent'], old_delivery_time)
		self.assertEqual(messages[0]['to'], self.minqi.primary_phone_number)
		self.assertEqual(messages[0]['content'], refill_content)
