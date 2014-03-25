import datetime, codecs, os, sys

from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotFound
from django.test import TestCase
from django.test import Client
from django.template.loader import render_to_string

from configs.dev import settings
from configs.dev.settings import MESSAGE_CUTOFF
from common.models import UserProfile, Drug
from common.utilities import SMSLogger
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import Notification, Prescription, Message, Feedback
from reminders import models as reminder_model
from reminders import tasks as reminder_tasks
from reminders import views as reminder_views
from reminders.notification_center import NotificationCenter
from reminders.response_center import ResponseCenter

from freezegun import freeze_time


class NotificationCenterTest(TestCase):
	def setUp(self):
		self.nc = NotificationCenter()
		self.doctor = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",
			primary_phone_number="2029163381", birthday=datetime.date(1960, 1, 1))
		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                              primary_phone_number="8569067308",
		                                              birthday=datetime.date(year=1990, month=8, day=7),
		                                              enroller=self.doctor)
		self.patient2 = PatientProfile.objects.create(first_name="Matt", last_name="Gaba",
		                                              primary_phone_number="2147094720",
		                                              birthday=datetime.date(year=1989, month=10, day=13),
		                                              enroller=self.patient1)
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
			Notification.objects.create(to=self.patient1, type=Notification.MEDICATION, prescription=self.prescription1,
			                            repeat=Notification.DAILY, send_datetime=send_datetime)
		self.med_notifications = Notification.objects.filter(
			to=self.patient1, type=Notification.MEDICATION).order_by('send_datetime')

		(self.refill_reminder, self.med_reminder) = Notification.objects.create_prescription_notifications(
			to=self.patient2, repeat=Notification.DAILY, prescription=self.prescription2)

		self.safetynet_notification = Notification.objects.create(to=self.patient1, type=Notification.SAFETY_NET,
		                                                               content="Your mother was adherent",
																	   patient_of_safety_net=self.patient2,
																	   adherence_rate=80, repeat=Notification.NO_REPEAT)

	def test_merge_notifications(self):
		merged_notifications = self.nc.merge_notifications(self.med_notifications)
		ground_truth_merged_notifications = []
		reminder_group = []
		for reminder in self.med_notifications:
			reminder_group.append(reminder)
		ground_truth_merged_notifications.append(tuple(reminder_group))
		ground_truth_merged_notifications = tuple(ground_truth_merged_notifications)
		self.assertEqual(merged_notifications, ground_truth_merged_notifications)

	def test_send_message(self):
		self.patient1.status = UserProfile.ACTIVE
		sent_time = datetime.datetime.now()
		self.nc.send_text_message(to=self.patient1, notifications=self.med_notifications,
			template='messages/medication_message.txt', context={'reminder_list':list(self.med_notifications)})

		# see if the right messages are created
		self.assertEqual(len(Message.objects.filter(to=self.patient1)), 1)

		# # see if the right book-keeping is performed
		feedback = Feedback.objects.all()
		self.assertEqual(len(feedback), len(self.med_notifications))
		for n in feedback:
			self.assertTrue(n.notification in self.med_notifications)

		Notification.objects.update()
		self.assertTrue((self.med_notifications[0].send_datetime.date() - sent_time.date()).days == 1)

	def test_send_welcome_notifications(self):
		# check that the patient's status is NEW
		self.assertTrue(self.patient1.status == UserProfile.NEW)
		# see if a reminder is sent (shouldn't be)
		self.nc.send_notifications(to=self.patient1, notifications=self.med_notifications)
		self.assertEqual(len(Message.objects.filter(to=self.patient1)), 0)

		# see if both welcome messages are sent
		now_datetime = datetime.datetime.now()
		welcome_notification = Notification.objects.create(to=self.patient1, type=Notification.WELCOME,
		                                                   repeat=Notification.NO_REPEAT, send_datetime=now_datetime)
		self.nc.send_notifications(to=self.patient1, notifications=welcome_notification)

		# see if message is sent
		self.assertEqual(len(Message.objects.filter(to=self.patient1)), 2)

		# see if the patient's status is changed from NEW to ACTIVE
		self.assertTrue(self.patient1.status == UserProfile.ACTIVE)

		# check that notification is deactivated
		welcome_notification = Notification.objects.filter(pk=welcome_notification.pk)[0]
		self.assertTrue(welcome_notification.active == False)

	def test_send_self_enrolled_welcome_notification(self):
		now_datetime = datetime.datetime.now()
		self.patient1.enroller = None
		self.patient1.save()
		welcome_notification = Notification.objects.create(to=self.patient1, type=Notification.WELCOME,
		                                                   repeat=Notification.NO_REPEAT, send_datetime=now_datetime)
		self.nc.send_notifications(to=self.patient1, notifications=welcome_notification)

		messages = Message.objects.filter(to=self.patient1)
		self.assertEqual(messages.count(), 2)
		expected_message_1 = "Hi, Minqi! You signed up for Smartdose to improve your medication experience. You can reply 'q' at any time to quit."
		self.assertEqual(messages[1].content, expected_message_1)
		expected_message_2 = "Smartdose sends you simple medicine reminders, making it easy to take the right dose at the right time.\n\n"+\
							 "For more info, you can visit www.smartdo.se"
		self.assertEqual(messages[0].content, expected_message_2)

	def test_send_safety_net_enrolled_welcome_notification(self):
		now_datetime = datetime.datetime.now()
		self.patient1.enroller = self.patient2
		self.patient1.save()
		welcome_notification = Notification.objects.create(to=self.patient1, type=Notification.WELCOME,
		                                                   repeat=Notification.NO_REPEAT, send_datetime=now_datetime)
		self.nc.send_notifications(to=self.patient1, notifications=welcome_notification)

		messages = Message.objects.filter(to=self.patient1)
		self.assertEqual(messages.count(), 2)
		expected_message_1 = "Hi, Minqi! Matt Gaba is giving you Smartdose to improve your medication experience. You can reply 'q' at any time to quit."
		self.assertEqual(messages[1].content, expected_message_1)
		expected_message_2 = "Smartdose sends you simple medicine reminders, making it easy to take the right dose at the right time.\n\n"+ \
		                     "For more info, you can visit www.smartdo.se"
		self.assertEqual(messages[0].content, expected_message_2)

	def test_send_doctor_net_enrolled_welcome_notification(self):
		now_datetime = datetime.datetime.now()
		welcome_notification = Notification.objects.create(to=self.patient1, type=Notification.WELCOME,
		                                                   repeat=Notification.NO_REPEAT, send_datetime=now_datetime)
		self.nc.send_notifications(to=self.patient1, notifications=welcome_notification)

		messages = Message.objects.filter(to=self.patient1)
		self.assertEqual(messages.count(), 2)
		expected_message_1 = "Hi, Minqi! Dr. Watcher is giving you Smartdose to improve your medication experience. You can reply 'q' at any time to quit."
		self.assertEqual(messages[1].content, expected_message_1)
		expected_message_2 = "Smartdose sends you simple medicine reminders, making it easy to take the right dose at the right time.\n\n"+ \
		                     "For more info, you can visit www.smartdo.se"
		self.assertEqual(messages[0].content, expected_message_2)

	def test_send_refill_notifications(self):
		# see if you can send refill notification
		self.assertTrue(self.patient2.status == UserProfile.NEW)
		sent_time = datetime.datetime.now()
		self.nc.send_notifications(to=self.patient2, notifications=self.refill_reminder)
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 0)
		
		# see if refill is sent
		self.patient2.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient2, notifications=self.refill_reminder)
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 1)

		# see if message number is set
		self.assertEqual(Message.objects.filter(to=self.patient2)[0].nth_message_of_day_of_type, 0)

		# check that send_datetime is properly incremented
		self.refill_reminder = Notification.objects.get(pk=self.refill_reminder.pk)
		self.assertTrue((self.refill_reminder.send_datetime.date() - sent_time.date()).days == 1)

	def test_send_medication_notifications(self):
		# see if you can send medication notification
		self.assertTrue(self.patient1.status == UserProfile.NEW)
		sent_time = datetime.datetime.now()
		self.nc.send_notifications(to=self.patient1, notifications=self.med_reminder)
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 0)
		
		# medication notification shouldn't be sent if prescription isn't filled
		self.patient2.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient2, notifications=self.med_reminder)
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 0)

		# medication notification should be sent if prescription is filled
		self.prescription2.filled = True
		self.prescription2.save()
		self.nc.send_notifications(to=self.patient2, notifications=self.med_reminder)
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 1)

		# see if message number is set
		self.assertEqual(Message.objects.filter(to=self.patient2)[0].nth_message_of_day_of_type, 0)
		# # check that send_datetime is properly incremented
		self.med_reminder = Notification.objects.get(pk=self.med_reminder.pk)
		self.assertTrue((self.med_reminder.send_datetime.date() - sent_time.date()).days == 1)

	def test_send_safetynet_notifications(self):
		# # see if safetynet notification is sent
		self.patient1.status = UserProfile.ACTIVE
		self.nc.send_notifications(to=self.patient1, notifications=self.safetynet_notification)
		self.assertEqual(len(Message.objects.filter(to=self.patient1)), 1)

		# check that safety-net notification is deactivated
		self.safetynet_notification = Notification.objects.get(pk=self.safetynet_notification.pk)
		self.assertTrue(self.safetynet_notification.active == False)

	def test_send_repeat_message_notifications(self):
		# Prepare initial med reminder to send
		self.patient2.status = UserProfile.ACTIVE
		self.prescription2.filled = True
		self.prescription2.save()
		# Send initial med reminder
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 0)
		self.nc.send_notifications(to=self.patient2, notifications=self.med_reminder)
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 1)
		# Get the message object that was created by sending
		message = Message.objects.filter(to=self.patient2)[0]
		repeat_notification = Notification.objects.create(to=self.patient2, type=Notification.REPEAT_MESSAGE,
		                                                  repeat=Notification.NO_REPEAT,
		                                                  message = message,
		                                                  send_datetime=datetime.datetime.now())
		self.nc.send_notifications(to=self.patient2, notifications=repeat_notification)
		messages = Message.objects.filter(to=self.patient2)
		original_message = messages[0]
		new_message = messages[1]
		self.assertEqual(len(Message.objects.filter(to=self.patient2)), 2)
		self.assertEqual(original_message.type, new_message.type)
		for feedback in new_message.feedbacks.all():
			self.assertIn(feedback, original_message.feedbacks.all())
		for notification in new_message.notifications.all():
			self.assertIn(notification, original_message.notifications.all())

	def test_send_notifications_deactivated_user(self):
		# Should not send messages to deactivated account
		self.patient1.status = UserProfile.QUIT
		self.patient1.save()
		now_datetime = datetime.datetime.now()
		notification = Notification.objects.create(to=self.patient1, type=Notification.WELCOME, send_datetime=now_datetime,
		                                           repeat=Notification.NO_REPEAT)

		self.nc.send_notifications(self.patient1, notification)
		self.assertEqual(len(Message.objects.all()), 0)

	def test_send_notifications_activated_user(self):
		# Check that sending a notification to active creates message as expected
		self.patient1.status = UserProfile.ACTIVE
		self.patient1.save()
		now_datetime = datetime.datetime.now()
		notification = Notification.objects.create(to=self.patient1, type=Notification.MEDICATION, prescription=self.prescription1,
			repeat=Notification.DAILY, send_datetime=now_datetime)

		self.nc.send_notifications(self.patient1, notification)
		self.assertEqual(len(Message.objects.all()), 1)

