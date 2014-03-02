# Unit tests for webapp views
# Execute views under various conditions and ensure database 
# is in a coherent state.

import datetime

from django.http import HttpResponseNotFound
from django.test import TestCase, Client

import mock

from common.utilities import next_weekday
from common.models import Drug
from patients.models import PatientProfile, SafetyNetRelationship, PrimaryContactRelationship
from doctors.models import DoctorProfile
from reminders.models import Prescription, ReminderTime, Message
from webapp.views import create_patient, retrieve_patient, \
	delete_patient, update_patient, create_reminder, delete_reminder

c = Client()

class CreatePatientTest(TestCase):
	def setUp(self):
		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')

	def test_invalid_request(self):
		# empty full name
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'', 'primary_phone_number':'8569067308'})
		self.assertEqual(response.status_code, 400)

		# empty phone number
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Minqi Jiang', 'primary_phone_number':''})
		self.assertEqual(response.status_code, 400)

	def test_create_new_patient(self):
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Matt Gaba', 'primary_phone_number':'2147094720'})
		self.assertEqual(response.status_code, 200)

		result = PatientProfile.objects.filter(first_name="Matt")
		self.assertTrue(result.exists())
		self.assertTrue(len(result) == 1)

		patient = result[0]
		self.assertEqual(patient.first_name, 'Matt')
		self.assertEqual(patient.last_name, 'Gaba')
		self.assertEqual(patient.full_name, "Matt Gaba")
		self.assertEqual(patient.primary_phone_number, '+12147094720')

		# make sure welcome message is sent
		welcome_count = len(ReminderTime.objects.filter(
			to=patient, reminder_type=ReminderTime.WELCOME))
		self.assertEqual(welcome_count, 1)

	def test_create_existing_patient(self):
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Minqi Jiang', 'primary_phone_number':'8569067308'})
		self.assertEqual(response.status_code, 200)

		result = PatientProfile.objects.filter(first_name='Minqi')
		self.assertTrue(result.exists())
		self.assertTrue(len(result) == 1)

		patient = result[0]
		self.assertEqual(patient.first_name, 'Minqi')
		self.assertEqual(patient.last_name, 'Jiang')
		self.assertEqual(patient.primary_phone_number, '+18569067308')

		welcome_count = len(ReminderTime.objects.filter(
			to=patient, reminder_type=ReminderTime.WELCOME))
		self.assertEqual(welcome_count, 0)

# Unit tests for retrieve patient
class RetrievePatientTest(TestCase):
	def setUp(self):
		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')

	def test_invalid_request(self):
		# empty patient id
		response = c.get('/fishfood/patients/', {'p_id':''})
		self.assertEqual(response.status_code, 400)

	def test_retrieve_nonexistent_patient(self):
		response = c.get('/fishfood/patients/', {'p_id':'5'})
		self.assertEqual(response.status_code, 400)

	def test_retrieve_existing_patient(self):
		response = c.get('/fishfood/patients/', {'p_id':str(self.patient1.id)})
		self.assertEqual(response.status_code, 200)

# Unit tests for update patient
class UpdatePatientTest(TestCase):
	def setUp(self):
		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')

	def test_invalid_request(self):
		# invalid p_id
		response = c.post('/fishfood/patients/update/', 
			{'full_name':'Minch Jiang', 
			'primary_phone_number':'8569067308',
			'p_id':''})
		self.assertEqual(response.status_code, 400)

		# invalid full name
		response = c.post('/fishfood/patients/update/', 
			{'full_name':'', 
			'primary_phone_number':'8569067308',
			'p_id':str(self.patient1.id)})
		self.assertEqual(response.status_code, 400)

		# invalid phone number
		response = c.post('/fishfood/patients/update/', 
			{'full_name':'Minch Jiang', 
			'primary_phone_number':'555',
			'p_id':str(self.patient1.id)})
		self.assertEqual(response.status_code, 400)

	def test_update_nonexistent_patient(self):
		response = c.post('/fishfood/patients/update/', 
			{'full_name':'Non Existent', 
			'primary_phone_number':'5555555555',
			'p_id':str(self.patient1.id + 1)})
		self.assertEqual(response.status_code, 400)

	def test_update_existing_patient(self):
		response = c.post('/fishfood/patients/update/', 
			{'full_name':'Minch Jiang', 
			'primary_phone_number':'555-555-5555',
			'p_id':str(self.patient1.id)})
		self.assertEqual(response.status_code, 200)

		patient1 = PatientProfile.objects.get(id=self.patient1.id)

		self.assertEqual(patient1.first_name, 'Minch')
		self.assertEqual(patient1.last_name, 'Jiang')
		self.assertEqual(patient1.primary_phone_number, '+15555555555')

