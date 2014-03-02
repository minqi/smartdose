import codecs
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
from common.utilities import SMSLogger
from configs.dev import settings
import os, sys
import datetime
from configs.dev.settings import MESSAGE_CUTOFF
from reminders.notification_center import NotificationCenter
from reminders.response_center import ResponseCenter


class NotificationCenterTest(TestCase):
	def setUp(self):
		self.nc = NotificationCenter()
		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=datetime.date(year=1990, month=8, day=7))
		self.patient2 = PatientProfile.objects.create(first_name="Matt", last_name="Gaba",
								 				  primary_phone_number="2147094720", 
								 				  birthday=datetime.date(year=1989, month=10, day=13))
		self.doctor = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher", 
			primary_phone_number="2029163381", birthday=datetime.date(1960, 1, 1))
		self.drug1 = Drug.objects.create(name='advil')
		self.prescription1 = Prescription.objects.create(prescriber=self.doctor, 
			patient=self.patient1, drug=self.drug1, filled=True)
		self.prescription2 = Prescription.objects.create(prescriber=self.doctor, 
			patient=self.patient1, drug=self.drug1)

		# create a bunch of medication notifications
		self.now_datetime = datetime.datetime.now()
		self.old_send_datetimes = []
		for i in range(5):
			send_datetime = self.now_datetime + datetime.timedelta(seconds=i*180)
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
		sent_time = datetime.datetime.now()
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
		self.assertTrue((self.med_reminders[0].send_time.date() - sent_time.date()).days == 1)

	def test_send_welcome_notifications(self):
		# check that the patient's status is NEW
		self.assertTrue(self.patient1.status == UserProfile.NEW)
		# see if a reminder is sent (shouldn't be)
		self.nc.send_notifications(to=self.patient1, notifications=self.med_reminders)
		self.assertEqual(len(Message.objects.filter(patient=self.patient1)), 0)

		# see if a welcome message is sent
		now_datetime = datetime.datetime.now()
		welcome_notification = ReminderTime.objects.create(to=self.patient1, 
			reminder_type=ReminderTime.WELCOME, repeat=ReminderTime.DAILY, send_time=now_datetime)
		self.nc.send_notifications(to=self.patient1, notifications=welcome_notification)

		# see if message is sent
		self.assertEqual(len(Message.objects.filter(patient=self.patient1)), 1)

		# see if message number is not set
		self.assertEqual(Message.objects.filter(patient=self.patient1)[0].message_number, None)

		# see if the patient's status is changed from NEW to ACTIVE
		self.assertTrue(self.patient1.status == UserProfile.ACTIVE)

		# check that notification is deactivated
		welcome_notification = ReminderTime.objects.filter(pk=welcome_notification.pk)[0]
		self.assertTrue(welcome_notification.active == False)

	def test_send_refill_notifications(self):
		# see if you can send refill notification
		self.assertTrue(self.patient2.status == UserProfile.NEW)
		sent_time = datetime.datetime.now()
		self.nc.send_notifications(to=self.patient2, notifications=self.refill_reminder)
		self.assertEqual(len(Message.objects.filter(patient=self.patient2)), 0)
		
		# see if refill is sent
		self.patient2.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient2, notifications=self.refill_reminder)
		self.assertEqual(len(Message.objects.filter(patient=self.patient2)), 1)

		# see if message number is set
		self.assertEqual(Message.objects.filter(patient=self.patient2)[0].message_number, 1)

		# check that send_time is properly incremented
		self.refill_reminder = ReminderTime.objects.get(pk=self.refill_reminder.pk)
		self.assertTrue((self.refill_reminder.send_time.date() - sent_time.date()).days == 1)

	def test_send_medication_notifications(self):
		# see if you can send medication notification
		self.assertTrue(self.patient1.status == UserProfile.NEW)
		sent_time = datetime.datetime.now()
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

		# see if message number is set
		self.assertEqual(Message.objects.filter(patient=self.patient2)[0].message_number, 1)
		# # check that send_time is properly incremented
		self.med_reminder = ReminderTime.objects.get(pk=self.med_reminder.pk)
		self.assertTrue((self.med_reminder.send_time.date() - sent_time.date()).days == 1)

	def test_send_safetynet_notifications(self):
		# # see if safetynet notification is sent
		self.patient1.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient1, notifications=self.safetynet_notification)
		self.assertEqual(len(Message.objects.filter(patient=self.patient1)), 1)

		# see if message number is not set
		self.assertEqual(Message.objects.filter(patient=self.patient1)[0].message_number, None)

		# check that safety-net notification is deactivated
		self.safetynet_notification = ReminderTime.objects.get(pk=self.safetynet_notification.pk)
		self.assertTrue(self.safetynet_notification.active == False)

	def test_send_notifications_deactivated_user(self):
		# Should not send messages to deactivated account
		self.patient1.status = UserProfile.QUIT
		self.patient1.save()
		now_datetime = datetime.datetime.now()
		notification = ReminderTime.objects.create(to=self.patient1, 
			reminder_type=ReminderTime.WELCOME, repeat=ReminderTime.DAILY, send_time=now_datetime)

		self.nc.send_notifications(self.patient1, notification)
		self.assertEqual(len(Message.objects.all()), 0)

	def test_send_notifications_activated_user(self):
		# Check that sending a notification to active creates message as expected
		self.patient1.status = UserProfile.ACTIVE
		self.patient1.save()
		now_datetime = datetime.datetime.now()
		notification = ReminderTime.objects.create(to=self.patient1, prescription=self.prescription1,
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY, send_time=now_datetime)

		self.nc.send_notifications(self.patient1, notification)
		self.assertEqual(len(Message.objects.all()), 1)

