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
import os
from datetime import datetime, timedelta, time, date
from configs.dev.settings import MESSAGE_CUTOFF

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
														 note="To make you strong", safety_net_on=True)
		reminder_tasks.datetime = DatetimeStub()
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close() 

	#def tearDown(self):
		#f = open(settings.MESSAGE_LOG_FILENAME, 'w') # Open file with 'w' permission to clear log file.
		#f.close()  

	def test_safety_net_template(self):
		self.minqi.addSafetyNetMember(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", 
						 birthday=date(year=1989, month=10, day=13), 
						 patient_relationship="friend")
		# Minqi has only taken 50 / 100 vitamins from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 50, 100)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('templates/safety_net_nonadherent_message.txt', dictionary)
		correct_message = "Your friend, Minqi Jiang, has had trouble taking the following medication from 10/10 to 10/17:\nvitamin: 50% (50/100)"
		self.assertEqual(message_body, correct_message)
		self.assertTrue(message_body.__len__() < 160) # Less than text message length

		# Try it with a second prescription
		drug2 = Drug.objects.create(name="cocaine")
		minqi_prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=drug2,
														 note="To make you strong", safety_net_on=True)
		# Minqi has only taken 50 / 100 vitamins and 1/3 cocaine from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 50, 100), (minqi_prescription2, 1, 3)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('templates/safety_net_nonadherent_message.txt', dictionary)
		correct_message = "Your friend, Minqi Jiang, has had trouble taking the following medication from 10/10 to 10/17:\nvitamin: 50% (50/100)\ncocaine: 33% (1/3)"
		self.assertEqual(message_body, correct_message)
		self.assertTrue(message_body.__len__() < 160) # Less than text message length

		# Try it with three prescriptions
		drug3 = Drug.objects.create(name="vaccine")
		minqi_prescription3 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=drug3,
														 note="To make you strong", safety_net_on=True)
		# Minqi has only taken 50 / 100 vitamins, 1/3 cocaine, 1/7 vaccine from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 50, 100), (minqi_prescription2, 1, 3), (minqi_prescription3, 1, 7)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('templates/safety_net_nonadherent_message.txt', dictionary)
		correct_message = "Your friend, Minqi Jiang, has had trouble taking the following medication from 10/10 to 10/17:\nvitamin: 50% (50/100)\ncocaine: 33% (1/3)\nvaccine: 14% (1/7)"
		self.assertEqual(message_body, correct_message)
		self.assertTrue(message_body.__len__() < 160) # Less than text message length

		# Test the alternative, adherent message
		# Minqi has only taken 50 / 100 vitamins, 1/3 cocaine, 1/7 vaccine from the time period 10/10/2013 to 10/17/2013
		prescriptions = [(self.minqi_prescription, 90, 100), (minqi_prescription2, 3, 3), (minqi_prescription3, 6, 7)]
		window_start = datetime(year=2013, month=10, day=10)
		window_finish = datetime(year=2013, month=10, day=17)

		dictionary = {'prescriptions':prescriptions, 'patient_relationship':'friend', 'patient_first':self.minqi.first_name, 'patient_last':self.minqi.last_name, 'window_start':window_start, 'window_finish':window_finish}
		message_body = render_to_string('templates/safety_net_adherent_message.txt', dictionary)
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
		send_time = time(hour=9, minute=0)
		reminder = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time)
		reminders = ReminderTime.objects.filter(id=reminder.id) #sendOneReminder needs a queryset, so get one here
		reminder_tasks.sendOneReminder(self.minqi, reminders)
		reminder_tasks.sendOneReminder(self.minqi, reminders)
		reminder_tasks.sendOneReminder(self.minqi, reminders)
		sent_reminders = SentReminder.objects.filter(reminder_time=reminder)
		for sent_reminder in sent_reminders:
			sent_reminder.time_sent = send_datetime
			sent_reminder.save()
		sent_reminders[0].processAck()

		# Now contact safety net
		contact_datetime = datetime(year=2013, month=4, day=18, hour=12, minute=0)
		reminder_tasks.datetime.set_fixed_now(contact_datetime)
		reminder_tasks.contactSafetyNet(send_datetime, contact_datetime, .8, timedelta(hours=4))

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
														 note="To make you strong", safety_net_on=True)
		reminder_tasks.datetime = DatetimeStub()


	def test_is_done(self):
		self.assertEqual(reminder_views.isDone(""), False)
		self.assertEqual(reminder_views.isDone("Hello"), False)
		self.assertEqual(reminder_views.isDone("1d"), False)
		self.assertEqual(reminder_views.isDone("1"), True)
		self.assertEqual(reminder_views.isDone("12"), True)
		self.assertEqual(reminder_views.isDone("14201341204124"), True)

	def test_process_done(self):
		# Returns HttpResponseNotFound() when there's nothing to ack
		self.assertEqual(reminder_views.processDone(self.minqi.primary_phone_number, "1").status_code, 404)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_sent, 0)
		# Schedule a reminder and put database in state after sent message
		send_time = time(hour=9, minute=0)
		reminder1 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time)
		message = Message.objects.create(patient=self.minqi)
		sent_reminder = SentReminder.objects.create(prescription = reminder1.prescription,
													reminder_time = reminder1,
													message=message)
		# Check that prescription knows there was a sent reminder
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_sent, 1)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_acked, 0)
		# If there is an ack with the wrong number, nothing should change.
		self.assertEqual(reminder_views.processDone(self.minqi.primary_phone_number, "2").content, "Whoops--there is no reminder with number '2' that needs a response.")
		self.assertEqual(Message.objects.get(id=message.id).state, Message.UNACKED)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_acked, 0)
		# Now, a proper ack with the correct number
		self.assertEqual(reminder_views.processDone(self.minqi.primary_phone_number, "1").content, "Be happy that you are taking care of your health!")
		self.assertEqual(Message.objects.get(id=message.id).state, Message.ACKED)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_acked, 1)

		# What if we get a message from an unknown number?
		self.assertEqual(reminder_views.processDone("2229392919", "9").status_code, 404)

	def test_twilio_request(self):
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
														note="To make you strong", safety_net_on=True)
		reminder = ReminderTime.objects.create(prescription=matt_prescription, repeat=ReminderTime.DAILY, send_time=time(hour=9, minute=0))
		# Set time to 9am and send messages
		reminder_tasks.datetime.set_fixed_now(datetime(year=2013, month=12, day=26, hour=9, minute=0))
		reminder_tasks.sendRemindersForNow()
		self.assertEqual(Message.objects.get(sentreminder__prescription__id=matt_prescription.id).state, Message.UNACKED)
		message_number = Message.objects.get(sentreminder__prescription__id=matt_prescription.id).message_number
		# Patient sends a bogus message
		c = Client()
		response = c.get('/textmessage_response/', {'from':matt.primary_phone_number, 'body':'bogus message'})
		self.assertEqual(Message.objects.get(sentreminder__prescription__id=matt_prescription.id).state, Message.UNACKED)
		self.assertEqual(response.content, "We did not understand your message. Reply 'help' for a list of available commands.")
		# Patient sends the correct message
		response = c.get('/textmessage_response/', {'from':matt.primary_phone_number, 'body':message_number})
		self.assertEqual(Message.objects.get(sentreminder__prescription__id=matt_prescription.id).state, Message.ACKED)
		self.assertEqual(response.content, "Be happy that you are taking care of your health!")


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
														 note="To make you strong", safety_net_on=True)
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
		send_time1 = time(hour=12, minute=0)
		send_time2 = time(hour=15, minute=0)
		send_time3 = time(hour=9, minute=0)
		send_time4 = time(hour=23, minute=59)
		send_time5 = time(hour=0, minute=6)

		# Sent every day at 12:00pm
		reminder1 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time1)
		# Sent every day at 9:00am
		reminder1a = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time3)
		# Sent every Monday at 12:00pm
		reminder2 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.WEEKLY, send_time=send_time1, day_of_week=1)
		# Sent every Wednesday at 12:00pm
		reminder3 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.WEEKLY, send_time=send_time1, day_of_week=3)
		# Sent first Wednesday of every month at 12:00pm
		reminder4 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=3, week_of_month=1)
		# Sent third Wednesday of every month at 12:00pm
		reminder5 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=3, week_of_month=3)
		# Sent last Monday of every month at 12:00pm
		reminder6 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=1, week_of_month=5)
		# Sent first day of every month at 9:00am
		reminder7 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time3, day_of_month=1)
		# Sent first day of every year at 3:00pm
		reminder8 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.YEARLY, send_time=send_time2, day_of_year=1)
		# Sent daily at 11:59pm
		reminder9 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time4)
		# Send second Thursday of every month at 12:06am
		reminder10 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time5, day_of_week=4, week_of_month=2)

		# Query at 12pm on 3rd Sunday, 11/17/13 should return only one reminder
		query_time = datetime(year=2013, month=11, day=17, hour=12, minute=0)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 1)
		self.assertEquals(reminder1, reminders.get(pk=reminder1.pk))
		# Query at 12pm on 2nd Monday, 11/11/13 should return two reminders
		query_time = datetime(year=2013, month=11, day=11, hour=12, minute=0)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 2)
		self.assertEquals(reminder1, reminders.get(pk=reminder1.pk))
		self.assertEquals(reminder2, reminders.get(pk=reminder2.pk))
		# Query at 12pm on 3rd Wednesday, 11/20/13 should return three reminders
		query_time = datetime(year=2013, month=11, day=20, hour=12, minute=0)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 3)
		self.assertEquals(reminder1, reminders.get(pk=reminder1.pk))
		self.assertEquals(reminder3, reminders.get(pk=reminder3.pk))
		self.assertEquals(reminder5, reminders.get(pk=reminder5.pk))
		# Query at 12pm on last Monday, 11/25/13 should return three reminders
		query_time = datetime(year=2013, month=11, day=25, hour=12, minute=0)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 3)
		self.assertEquals(reminder1, reminders.get(pk=reminder1.pk))
		self.assertEquals(reminder2, reminders.get(pk=reminder2.pk))
		self.assertEquals(reminder6, reminders.get(pk=reminder6.pk))
		# Query at 9am on first day of month, 11/1/13 should return two reminders
		query_time = datetime(year=2013, month=11, day=1, hour=9, minute=0)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 2)
		self.assertEquals(reminder1a, reminders.get(pk=reminder1a.pk))
		self.assertEquals(reminder7, reminders.get(pk=reminder7.pk))
		# Query at 3pm on first day of year, 1/1/13 should return one reminder
		query_time = datetime(year=2013, month=1, day=1, hour=15, minute=0)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 1)
		self.assertEquals(reminder8, reminders.get(pk=reminder8.pk))
		# Query at 12:01am on 1/3/13 should return one reminder
		query_time = datetime(year=2013, month=1, day=1, hour=0, minute=1)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 1)
		self.assertEquals(reminder9, reminders.get(pk=reminder9.pk))
		# Query at 12:01am on 1/3/13 with 1 minute offset no reminders
		query_time = datetime(year=2013, month=1, day=1, hour=0, minute=1)
		offset = timedelta(minutes=1)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 0)
		# Query at 12:07am on second Thursday, 2/14/13 should return two reminders
		query_time = datetime(year=2013, month=2, day=14, hour=0, minute=7)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		self.assertEquals(reminders.count(), 2)
		self.assertEquals(reminder9, reminders.get(pk=reminder9.pk))
		self.assertEquals(reminder10, reminders.get(pk=reminder10.pk))

	def test_create_message(self):
		send_time1 = time(hour=12, minute=0)
		reminder1 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time1)

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
		self.assertEquals(m3.message_number, 3)

		# Advance to the next day (18 hours later) and send another message. Test the message number
		sent_time = sent_time + timedelta(hours=18)
		reminder_model.datetime.set_fixed_now(sent_time)
		m4 = Message.objects.create(patient=self.minqi)
		m4.time_sent = sent_time
		m4.save()
		self.assertEquals(m4.message_number, 1)
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

	def test_textreminder_template(self):
		send_time = time(hour=9, minute=0)

		# Test message with one reminder
		reminder1 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time)
		reminder_list = ReminderTime.objects.filter(prescription=self.minqi_prescription)
		m1 = Message.objects.create(patient=self.minqi)
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('templates/textreminder.txt', dictionary)
		self.assertEquals(message_body, "Time to take your vitamin. Reply '1' when you finish.")

		# Test message with two reminders
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
														 note="To make you strong", safety_net_on=True)
		reminder2 = ReminderTime.objects.create(prescription=prescription2, repeat=ReminderTime.DAILY, send_time=send_time)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2))
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('templates/textreminder.txt', dictionary)
		self.assertEquals(message_body, "Time to take your vitamin and meditation. Reply '1' when you finish.")

		# Test message with three reminders
		lipitor = Drug.objects.create(name="lipitor")
		prescription3 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=lipitor,
														 note="To make you strong", safety_net_on=True)
		reminder3 = ReminderTime.objects.create(prescription=prescription3, repeat=ReminderTime.DAILY, send_time=send_time)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2) | Q(prescription=prescription3))
		dictionary = {'reminder_list': reminder_list, 'message_number':m1.message_number}
		message_body = render_to_string('templates/textreminder.txt', dictionary)
		self.assertEquals(message_body, "Time to take your vitamin, meditation and lipitor. Reply '1' when you finish.")

	def test_sendOneReminder(self):
		send_time = time(hour=9, minute=0)

		# Define a reminder
		reminder1 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time)
		reminder_list = ReminderTime.objects.filter(prescription=self.minqi_prescription)
		# Entry should not exist in database before sending message
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder1.prescription)
		self.assertEqual(message.count(), 0)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_sent, 0)
		# Send the message
		reminder_tasks.sendOneReminder(self.minqi, reminder_list)
		# Did the message get sent correctly?
		self.assertEqual(len(Message.objects.filter(patient=self.minqi)), 1)		
		self.assertEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "Time to take your vitamin. Reply '1' when you finish.")
		# Did database get correctly updated?
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder1.prescription)
		self.assertEqual(message.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=self.minqi_prescription, message=message[0])
		self.assertEqual(sentreminders.count(), 1)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_sent, 1)

		# Now send a message with two reminders
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
														 note="To make you strong", safety_net_on=True)
		reminder2 = ReminderTime.objects.create(prescription=prescription2, repeat=ReminderTime.DAILY, send_time=send_time)
		reminder_list = ReminderTime.objects.filter(Q(prescription=self.minqi_prescription) | Q(prescription=prescription2))
		# Entry for message with second prescription should not exist in database before sending message
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder2.prescription)
		self.assertEqual(message.count(), 0)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_sent, 1)
		self.assertEqual(Prescription.objects.get(id=prescription2.id).total_reminders_sent, 0)
		# Send the message
		reminder_tasks.sendOneReminder(self.minqi, reminder_list)
		# Did the message get sent correctly?
		self.assertEqual(len(Message.objects.filter(patient=self.minqi)), 2)
		# self.assertEqual(getLastSentMessageContent(), self.minqi.primary_phone_number + ": " + "Time to take your meditation and vitamin. Reply '2' when you finish.")
		# Did database get correctly updated?
		message = Message.objects.filter(patient=self.minqi, sentreminder__prescription=reminder2.prescription)
		self.assertEqual(message.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=self.minqi_prescription, message=message[0])
		self.assertEqual(sentreminders.count(), 1)
		sentreminders = SentReminder.objects.filter(prescription=prescription2, message=message[0])
		self.assertEqual(sentreminders.count(), 1)
		self.assertEqual(Prescription.objects.get(id=self.minqi_prescription.id).total_reminders_sent, 2)
		self.assertEqual(Prescription.objects.get(id=prescription2.id).total_reminders_sent, 1)


	def test_sendRemindersForNow(self):
		# A few more pills, prescriptions
		meditation = Drug.objects.create(name="meditation")
		prescription2 = Prescription.objects.create(prescriber=self.bob, patient=self.minqi, drug=meditation,
													note="To make you strong", safety_net_on=True)

		# make sure there's nothing in our sent message logs
		self.assertEqual(getLastSentMessageContent(), "")

		# try sending messages for when there are no scheduled reminders (12am)
		send_datetime = datetime(year=2013, month=4, day=11, hour=12, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertEqual(getLastSentMessageContent(), "")

		# Schedule some reminders at 9am for Minqi
		send_time = time(hour=9, minute=0)
		reminder1 = ReminderTime.objects.create(prescription=self.minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time)
		reminder2 = ReminderTime.objects.create(prescription=prescription2, repeat=ReminderTime.DAILY, send_time=send_time)
		
		# Send some reminders for now (12am)
		reminder_tasks.sendRemindersForNow()
		self.assertEqual(getLastSentMessageContent(), "")

		# Now change the time to 9am when reminders should be sent
		send_datetime = datetime(year=2013, month=4, day=11, hour=9, minute=0)
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
		matt_prescription = Prescription.objects.create(prescriber=self.bob, patient=matt, drug=self.vitamin,
														 note="To make you strong", safety_net_on=True)
		send_time2 = time(hour=10, minute=0)
		matt_reminder1 = ReminderTime.objects.create(prescription=matt_prescription, repeat=ReminderTime.DAILY, send_time=send_time2)

		# Change time to 10am and make sure message is sent
		send_datetime = datetime(year=2013, month=4, day=11, hour=10, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertEqual(getLastSentMessageContent(), matt.primary_phone_number + ": " + "Time to take your vitamin. Reply '1' when you finish.")

		# Schedule reminders for Matt and Minqi at 12am. 
		send_time3 = time(hour=12, minute=0)
		matt_reminder2 = ReminderTime.objects.create(prescription=matt_prescription, repeat=ReminderTime.DAILY, send_time=send_time3)
		minqi_reminder3 = ReminderTime.objects.create(prescription=prescription2, repeat=ReminderTime.DAILY, send_time=send_time3)
		# Move time to 11 to make sure no messages are sent.
		send_datetime = datetime(year=2013, month=4, day=11, hour=11, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertNotIn(matt.primary_phone_number + ": " + "Time to take your vitamin. Reply '2' when you finish.", getLastNSentMessageContent(2))
		self.assertNotIn(self.minqi.primary_phone_number + ": " + "Time to take your meditation. Reply '2' when you finish.", getLastNSentMessageContent(2))
		# Move time to 12 and make sure messages get sent.
		send_datetime = datetime(year=2013, month=4, day=11, hour=12, minute=0)
		reminder_tasks.datetime.set_fixed_now(send_datetime)
		reminder_tasks.sendRemindersForNow()
		self.assertIn(matt.primary_phone_number + ": " + "Time to take your vitamin. Reply '2' when you finish.", getLastNSentMessageContent(2))
		self.assertIn(self.minqi.primary_phone_number + ": " + "Time to take your meditation. Reply '2' when you finish.", getLastNSentMessageContent(2))