# Unit tests for delete patient
class DeletePatientTest(TestCase):
	def setUp(self):
		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')
		self.doctor = DoctorProfile.objects.create(
			first_name='Test', last_name='Doctor', primary_phone_number='+15555555555')
		self.drug1 = Drug.objects.create(name='drug1')
		self.prescription1 = Prescription.objects.create(
			prescriber=self.doctor, patient=self.patient1, drug=self.drug1)

		self.welcome_reminder = ReminderTime.objects.create(
			to=self.patient1, reminder_type=ReminderTime.WELCOME, repeat=ReminderTime.DAILY,
			send_time=datetime.datetime.now())
		self.refill_reminder = ReminderTime.objects.create(
			to=self.patient1, reminder_type=ReminderTime.REFILL, repeat=ReminderTime.DAILY,
			prescription=self.prescription1, send_time=datetime.datetime.now())
		self.medication_reminder = ReminderTime.objects.create(
			to=self.patient1, reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY,
			prescription=self.prescription1, send_time=datetime.datetime.now())

		self.patient1.add_safetynet_member(
			patient_relationship='Friend', first_name='Matt', last_name='Gaba',
			primary_phone_number='+12147094720', birthday='1989-10-13')
		self.patient1.add_primary_contact_member(
			patient_relationship='Friend', first_name='Matt', last_name='Gaba',
			primary_phone_number='+12147094720', birthday='1989-10-13')

	def test_invalid_request(self):
		# no patient id
		response = c.post('/fishfood/patients/delete/', {'p_id':''})
		self.assertEqual(response.status_code, 400)

	def test_delete_nonexistent_patient(self):
		response = c.post('/fishfood/patients/delete/', {'p_id':self.patient1.id + 1})
		self.assertEqual(response.status_code, 400)

	def test_delete_existing_patient(self):
		response = c.post('/fishfood/patients/delete/', {'p_id':self.patient1.id})
		self.assertEqual(response.status_code, 302) # redirected to main fishfood view

		result = PatientProfile.objects.filter(id=self.patient1.id)
		self.assertTrue(result.exists())

		patient = result.first()
		self.assertTrue(patient.status == PatientProfile.QUIT)

		self.assertEqual(len(Prescription.objects.filter(patient=self.patient1)), 0)
		self.assertEqual(len(ReminderTime.objects.filter(to=self.patient1)), 0)
		self.assertEqual(len(SafetyNetRelationship.objects.filter(
			source_patient=self.patient1)), 0)
		self.assertEqual(len(PrimaryContactRelationship.objects.filter(
			source_patient=self.patient1)), 0)

