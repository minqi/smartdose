"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from common.models import Drug
from django.template.loader import render_to_string
from django.test import Client
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotFound
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import ReminderTime, Prescription, Message, SentReminder
from reminders import models as reminder_model
from reminders import tasks as reminder_tasks
from reminders import views as reminder_views
from common.utilities import DatetimeStub, getLastSentMessageContent, getLastNSentMessageContent
from configs.dev import settings
import os, sys
from datetime import datetime, timedelta, time, date
from configs.dev.settings import MESSAGE_CUTOFF
from reminders.notification_center import NotificationCenter

class NotificationCenterTest(TestCase):
	def test_merge_notifications(self):
		nc = NotificationCenter()

		# create 5 notifications within an 3600 s (1 hr), and 5 in the next hour
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  birthday=date(year=1990, month=8, day=7))
		now_time = datetime.now()
		for i in range(5):
			send_time = now_time + timedelta(seconds=i*360)
			ReminderTime.objects.create(to=minqi, reminder_type=ReminderTime.WELCOME, repeat=ReminderTime.DAILY, send_time=send_time)

		reminders = ReminderTime.objects.all()
		merged_reminders = nc.merge_notifications(reminders)

		ground_truth_merged_reminders = []

		reminder_group = []
		for reminder in reminders:
			reminder_group.append(reminder)
		ground_truth_merged_reminders.append(tuple(reminder_group))
		ground_truth_merged_reminders = tuple(ground_truth_merged_reminders)
		self.assertEqual(merged_reminders, ground_truth_merged_reminders)