class WelcomeMessageTest(TestCase):
	def setUp(self):
		self.nc = NotificationCenter()
		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=datetime.date(year=1990, month=8, day=7))
		Notification.objects.create(to=self.patient1, type=Notification.WELCOME, repeat=Notification.NO_REPEAT,
		                            send_datetime=datetime.datetime.now())
	def test_welcome_message(self):
		self.assertEqual(self.patient1.status, PatientProfile.NEW)
		
		# make sure welcome message was created
		now_datetime = datetime.datetime.now()
		notifications = Notification.objects.notifications_at_time(now_datetime)
		self.assertEqual(len(notifications), 1) 
		self.assertEqual(notifications[0].type, Notification.WELCOME)
		self.assertEqual(notifications[0].to, self.patient1)

		# after sending welcome, make sure patient is active and 
		# welcome notification is not
		self.nc.send_notifications(self.patient1, notifications)
		welcome_notification = Notification.objects.filter(pk=notifications[0].pk)[0]
		self.assertEqual(welcome_notification.active,  False)
		self.assertEqual(self.patient1.status, PatientProfile.ACTIVE)

class UpdateSendDateTimeTest(TestCase):
	def setUp(self):
		self.test_datetime = datetime.datetime.now()

		self.patient1 = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=datetime.date(year=1990, month=8, day=7))
		self.n_daily = Notification(to=self.patient1, type=Notification.STATIC_ONE_OFF, repeat=Notification.DAILY,
			send_datetime=self.test_datetime, content="Test content")
		self.n_weekly = Notification(to=self.patient1, type=Notification.STATIC_ONE_OFF,
			 repeat=Notification.WEEKLY, send_datetime=self.test_datetime, content="Test content")
		self.n_monthly = Notification(to=self.patient1, type=Notification.STATIC_ONE_OFF, repeat=Notification.MONTHLY,
			 send_datetime=self.test_datetime, content="Test content")
		self.n_yearly = Notification(to=self.patient1, type=Notification.STATIC_ONE_OFF, repeat=Notification.YEARLY,
			 send_datetime=self.test_datetime, content="Test content")


	def test_update_daily_send_datetime(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=1)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_daily.update_to_next_send_time()
		self.n_daily = Notification.objects.get(pk=self.n_daily.pk)
		self.assertTrue((self.n_daily.send_datetime - future_datetime).days == 1)
		freezer.stop()

	def test_update_weekly_send_datetime(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=7)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_weekly.update_to_next_send_time()
		self.n_weekly = Notification.objects.get(pk=self.n_weekly.pk)
		self.assertTrue((self.n_weekly.send_datetime - future_datetime).days == 7)
		freezer.stop()

	def test_update_monthly_send_datetime(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=31)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_monthly.update_to_next_send_time()
		self.n_monthly = Notification.objects.get(pk=self.n_monthly.pk)
		self.assertTrue((self.n_monthly.send_datetime.month - future_datetime.month) == 1)
		freezer.stop()

	def test_update_yearly_send_datetime(self):
		future_datetime = self.test_datetime + datetime.timedelta(days=31)
		freezer = freeze_time(future_datetime)
		freezer.start()
		self.n_yearly.update_to_next_send_time()
		self.n_yearly = Notification.objects.get(pk=self.n_yearly.pk)
		self.assertTrue((self.n_yearly.send_datetime.year - future_datetime.year) == 1)
		freezer.stop()