# Unit tests for create reminder
class CreateReminderTest(TestCase):
	def setUp(self):
		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')
		self.doctor = DoctorProfile.objects.create(
						first_name="Smartdose", last_name="", 
						primary_phone_number="+18569067308", 
						birthday=datetime.date(2014, 1, 28))
		self.drug1 = Drug.objects.create(name='drug1')
		self.prescription1 = Prescription.objects.create(
			prescriber=self.doctor, patient=self.patient1, drug=self.drug1)

	def test_invalid_request(self):
		# no patient_id	
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':'', 'drug_name':'drug1', 
			'reminder_time':'9:00 AM', 'mon':True})
		self.assertEqual(response.status_code, 400)

		# no drug name
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'', 
			'reminder_time':'9:00 AM', 'mon':True})
		self.assertEqual(response.status_code, 400)

		# no reminder time
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'', 'mon':True})
		self.assertEqual(response.status_code, 400)

		# no days selected
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 400)

	def test_create_for_nonexistent_patient(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id + 1), 'drug_name':'drug1', 
			'reminder_time':'9:00 AM', 'mon':True})
		self.assertEqual(response.status_code, 400)

	def test_create_daily_reminder_with_colliding_daily_reminder(self):
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.MEDICATION,
			send_time = send_datetime, 
			repeat=ReminderTime.DAILY, 
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(ReminderTime.objects.all())

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 
			'mon':True, 'tue':True, 'wed':True,
			'thu':True, 'fri':True, 'sat':True, 'sun':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(ReminderTime.objects.all())
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY))
		weekly_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.WEEKLY)) 
		self.assertEqual(daily_reminder_count, 1)
		self.assertEqual(weekly_reminder_count, 0)

	def test_create_daily_reminder_with_colliding_weekly_reminder(self):
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.MEDICATION,
			send_time = send_datetime, 
			repeat=ReminderTime.WEEKLY, 
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(ReminderTime.objects.all())

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 
			'mon':True, 'tue':True, 'wed':True,
			'thu':True, 'fri':True, 'sat':True, 'sun':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(ReminderTime.objects.all())
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY))
		weekly_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.WEEKLY)) 
		self.assertEqual(daily_reminder_count, 1)
		self.assertEqual(weekly_reminder_count, 0)

	def test_create_weekly_reminder_with_colliding_daily_reminder(self):
		# create daily reminder to collide on Mon at 9:00 AM
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.MEDICATION,
			send_time = send_datetime, 
			repeat=ReminderTime.DAILY, 
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(ReminderTime.objects.all())

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(ReminderTime.objects.all())
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY))
		weekly_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.WEEKLY)) 
		self.assertEqual(daily_reminder_count, 1)
		self.assertEqual(weekly_reminder_count, 0)
		
	def test_create_weekly_reminder_with_colliding_weekly_reminder(self):
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.MEDICATION,
			send_time = send_datetime, 
			repeat=ReminderTime.WEEKLY, 
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(ReminderTime.objects.all())

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(ReminderTime.objects.all())
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY))
		weekly_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.WEEKLY)) 
		self.assertEqual(daily_reminder_count, 0)
		self.assertEqual(weekly_reminder_count, 1)

	def test_create_with_refill_and_prescription_not_filled(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True, 'send_refill_reminder':True})
		self.assertEqual(response.status_code, 200)

		weekly_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.WEEKLY)) 
		self.assertEqual(weekly_reminder_count, 1)

		refill_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.REFILL)) 
		self.assertEqual(refill_reminder_count, 1)

	def test_create_with_refill_and_prescription_filled(self):
		self.prescription1.filled = True # fill the prescription
		self.prescription1.save()

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True, 'send_refill_reminder':True})
		self.assertEqual(response.status_code, 200)

		weekly_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.WEEKLY)) 
		self.assertEqual(weekly_reminder_count, 1)

		refill_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.REFILL)) 
		self.assertEqual(refill_reminder_count, 0)

	def test_create_daily_reminder_without_colliding_reminder(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00',
			'mon':True, 'tue':True, 'wed':True,
			'thu':True, 'fri':True, 'sat':True, 'sun':True})
		self.assertEqual(response.status_code, 200)

		daily_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.DAILY)) 
		self.assertEqual(daily_reminder_count, 1)

		refill_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.REFILL)) 
		self.assertEqual(refill_reminder_count, 0)

	def test_create_weekly_reminder_without_colliding_reminder(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		weekly_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, repeat=ReminderTime.WEEKLY)) 
		self.assertEqual(weekly_reminder_count, 1)

		refill_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.REFILL)) 
		self.assertEqual(refill_reminder_count, 0)

	def test_create_reminder_without_refill_reminder(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug3', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		refill_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.REFILL)) 
		self.assertEqual(refill_reminder_count, 0)

		# if reminder created w/o refill reminder, filled should be true
		self.assertTrue(Prescription.objects.get(drug__name='drug3').filled, True)

# Unit tests for delete reminder
class DeleteReminderTest(TestCase):
	def setUp(self):
		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')
		self.doctor = DoctorProfile.objects.create(
						first_name="Smartdose", last_name="", 
						primary_phone_number="+18569067308", 
						birthday=datetime.date(2014, 1, 28))
		self.drug1 = Drug.objects.create(name='drug1')
		self.prescription1 = Prescription.objects.create(
			prescriber=self.doctor, patient=self.patient1, drug=self.drug1)

		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		self.refill_reminder = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.REFILL,
			send_time = send_datetime, 
			repeat=ReminderTime.DAILY, 
			prescription=self.prescription1)
		self.med_reminder1 = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.MEDICATION,
			send_time = send_datetime, 
			repeat=ReminderTime.DAILY, 
			prescription=self.prescription1,
			day_of_week=1)
		send_datetime = next_weekday(send_datetime, 1)
		self.med_reminder2 = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.MEDICATION,
			send_time = send_datetime, 
			repeat=ReminderTime.DAILY, 
			prescription=self.prescription1,
			day_of_week=2)
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(10,0))
		send_datetime = next_weekday(send_datetime, 1)
		self.med_reminder3 = ReminderTime.objects.create(
			to=self.patient1, 
			reminder_type=ReminderTime.MEDICATION,
			send_time = send_datetime, 
			repeat=ReminderTime.WEEKLY, 
			prescription=self.prescription1,
			day_of_week=8)

	def test_invalid_request(self):
		# no patient id
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':'', 'drug_name':'drug1', 'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 400)

		# no drug name
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 'drug_name':'', 
			'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 400)

		# whitespace drug name
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 'drug_name':'   ', 
			'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 400)

		# no reminder time
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':''})
		self.assertEqual(response.status_code, 400)

	def test_delete_for_nonexistent_patient(self):
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id + 1), 'drug_name':'drug1', 
			'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 400)

	def test_delete_for_nonexistent_prescription(self):
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 
			'drug_name':'unprescribed_drug', 'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 400)

	def test_delete_nonexistent_reminder_time(self):
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 
			'drug_name':'unprescribed_drug', 'drug1':'10:00 AM'})
		self.assertEqual(response.status_code, 400)

	def test_delete_existing_reminder_for_one_time(self):
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 
			'drug_name':'drug1', 'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 200)

		remaining_med_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, prescription__drug__name='drug1'))
		self.assertEqual(remaining_med_reminder_count, 1)

		remaining_refill_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.REFILL, prescription__drug__name='drug1'))
		self.assertEqual(remaining_refill_reminder_count, 1)

	def test_delete_existing_reminder_for_all_times(self):
		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 
			'drug_name':'drug1', 'reminder_time':'9:00 AM'})
		self.assertEqual(response.status_code, 200)

		response = c.post('/fishfood/reminders/delete/', 
			{'p_id':str(self.patient1.id), 
			'drug_name':'drug1', 'reminder_time':'10:00 AM'})
		self.assertEqual(response.status_code, 200)

		remaining_med_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.MEDICATION, prescription__drug__name='drug1'))
		self.assertEqual(remaining_med_reminder_count, 0)

		remaining_refill_reminder_count = len(ReminderTime.objects.filter(
			reminder_type=ReminderTime.REFILL, prescription__drug__name='drug1'))
		self.assertEqual(remaining_refill_reminder_count, 0)