class WelcomeMessageTest(TestCase):
	def setUp(self):
		self.nc = NotificationCenter()
		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=datetime.date(year=1990, month=8, day=7))
		ReminderTime.objects.create_welcome_notification(to=self.patient1)
	def test_welcome_message(self):
		self.assertEqual(self.patient1.status, PatientProfile.NEW)
		
		# make sure welcome message was created
		now_datetime = datetime.datetime.now()
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
		self.test_datetime = datetime.datetime.now()

		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=datetime.date(year=1990, month=8, day=7))
		self.n_daily = ReminderTime(to=self.patient1, repeat=ReminderTime.DAILY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)
		self.n_weekly = ReminderTime(to=self.patient1, repeat=ReminderTime.WEEKLY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)
		self.n_monthly = ReminderTime(to=self.patient1, repeat=ReminderTime.MONTHLY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)
		self.n_yearly = ReminderTime(to=self.patient1, repeat=ReminderTime.YEARLY,
			reminder_type=ReminderTime.SAFETY_NET, send_time=self.test_datetime)


	def test_update_daily_send_time(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=1)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_daily.update_to_next_send_time()
		self.n_daily = ReminderTime.objects.get(pk=self.n_daily.pk)
		self.assertTrue((self.n_daily.send_time - future_datetime).days == 1)
		freezer.stop()

	def test_update_weekly_send_time(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=7)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_weekly.update_to_next_send_time()
		self.n_weekly = ReminderTime.objects.get(pk=self.n_weekly.pk)
		self.assertTrue((self.n_weekly.send_time - future_datetime).days == 7)
		freezer.stop()

	def test_update_monthly_send_time(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=31)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_monthly.update_to_next_send_time()
		self.n_monthly = ReminderTime.objects.get(pk=self.n_monthly.pk)
		self.assertTrue((self.n_monthly.send_time.month - future_datetime.month) == 1)
		freezer.stop()

	def test_update_yearly_send_time(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=31)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_yearly.update_to_next_send_time()
		self.n_yearly = ReminderTime.objects.get(pk=self.n_yearly.pk)
		self.assertTrue((self.n_yearly.send_time.year - future_datetime.year) == 1)
		freezer.stop()

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
	#TODO(mgaba): Test case where primary contact receives messages
	def setUp(self):
		return