class SafetyNetTest(TestCase):
	def setUp(self):
		self.bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",  
										   primary_phone_number="2029163381", 
										   birthday=date(year=1960, month=10, day=20),
										   username="2029163381",
										   address_line1="4262 Cesar Chavez", postal_code="94131", 
										   city="San Francisco", state_province="CA", country_iso_code="US")
		self.vitamin = Drug.objects.create(name="vitamin")
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  username="8569067308",
								 				  birthday=date(year=1990, month=4, day=21),
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		self.minqi_prescription = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=self.vitamin,
														 note="To make you strong", safety_net_on=True, filled=True)
		reminder_tasks.datetime = DatetimeStub()
		reminder_model.datetime = DatetimeStub()
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close() 

	def tearDown(self):
		f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file.
		f.close()  

	def test_safety_net_template(self):
		self.minqi.addSafetyNetMember(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", 
						 birthday=date(year=1989, month=10, day=13), 
						 patient_relationship="friend")
		# Minqi has only taken 50 / 100 vitamins from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 50, 100)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('safety_net_nonadherent_message.txt', dictionary)
		correct_message = "Your friend, Minqi Jiang, has had trouble taking the following medication from 10/10 to 10/17:\nvitamin: 50% (50/100)"
		self.assertEqual(message_body, correct_message)
		self.assertTrue(message_body.__len__() < 160) # Less than text message length

		# Try it with a second prescription
		drug2 = Drug.objects.create(name="cocaine")
		minqi_prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=drug2,
														 note="To make you strong", safety_net_on=True, filled=True)
		# Minqi has only taken 50 / 100 vitamins and 1/3 cocaine from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 50, 100), (minqi_prescription2, 1, 3)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('safety_net_nonadherent_message.txt', dictionary)
		correct_message = "Your friend, Minqi Jiang, has had trouble taking the following medication from 10/10 to 10/17:\nvitamin: 50% (50/100)\ncocaine: 33% (1/3)"
		self.assertEqual(message_body, correct_message)
		self.assertTrue(message_body.__len__() < 160) # Less than text message length

		# Try it with three prescriptions
		drug3 = Drug.objects.create(name="vaccine")
		minqi_prescription3 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=drug3,
														 note="To make you strong", safety_net_on=True, filled=True)
		# Minqi has only taken 50 / 100 vitamins, 1/3 cocaine, 1/7 vaccine from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 50, 100), (minqi_prescription2, 1, 3), (minqi_prescription3, 1, 7)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('safety_net_nonadherent_message.txt', dictionary)
		correct_message = "Your friend, Minqi Jiang, has had trouble taking the following medication from 10/10 to 10/17:\nvitamin: 50% (50/100)\ncocaine: 33% (1/3)\nvaccine: 14% (1/7)"
		self.assertEqual(message_body, correct_message)
		self.assertTrue(message_body.__len__() < 160) # Less than text message length

		# Test the alternative, adherent message
		# Minqi has only taken 50 / 100 vitamins, 1/3 cocaine, 1/7 vaccine from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 90, 100), (minqi_prescription2, 3, 3), (minqi_prescription3, 6, 7)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('safety_net_adherent_message.txt', dictionary)
		correct_message = "Your friend, Minqi Jiang, successfully took the following medication from 10/10 to 10/17:\nvitamin: 90% (90/100)\ncocaine: 100% (3/3)\nvaccine: 86% (6/7)"
		self.assertEqual(message_body, correct_message)
		self.assertTrue(message_body.__len__() < 160) # Less than text message length

	def test_contact_safety_net(self):
		# Add a safety net member for Minqi
		# TODO: test scenario where Minqi doesn't have a safety net
		self.minqi.addSafetyNetMember(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", 
						 birthday=date(year=1989, month=10, day=13), 
						 patient_relationship="friend")
		self.minqi_prescription.safety_net_on = True
		self.minqi_prescription.save()
		# Construct a scenario where Minqi is sent three reminders over the course of a week and acks one of them.
		send_datetime = datetime(year=2013, month=4, day=11, hour=9, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		send_time1 = time(hour=9, minute=0)
		datetime1 = datetime.combine(date(year=2013, month=4, day=11), send_time1)

		reminder = ReminderTime.objects.create(
						to=self.minqi, 
						prescription=self.minqi_prescription, 
						repeat=ReminderTime.DAILY, 
						send_time=datetime1, 
						reminder_type=ReminderTime.MEDICATION)
		reminders = ReminderTime.objects.filter(id=reminder.id) #sendReminders needs a queryset, so get one here
		self.minqi.sendReminders(reminders)
		self.minqi.sendReminders(reminders)
		self.minqi.sendReminders(reminders)
		sent_reminders = SentReminder.objects.filter(reminder_time=reminder)
		for sent_reminder in sent_reminders:
			sent_reminder.time_sent = send_datetime
			sent_reminder.save()
		sent_reminders[0].processAck()

		# Now contact safety net
		contact_datetime = datetime(year=2013, month=4, day=18, hour=12, minute=0)
		reminder_tasks.datetime.set_fixed_now(contact_datetime)

		reminder_model.datetime.set_fixed_now(contact_datetime)
		reminder_tasks.contactSafetyNet(send_datetime, contact_datetime, .8, timedelta(hours=4))

		reminder_tasks.sendRemindersForNow()
		self.assertEqual(getLastSentMessageContent(), "2147094720: Your friend, Minqi Jiang, has had trouble taking the following medication from 04/11 to 04/18:|vitamin: 33% (1/3)")


class HandleResponseTest(TestCase):
	def setUp(self):
		self.bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",  
										   primary_phone_number="2029163381", 
										   birthday=date(year=1960, month=10, day=20),
										   username="2029163381",
										   address_line1="4262 Cesar Chavez", postal_code="94131", 
										   city="San Francisco", state_province="CA", country_iso_code="US")
		self.vitamin = Drug.objects.create(name="vitamin")
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  username="8569067308",
								 				  birthday=date(year=1990, month=4, day=21),
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		self.minqi_prescription = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=self.vitamin,
														 note="To make you strong", safety_net_on=True, filled=True)
		reminder_tasks.datetime = DatetimeStub()


	def test_is_ack(self):
		self.assertEqual(reminder_views.isAck(""), False)
		self.assertEqual(reminder_views.isAck("Hello"), False)
		self.assertEqual(reminder_views.isAck("1d"), False)
		self.assertEqual(reminder_views.isAck("1"), True)
		self.assertEqual(reminder_views.isAck("12"), True)
		self.assertEqual(reminder_views.isAck("14201341204124"), True)

	def test_process_ack(self):
		# Returns HttpResponseNotFound() when there's nothing to ack
		self.assertEqual(reminder_views.processAck(self.minqi.primary_phone_number, "1").status_code, 404)

		# Schedule a reminder and put database in state after sent message
		send_time1 = time(hour=9, minute=0)
		datetime1 = datetime.combine(date.today(), send_time1)

		reminder1 = ReminderTime.objects.create(to=self.minqi, prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)
		message = Message.objects.create(patient=self.minqi)
		sent_reminder = SentReminder.objects.create(prescription = reminder1.prescription,
													reminder_time = reminder1,
													message=message)
		# Check that there was a sent reminder
		self.assertEqual(SentReminder.objects.get(id=sent_reminder.id).ack, False)
		self.assertEqual(Message.objects.get(id=message.id).state, Message.UNACKED)
		# If there is an ack with the wrong number, nothing should change.
		self.assertEqual(reminder_views.processAck(self.minqi.primary_phone_number, "2").content, "Whoops--there is no reminder with number '2' that needs a response.")
		self.assertEqual(Message.objects.get(id=message.id).state, Message.UNACKED)
		self.assertEqual(SentReminder.objects.get(id=sent_reminder.id).ack, False)
		# Now, a proper ack with the correct number
		self.assertEqual(reminder_views.processAck(self.minqi.primary_phone_number, "1").content, "Your family will be happy to know that you're taking care of your health :)")
		self.assertEqual(Message.objects.get(id=message.id).state, Message.ACKED)
		self.assertEqual(SentReminder.objects.get(id=sent_reminder.id).ack, True)

		# Test a pharmacy refill reminder
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
														 note="To make you strong", safety_net_on=True)
		reminder2 = ReminderTime.objects.create(to=self.minqi, prescription=prescription2, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.REFILL)
		message = Message.objects.create(patient=self.minqi)
		sent_reminder = SentReminder.objects.create(prescription = prescription2,
													reminder_time = reminder2,
													message=message)
		# Check that there was a sent reminder
		self.assertEqual(SentReminder.objects.get(id=sent_reminder.id).ack, False)
		self.assertEqual(Message.objects.get(id=message.id).state, Message.UNACKED)
		self.assertEqual(prescription2.filled, False)
		self.assertEqual(ReminderTime.objects.filter(id=reminder2.id).count(), 1)
		# If there is an ack with the wrong number, nothing should change.
		self.assertEqual(reminder_views.processAck(self.minqi.primary_phone_number, "2").content, "Whoops--there is no reminder with number '2' that needs a response.")
		self.assertEqual(Message.objects.get(id=message.id).state, Message.UNACKED)
		self.assertEqual(SentReminder.objects.get(id=sent_reminder.id).ack, False)
		self.assertEqual(prescription2.filled, False)
		self.assertEqual(ReminderTime.objects.get(id=reminder2.id).active, True)
		# Now, a proper ack with the correct number should mark prescription as filled and delete the refill reminder
		self.assertEqual(reminder_views.processAck(self.minqi.primary_phone_number, "1").content, "Your family will be happy to know that you're taking care of your health :)")
		self.assertEqual(Message.objects.get(id=message.id).state, Message.ACKED)
		self.assertEqual(SentReminder.objects.get(id=sent_reminder.id).ack, True)
		self.assertEqual(Prescription.objects.get(id=prescription2.id).filled, True)
		self.assertEqual(ReminderTime.objects.get(id=reminder2.id).active, False)


		# What if we get a message from an unknown number?
		self.assertEqual(reminder_views.processAck("2229392919", "9").status_code, 404)

	def test_twilio_request(self):
		datetime1 = datetime(year=2013, month=12, day=26, hour=9, minute=0)

		# Set up a patient named matt who takes a vitamin at 9am
		matt = PatientProfile.objects.create(first_name="Matt", last_name="Gaba",
								 				  primary_phone_number="2147094720", 
								 				  username="2147094720",
								 				  birthday=date(year=1989, month=10, day=13),
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		matt_prescription = Prescription.objects.create(prescriber=self.bob, patient=matt, drug=self.vitamin,
														note="To make you strong", safety_net_on=True, filled=True)
		reminder = ReminderTime.objects.create(to=matt, prescription=matt_prescription, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)
		# Set time to 9am and send messages
		reminder_tasks.datetime.set_fixed_now(datetime(year=2013, month=12, day=26, hour=9, minute=0))
		reminder_tasks.sendRemindersForNow()

		self.assertEqual(Message.objects.get(sentreminder__prescription__id=matt_prescription.id).state, Message.UNACKED)
		message_number = Message.objects.get(sentreminder__prescription__id=matt_prescription.id).message_number
		# Patient sends a bogus message
		c = Client()
		response = c.get('/textmessage_response/', {'From':matt.primary_phone_number, 'Body':'bogus message'})
		self.assertEqual(Message.objects.get(sentreminder__prescription__id=matt_prescription.id).state, Message.UNACKED)
		self.assertEqual(response.content, "We did not understand your message. Reply 'help' for a list of available commands.")
		# Patient sends the correct message
		response = c.get('/textmessage_response/', {'From':matt.primary_phone_number, 'Body':message_number})
		self.assertEqual(Message.objects.get(sentreminder__prescription__id=matt_prescription.id).state, Message.ACKED)
		self.assertEqual(response.content, "Your family will be happy to know that you're taking care of your health :)")


class SendRemindersTest(TestCase):
	def setUp(self):
		# Create some records
		#TODO(mgaba): Create fixtures that have populate DB with this information
		self.bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",  
										   primary_phone_number="2029163381", 
										   username="2029163381",
										   birthday=date(year=1960, month=10, day=20),
										   address_line1="4262 Cesar Chavez", postal_code="94131", 
										   city="San Francisco", state_province="CA", country_iso_code="US")
		self.vitamin = Drug.objects.create(name="vitamin")
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  username="8569067308",
								 				  birthday=date(year=1990, month=4, day=21),
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		self.minqi_prescription = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=self.vitamin,
														 note="To make you strong", safety_net_on=True, filled=True)
		reminder_model.datetime = DatetimeStub()
		reminder_tasks.datetime = DatetimeStub()
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close() 

	def tearDown(self):
			f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file.
			f.close() 

	# Create records for test
	def test_reminders_at_time(self):
		# need to set global datetime

		# schedule daily, weekly, monthly, and yearly reminders
		daily_send_datetime   = datetime.combine(date(year=2014, month=1, day=1),  time(hour=12, minute=0))
		weekly_send_datetime  = datetime.combine(date(year=2014, month=1, day=7),  time(hour=15, minute=0))
		monthly_send_datetime = datetime.combine(date(year=2014, month=1, day=14), time(hour=18, minute=0))
		yearly_send_datetime  = datetime.combine(date(year=2014, month=8, day=7),  time(hour=12, minute=0))

		daily_reminder = ReminderTime.objects.create(
							to=self.minqi,
							repeat=ReminderTime.DAILY,
							send_time=daily_send_datetime,
							reminder_type=ReminderTime.WELCOME
						)
		weekly_reminder = ReminderTime.objects.create(
							to=self.minqi,
							repeat=ReminderTime.WEEKLY,
							send_time=weekly_send_datetime,
							reminder_type=ReminderTime.WELCOME
						)
		monthly_reminder = ReminderTime.objects.create(
							to=self.minqi,
							repeat=ReminderTime.MONTHLY,
							send_time=monthly_send_datetime,
							reminder_type=ReminderTime.WELCOME
						)
		yearly_reminder = ReminderTime.objects.create(
							to=self.minqi,
							repeat=ReminderTime.YEARLY,
							send_time=yearly_send_datetime,
							reminder_type=ReminderTime.WELCOME
						)

		query_datetime = datetime(year=2013, month=12, day=31, hour=12, minute=0)
		reminders = ReminderTime.objects.reminders_at_time(query_datetime)
		self.assertEquals(reminders.count(), 0)

		# increment date to next day to test daily reminders
		query_datetime = datetime(year=2014, month=1, day=1, hour=12, minute=0)
		reminders = ReminderTime.objects.reminders_at_time(query_datetime)
		self.assertEquals(reminders.count(), 1)
		self.assertEquals(daily_reminder, reminders.get(pk=daily_reminder.pk))
		
		# increment date to next week to make sure the weekly reminder is being sent
		query_datetime = datetime(year=2014, month=1, day=7, hour=15, minute=0)
		reminders = ReminderTime.objects.reminders_at_time(query_datetime)
		self.assertEquals(reminders.count(), 2)
		self.assertEquals(daily_reminder, reminders.get(pk=daily_reminder.pk))
		self.assertEquals(weekly_reminder, reminders.get(pk=weekly_reminder.pk))
		
		# increment date to next month to make sure the monthly reminder is being sent
		query_datetime = datetime(year=2014, month=1, day=14, hour=18, minute=0)
		reminders = ReminderTime.objects.reminders_at_time(query_datetime)
		self.assertEquals(reminders.count(), 3)
		self.assertEquals(daily_reminder, reminders.get(pk=daily_reminder.pk))
		self.assertEquals(weekly_reminder, reminders.get(pk=weekly_reminder.pk))
		self.assertEquals(monthly_reminder, reminders.get(pk=monthly_reminder.pk))

		# increment date to next year to make sure the yearly reminder is being sent
		query_datetime = datetime(year=2014, month=8, day=7, hour=12, minute=0)
		reminders = ReminderTime.objects.reminders_at_time(query_datetime)
		self.assertEquals(reminders.count(), 4)
		self.assertEquals(daily_reminder, reminders.get(pk=daily_reminder.pk))
		self.assertEquals(weekly_reminder, reminders.get(pk=weekly_reminder.pk))
		self.assertEquals(monthly_reminder, reminders.get(pk=monthly_reminder.pk))
		self.assertEquals(yearly_reminder, reminders.get(pk=yearly_reminder.pk))

	def test_create_message(self):
		send_time1 = time(hour=12, minute=0)
		datetime1 = datetime.combine(date.today(), send_time1)

		reminder1 = ReminderTime.objects.create(to=self.minqi, prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)

		# Create a message now and test the message number
		sent_time = datetime.now()
		reminder_model.datetime.set_fixed_now(sent_time)
		m1 = Message.objects.create(patient=self.minqi)
		m1.time_sent = sent_time
		m1.save()
		self.assertEquals(m1.message_number, 1)

		# Create a second message three hours later and test the message number
		sent_time = sent_time + timedelta(hours=3)
		reminder_model.datetime.set_fixed_now(sent_time)
		m2 = Message.objects.create(patient=self.minqi)
		m2.time_sent = sent_time
		m2.save()
		self.assertEquals(m2.message_number, 2)

		# Ack the first and second message
		m1.state = Message.ACKED
		m1.save()
		m2.state = Message.ACKED
		m2.save()

		# Create a third message three hours later and test the message number
		sent_time = sent_time + timedelta(hours=3)
		reminder_model.datetime.set_fixed_now(sent_time)
		m3 = Message.objects.create(patient=self.minqi)
		m3.time_sent = sent_time
		m3.save()
		self.assertEquals(m3.message_number, 1)

		# Advance to the next day (18 hours later) and send another message. Test the message number
		sent_time = sent_time + timedelta(hours=18)
		reminder_model.datetime.set_fixed_now(sent_time)
		m4 = Message.objects.create(patient=self.minqi)
		m4.time_sent = sent_time
		m4.save()
		self.assertEquals(m4.message_number, 2)
		self.assertEquals(m1.state, Message.ACKED)
		self.assertEquals(m4.state, Message.UNACKED)

		# m4 doesn't get acked. What happens when we advance to the next day and send a message?
		sent_time = sent_time + timedelta(hours=24)
		reminder_model.datetime.set_fixed_now(sent_time)
 		m5 = Message.objects.create(patient=self.minqi)
 		m5.time_sent = sent_time
 		m5.save()
		self.assertEquals(m5.state, Message.UNACKED)
		self.assertEquals(m5.message_number, 1)
		self.assertEquals(Message.objects.get(id=m4.id).state, Message.EXPIRED)

		reminder_model.datetime.reset_now()

	def test_medicationreminder_template(self):
		send_time1 = time(hour=9, minute=0)
		datetime1 = datetime.combine(date.today(), send_time1)

		# Test message with one reminder
		reminder1 = ReminderTime.objects.create(to=self.minqi, prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)
		reminder_list = ReminderTime.objects.filter(prescription=self.minqi_prescription)
		m1 = Message.objects.create(patient=self.minqi)
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('medication_reminder.txt', dictionary)
		self.assertEquals(message_body, "Time to take your vitamin. Reply '1' when you finish.")

		# Test message with two reminders
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
														 note="To make you strong", safety_net_on=True, filled=True)
		reminder2 = ReminderTime.objects.create(to=self.minqi, prescription=prescription2, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2))
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('medication_reminder.txt', dictionary)
		self.assertEquals(message_body, "Time to take your vitamin and meditation. Reply '1' when you finish.")

		# Test message with three reminders
		lipitor = Drug.objects.create(name="lipitor")
		prescription3 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=lipitor,
														 note="To make you strong", safety_net_on=True, filled=True)
		reminder3 = ReminderTime.objects.create(to=self.minqi, prescription=prescription3, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2) | Q(prescription=prescription3))
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('medication_reminder.txt', dictionary)
		self.assertEquals(message_body, "Time to take your vitamin, meditation and lipitor. Reply '1' when you finish.")

	def test_refillreminder_template(self):
		send_time1 = time(hour=9, minute=0)
		datetime1 = datetime.combine(date.today(), send_time1)

		# Test message with one reminder
		reminder1 = ReminderTime.objects.create(to=self.minqi, prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.REFILL)
		reminder_list = ReminderTime.objects.filter(prescription=self.minqi_prescription)
		m1 = Message.objects.create(patient=self.minqi)
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('refill_reminder.txt', dictionary)
		self.assertEquals(message_body, "It's important you fill your vitamin prescription as soon as possible. Reply '1' when you've received your medicine.")
		self.assertTrue(message_body.__len__()<=160)


		# Test message with two reminders
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
														 note="To make you strong", safety_net_on=True)
		reminder2 = ReminderTime.objects.create(to=self.minqi, prescription=prescription2, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.REFILL)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2))
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('refill_reminder.txt', dictionary)
		self.assertEquals(message_body, "It's important you fill your vitamin and meditation prescription as soon as possible. Reply '1' when you've received your medicine.")
		self.assertTrue(message_body.__len__()<=160)

		# Test message with three reminders
		lipitor = Drug.objects.create(name="lipitor")
		prescription3 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=lipitor,
														 note="To make you strong", safety_net_on=True)
		reminder3 = ReminderTime.objects.create(to=self.minqi, prescription=prescription3, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.REFILL)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2) | Q(prescription=prescription3))
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('refill_reminder.txt', dictionary)
		self.assertEquals(message_body, "It's important you fill your vitamin, meditation and lipitor prescription as soon as possible. Reply '1' when you've received your medicine.")
		self.assertTrue(message_body.__len__()<=160)

	def test_sendReminders_medication(self):
		send_time1 = time(hour=9, minute=0)
		datetime1 = datetime.combine(date.today(), send_time1)

		# Define a reminder
		reminder1 = ReminderTime.objects.create(to=self.minqi, prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)
		reminder_list = ReminderTime.objects.filter(prescription=self.minqi_prescription)
		# Entry should not exist in database before sending message
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder1.prescription)
		self.assertEqual(message.count(), 0)
		# Send the message
		self.minqi.sendReminders(reminder_list)
		# Did the message get sent correctly?
		self.assertEqual(len(Message.objects.filter(patient=self.minqi)), 1)		
		self.assertEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "Time to take your vitamin. Reply '1' when you finish.")
		# Did database get correctly updated?
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder1.prescription)
		self.assertEqual(message.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=self.minqi_prescription, message=message[0])
		self.assertEqual(sentreminders.count(), 1)

		# Now send a message with two reminders
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
														 note="To make you strong", safety_net_on=True, filled=True)
		reminder2 = ReminderTime.objects.create(to=self.minqi, prescription=prescription2, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.MEDICATION)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2))
		# Entry for message with second prescription should not exist in database before sending message
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder2.prescription)
		self.assertEqual(message.count(), 0)

		reminder1.send_time = datetime1
		reminder1.save()
		# Send the message
		self.minqi.sendReminders(reminder_list)
		# Did the message get sent correctly?
		self.assertEqual(len(Message.objects.filter(patient=self.minqi)), 2)
		self.assertEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "Time to take your meditation and vitamin. Reply '2' when you finish.")
		# Did database get correctly updated?
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder2.prescription)
		self.assertEqual(message.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=self.minqi_prescription, message=message[0])
		self.assertEqual(sentreminders.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=prescription2, message=message[0])
		self.assertEqual(sentreminders.count(), 1)


	def test_sendReminders_refill(self):
		send_time1 = time(hour=9, minute=0)
		datetime1 = datetime.combine(date.today(), send_time1)

		# Define a reminder
		reminder1 = ReminderTime.objects.create(to=self.minqi, prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.REFILL)
		reminder_list = ReminderTime.objects.filter(prescription=self.minqi_prescription)
		# Entry should not exist in database before sending message
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder1.prescription)
		self.assertEqual(message.count(), 0)
		# Send the message
		self.minqi.sendReminders(reminder_list)
		# Did the message get sent correctly?
		self.assertEqual(len(Message.objects.filter(patient=self.minqi)), 1)		
		self.assertNotEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "Time to take your vitamin. Reply '1' when you finish.")
		self.assertEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "It's important you fill your vitamin prescription as soon as possible. Reply '1' when you've received your medicine.")

		# Did database get correctly updated?
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder1.prescription)
		self.assertEqual(message.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=self.minqi_prescription, message=message[0])
		self.assertEqual(sentreminders.count(), 1)

		# Now send a message with two reminders
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
														 note="To make you strong", safety_net_on=True, filled=False)
		reminder2 = ReminderTime.objects.create(to=self.minqi, prescription=prescription2, repeat=ReminderTime.DAILY, send_time=datetime1, reminder_type=ReminderTime.REFILL)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2))
		# Entry for message with second prescription should not exist in database before sending message
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder2.prescription)
		self.assertEqual(message.count(), 0)

		reminder1.send_time = datetime1
		reminder1.save()
		# Send the message
		self.minqi.sendReminders(reminder_list)
		# Did the message get sent correctly?
		self.assertEqual(len(Message.objects.filter(patient=self.minqi)), 2)
		self.assertNotEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "Time to take your meditation and vitamin. Reply '2' when you finish.")
		self.assertNotEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "It's important you fill your vitamin and meditation prescription as soon as possible. Reply '2' when you've received your medicine.")
		# Did database get correctly updated?
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder2.prescription)
		self.assertEqual(message.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=self.minqi_prescription, message=message[0])
		self.assertEqual(sentreminders.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=prescription2, message=message[0])
		self.assertEqual(sentreminders.count(), 1)


	def test_sendRemindersForNow(self):
		# A few more pills, prescriptions
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
													note="To make you strong", safety_net_on=True, filled=True)

		# make sure there's nothing in our sent message logs
		self.assertEqual(getLastSentMessageContent(), "")

		# try sending messages for when there are no scheduled reminders (12am)
		send_datetime = datetime(year=2013, month=4, day=11, hour=12, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertEqual(getLastSentMessageContent(), "")

		# Schedule some reminders at 9am for Minqi
		# send_time1 = time(hour=9, minute=0)
		datetime1 = datetime(year=2013, month=4, day=11, hour=9, minute=0)
		reminder1 = ReminderTime.objects.create(
						to=self.minqi, 
						prescription=self.minqi_prescription, 
						repeat=ReminderTime.DAILY, 
						send_time=datetime1, 
						reminder_type=ReminderTime.MEDICATION)
		datetime1 = datetime(year=2013, month=4, day=11, hour=9, minute=0)
		reminder2 = ReminderTime.objects.create(
						to=self.minqi, 
						prescription=prescription2, 
						repeat=ReminderTime.DAILY, 
						send_time=datetime1, 
						reminder_type=ReminderTime.MEDICATION)
		
		# Send some reminders for now (12am)
		send_datetime = datetime(year=2013, month=4, day=11, hour=0, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertEqual(getLastSentMessageContent(), "")

		# Now change the time to 9am when reminders should be sent
		send_datetime = datetime(year=2013, month=4, day=11, hour=9, minute=1)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "Time to take your meditation and vitamin. Reply '1' when you finish.")

		# Add another patient and schedule reminders at 10am for that patient
		matt = PatientProfile.objects.create(first_name="Matt", last_name="Gaba",
								 				  primary_phone_number="2147094720", 
								 				  username="2147094720",
								 				  birthday=date(year=1989, month=10, day=13),
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		matt_prescription = Prescription.objects.create(
								prescriber=self.bob, 
								patient=matt, 
								drug=self.vitamin,
								note="To make you strong", 
								safety_net_on=True, 
								filled=True)

		datetime2 = datetime(year=2013, month=4, day=11, hour=10, minute=0)
		matt_reminder1 = ReminderTime.objects.create(
								to=matt, 
								prescription=matt_prescription, 
								repeat=ReminderTime.DAILY, 
								send_time=datetime2, 
								reminder_type=ReminderTime.MEDICATION)

		# Change time to 10am and make sure message is sent
		send_datetime = datetime(year=2013, month=4, day=11, hour=10, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()

		self.assertEqual(getLastSentMessageContent(), matt.primary_phone_number + ": " + "Time to take your vitamin. Reply '1' when you finish.")

		# Schedule reminders for Matt and Minqi at 12am. 
		datetime3 = datetime(year=2013, month=4, day=11, hour=12, minute=0)
		matt_reminder2 = ReminderTime.objects.create(to=matt, prescription=matt_prescription, repeat=ReminderTime.DAILY, send_time=datetime3, reminder_type=ReminderTime.MEDICATION)
		minqi_reminder3 = ReminderTime.objects.create(to=self.minqi, prescription=prescription2, repeat=ReminderTime.DAILY, send_time=datetime3, reminder_type=ReminderTime.MEDICATION)
		# # Move time to 11 to make sure no messages are sent.
		send_datetime = datetime(year=2013, month=4, day=11, hour=11, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()

		self.assertNotIn(matt.primary_phone_number + ": " + "Time to take your vitamin. Reply '2' when you finish.", getLastNSentMessageContent(2))
		self.assertNotIn(self.minqi.primary_phone_number + ": " + "Time to take your meditation. Reply '2' when you finish.", getLastNSentMessageContent(2))
		# # Move time to 12 and make sure messages get sent.
		send_datetime = datetime(year=2013, month=4, day=11, hour=12, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertIn(matt.primary_phone_number + ": " + "Time to take your vitamin. Reply '2' when you finish.", getLastNSentMessageContent(2))
		self.assertIn(self.minqi.primary_phone_number + ": " + "Time to take your meditation. Reply '2' when you finish.", getLastNSentMessageContent(2))

		reminder_model.datetime.reset_now()


