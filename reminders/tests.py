"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase

from common.models import Drug
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import ReminderTime, Prescription, Message

from datetime import datetime, timedelta, time


class ReminderManagerTest(TestCase):
# Create records for test
	def test_reminders_at_time(self):
		#TODO(mgaba): Create fixtures that have populate DB with this information
		bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",  
										   primary_phone_number="2029163381", 
										   username="2029163381",
										   address_line1="4262 Cesar Chavez", postal_code="94131", 
										   city="San Francisco", state_province="CA", country_iso_code="US")
		vitamin = Drug.objects.create(name="Vitamin")
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  username="8569067308",
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		minqi_prescription = Prescription.objects.create(prescriber=bob, patient=minqi, drug=vitamin,
														 note="To make you strong", safety_net_on=True)



		send_time1 = time(hour=12, minute=0)
		send_time2 = time(hour=15, minute=0)
		send_time3 = time(hour=9, minute=0)
		send_time4 = time(hour=23, minute=59)
		send_time5 = time(hour=0, minute=6)

		# Sent every day at 12:00pm
		reminder1 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time1)
		# Sent every day at 9:00am
		reminder1a = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time3)
		# Sent every Monday at 12:00pm
		reminder2 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.WEEKLY, send_time=send_time1, day_of_week=1)
		# Sent every Wednesday at 12:00pm
		reminder3 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.WEEKLY, send_time=send_time1, day_of_week=3)
		# Sent first Wednesday of every month at 12:00pm
		reminder4 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=3, week_of_month=1)
		# Sent third Wednesday of every month at 12:00pm
		reminder5 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=3, week_of_month=3)
		# Sent last Monday of every month at 12:00pm
		reminder6 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=1, week_of_month=5)
		# Sent first day of every month at 9:00am
		reminder7 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time3, day_of_month=1)
		# Sent first day of every year at 3:00pm
		reminder8 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.YEARLY, send_time=send_time2, day_of_year=1)
		# Sent daily at 11:59pm
		reminder9 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time4)
		# Send second Thursday of every month at 12:06am
		reminder10 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time5, day_of_week=4, week_of_month=2)

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

	def test_patients_from_reminders(self):
		#TODO(mgaba): Create fixtures that have populate DB with this information
		bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",  
										   primary_phone_number="2029163381", 
										   username="2029163381",
										   address_line1="4262 Cesar Chavez", postal_code="94131", 
										   city="San Francisco", state_province="CA", country_iso_code="US")
		vitamin = Drug.objects.create(name="Vitamin")
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  username="8569067308",
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		minqi_prescription = Prescription.objects.create(prescriber=bob, patient=minqi, drug=vitamin,
														 note="To make you strong", safety_net_on=True)

		send_time1 = time(hour=12, minute=0)
		send_time2 = time(hour=15, minute=0)
		send_time3 = time(hour=9, minute=0)
		send_time4 = time(hour=23, minute=59)
		send_time5 = time(hour=0, minute=6)

		# Sent every day at 12:00pm
		reminder1 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time1)
		# Sent every day at 9:00am
		reminder1a = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time3)
		# Sent every Monday at 12:00pm
		reminder2 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.WEEKLY, send_time=send_time1, day_of_week=1)
		# Sent every Wednesday at 12:00pm
		reminder3 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.WEEKLY, send_time=send_time1, day_of_week=3)
		# Sent first Wednesday of every month at 12:00pm
		reminder4 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=3, week_of_month=1)
		# Sent third Wednesday of every month at 12:00pm
		reminder5 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=3, week_of_month=3)
		# Sent last Monday of every month at 12:00pm
		reminder6 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time1, day_of_week=1, week_of_month=5)
		# Sent first day of every month at 9:00am
		reminder7 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time3, day_of_month=1)
		# Sent first day of every year at 3:00pm
		reminder8 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.YEARLY, send_time=send_time2, day_of_year=1)
		# Sent daily at 11:59pm
		reminder9 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time4)
		# Send second Thursday of every month at 12:06am
		reminder10 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.MONTHLY, send_time=send_time5, day_of_week=4, week_of_month=2)

		query_time = datetime(year=2013, month=11, day=20, hour=12, minute=0)
		offset = timedelta(minutes=15)
		reminders = ReminderTime.objects.reminders_at_time(query_time, offset)
		distinct_reminders = reminders.distinct('prescription__patient')
		p = distinct_reminders[0].prescription.patient
		p_pills = reminders.filter(prescription__patient=p)
		print p_pills

	def test_create_message(self):
		bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",  
										   primary_phone_number="2029163381", 
										   username="2029163381",
										   address_line1="4262 Cesar Chavez", postal_code="94131", 
										   city="San Francisco", state_province="CA", country_iso_code="US")
		vitamin = Drug.objects.create(name="Vitamin")
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  username="8569067308",
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		minqi_prescription = Prescription.objects.create(prescriber=bob, patient=minqi, drug=vitamin,
														 note="To make you strong", safety_net_on=True)
		send_time1 = time(hour=12, minute=0)
		reminder1 = ReminderTime.objects.create(prescription=minqi_prescription, repeat=ReminderTime.DAILY, send_time=send_time1)

		# Create a message and test the message number
		m1 = Message.objects.create(patient=minqi)
		self.assertEquals(m1.message_number, 1)

		# Create a second message and test the message number
		m2 = Message.objects.create(patient=minqi)
		self.assertEquals(m2.message_number, 2)

		# Ack the second message and first message, create a new message, and test the message number
		m1.state = Message.ACKED
		m1.save()
		m2.state = Message.ACKED
		m2.save()
		m3 = Message.objects.create(patient=minqi)
		self.assertEquals(m3.message_number, 1)

		# Create a second message (message number should equal 2), ack that message, and create another message (message number should equal 2 again)
		m4 = Message.objects.create(patient=minqi)
		self.assertEquals(m4.message_number, 2)
		m4.state = Message.ACKED
		m4.save()
		m5 = Message.objects.create(patient=minqi)
		self.assertEquals(m5.message_number, 2)

		# Ack message number 1, create another message, and verify this message has number 3 (because 2 is still unacked)
		m3.state = Message.ACKED
		m3.save()
		m6 = Message.objects.create(patient=minqi)
		self.assertEquals(m6.message_number, 3)