class TestSafetyNetTemplate(TestCase):

	def test_adherent_template_male_response(self):
		dictionary = {
			'adherence_percentage':100,
		    'threshold':80,
		    'patient_first':'Matthew',
		    'patient_gender':PatientProfile.MALE,
		    'patient_relationship':'son'
		}
		correct_message = "Great news - your son, Matthew, has been taking care this week. He's reported taking 100% of his meds."
		message_body = render_to_string('messages/safety_net_message_adherent.txt',dictionary)
		self.assertEqual(message_body, correct_message)

	def test_adherent_template_female_response(self):
		dictionary = {
		'adherence_percentage':100,
		'threshold':80,
		'patient_first':'Marge',
		'patient_gender':PatientProfile.FEMALE,
		'patient_relationship':'mother'
		}
		correct_message = "Great news - your mother, Marge, has been taking care this week. She's reported taking 100% of her meds."
		message_body = render_to_string('messages/safety_net_message_adherent.txt',dictionary)
		self.assertEqual(message_body, correct_message)

	def test_adherent_template_gender_neutral_response(self):
		dictionary = {
		'adherence_percentage':100,
		'threshold':80,
		'patient_first':'Pat',
		'patient_gender':PatientProfile.UNKNOWN,
		'patient_relationship':'sibling'
		}
		correct_message = "Great news - your sibling, Pat, has been taking care this week. They've reported taking 100% of their meds."
		message_body = render_to_string('messages/safety_net_message_adherent.txt',dictionary)
		self.assertEqual(message_body, correct_message)

	def test_borderline_adherent_template_female_response(self):
		dictionary = {
		'adherence_percentage':80,
		'threshold':80,
		'patient_first':'Marge',
		'patient_gender':PatientProfile.FEMALE,
		'patient_relationship':'mother'
		}
		correct_message = "Great news - your mother, Marge, has been taking care this week. She's reported taking 80% of her meds."
		message_body = render_to_string('messages/safety_net_message_adherent.txt',dictionary)
		self.assertEqual(message_body, correct_message)

	def test_nonadherent_template_male_response(self):
		dictionary = {
		'adherence_percentage':30,
		'threshold':80,
		'patient_first':'John',
		'patient_gender':PatientProfile.MALE,
		'patient_relationship':'grandfather'
		}
		correct_message = "Your grandfather, John, has had trouble with his medicine this week. He's reported taking 30% of his meds. Maybe you should give him a call?"
		message_body = render_to_string('messages/safety_net_message_nonadherent.txt',dictionary)
		self.assertEqual(message_body, correct_message)

	def test_nonadherent_template_female_response(self):
		dictionary = {
		'adherence_percentage':30,
		'threshold':80,
		'patient_first':'Jane',
		'patient_gender':PatientProfile.FEMALE,
		'patient_relationship':'grandmother'
		}
		correct_message = "Your grandmother, Jane, has had trouble with her medicine this week. She's reported taking 30% of her meds. Maybe you should give her a call?"
		message_body = render_to_string('messages/safety_net_message_nonadherent.txt',dictionary)
		self.assertEqual(message_body, correct_message)

	def test_nonadherent_template_gender_neutral_response(self):
		dictionary = {
		'adherence_percentage':30,
		'threshold':80,
		'patient_first':'Jan',
		'patient_gender':PatientProfile.UNKNOWN,
		'patient_relationship':'grandparent'
		}
		correct_message = "Your grandparent, Jan, has had trouble with their medicine this week. They've reported taking 30% of their meds. Maybe you should give them a call?"
		message_body = render_to_string('messages/safety_net_message_nonadherent.txt',dictionary)
		self.assertEqual(message_body, correct_message)
