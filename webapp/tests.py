# Unit tests for webapp views
# Execute views under various conditions and ensure database 
# is in a coherent state.

import datetime

from django.http import HttpResponseNotFound
from django.test import TestCase, Client

import mock

from common.utilities import next_weekday
from common.models import Drug
from patients.models import PatientProfile, SafetyNetRelationship
from doctors.models import DoctorProfile
from reminders.models import Prescription, Notification, Message
from webapp.views import create_patient, retrieve_patient, \
	delete_patient, update_patient, create_reminder, delete_reminder

from guardian.shortcuts import assign_perm

# set up test client
c = Client()

class UserRegistrationTest(TestCase):
	def setUp(self):
		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308',
			email='minqi@smartdose.co',
			num_caregivers=1)
		self.patient2 = PatientProfile.objects.create(
			first_name='Matt', last_name='Gaba', primary_phone_number='+12147094720',
			email='matt@smartdose.co',
			num_caregivers=1)

	def test_invalid_request(self):
		# no full name
		response = c.post('/fishfood/signup/', 
			{'full_name':'', 'primary_phone_number':'1234567890', 
			'email':'test@smartdose.co', 'password1':'testpassword',
			'password2':'testpassword'})
		self.assertEqual(response.status_code, 400)

		# no email
		response = c.post('/fishfood/signup/', 
			{'full_name':'Test User', 'primary_phone_number':'1234567890', 
			'email':'', 'password1':'testpassword', 'password2':'testpassword'})
		self.assertEqual(response.status_code, 400)

		# no primary phone number
		response = c.post('/fishfood/signup/', 
			{'full_name':'Test User', 'primary_phone_number':'', 
			'email':'test@smartdose.co', 'password1':'testpassword',
			'password2':'testpassword'})
		self.assertEqual(response.status_code, 400)

		# no password
		response = c.post('/fishfood/signup/', 
			{'full_name':'Test User', 'primary_phone_number':'1234567890', 
			'email':'test@smartdose.co', 'password1':'', 
			'password2':''})

		# mismatched passwords
		response = c.post('/fishfood/signup/', 
			{'full_name':'Test User', 'primary_phone_number':'1234567890', 
			'email':'test@smartdose.co', 'password1':'test', 
			'password2':'testpassword'})
		self.assertEqual(response.status_code, 400)

	def test_register_existing_email(self):
		response = c.post('/fishfood/signup/', 
			{'full_name':'Test User', 'primary_phone_number':'1234567890', 
			'email':'minqi@smartdose.co', 'password1':'testpassword',
			'password2':'testpassword'})
		self.assertEqual(response.status_code, 400)

	def test_register_existing_phone_number(self):
		response = c.post('/fishfood/signup/', 
			{'full_name':'Test User', 'primary_phone_number':'8569067308', 
			'email':'test@smartdose.co', 'password1':'testpassword',
			'password2':'testpassword'})
		self.assertEqual(response.status_code, 400)

	def test_register_new_user(self):
		response = c.post('/fishfood/signup/', 
			{'full_name':'Test User', 'primary_phone_number':'1234567890', 
			'email':'test@smartdose.co', 'password1':'testpassword',
			'password2':'testpassword'})
		self.assertEqual(response.status_code, 302)

		q = PatientProfile.objects.filter(full_name='Test User')
		self.assertTrue(q.exists())
		self.assertEqual(q[0].num_caregivers, 1)


class CreatePatientTest(TestCase):
	def setUp(self):
		client_user = PatientProfile.objects.create(
			first_name='Test', last_name='User', primary_phone_number='+10000000000',
			num_caregivers=1)
		client_user.set_password('testpassword')
		client_user.save()
		c.login(phone_number='+10000000000', password='testpassword')
		self.client_user = client_user

		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308',
			num_caregivers=1)

		self.patient2 = PatientProfile.objects.create(
			first_name='Test', last_name='User2', primary_phone_number='+11111111111',
			num_caregivers=1)

		self.patient3 = PatientProfile.objects.create(
			first_name='Test', last_name='User3', primary_phone_number='+11111111112',
			num_caregivers=0)

	def test_invalid_request(self):
		# empty full name
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'', 'primary_phone_number':'5555555555'})
		self.assertEqual(response.status_code, 400)

		# empty phone number
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Matt Gaba', 'primary_phone_number':''})
		self.assertEqual(response.status_code, 400)

	def test_create_patient_as_primary_contact(self):
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Matt Gaba', 'primary_phone_number':'10000000000'})
		self.assertEqual(response.status_code, 200)

		q = PatientProfile.objects.filter(full_name='Matt Gaba')
		self.assertTrue(q.exists())

		p = q[0]
		self.assertTrue(not p.primary_phone_number)
		self.assertEqual(p.primary_contact, self.client_user)
		self.assertEqual(p.num_caregivers, 1)
		self.assertEqual(p.status, PatientProfile.NEW)

		q = Notification.objects.filter(to=p, reminder_type=Notification.WELCOME)
		self.assertEqual(len(q), 1)

	def test_create_patient_existing_unmanaged_account(self):
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Test UserChanged', 'primary_phone_number':'11111111112'})
		self.assertEqual(response.status_code, 200)

		q = PatientProfile.objects.filter(primary_phone_number='+1111111112')
		p = q[0]
		self.assertTrue(q.exists())
		self.assertEqual(p.full_name, 'Test UserChanged')
		self.assertEqual(p.num_caregivers, 1)
		self.assertEqual(p.status, PatientProfile.NEW)

		q = Notification.objects.filter(to=p, reminder_type=Notification.WELCOME)
		self.assertEqual(len(q), 1)

	def test_create_patient_existing_managed_account(self):
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Test User2', 'primary_phone_number':'11111111111'})
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
		self.assertEqual(patient.num_caregivers, 1)

		q = SafetyNetRelationship.objects.filter(
			source_patient__id=patient.id, target_patient__id=self.client_user.id)
		self.assertTrue(q.exists())

		self.assertTrue(self.client_user.has_perm('manage_patient_profile', patient))

		# make sure welcome message is sent
		welcome_count = len(Notification.objects.filter(
			to=patient, reminder_type=Notification.WELCOME))
		self.assertEqual(welcome_count, 1)

	def test_create_existing_patient(self):
		# creating a patient that is already managed
		response = c.post('/fishfood/patients/new/', 
			{'full_name':'Minqi Jiang', 'primary_phone_number':'8569067308'})
		self.assertEqual(response.status_code, 400)

		result = PatientProfile.objects.filter(first_name='Minqi')
		self.assertTrue(result.exists())
		self.assertTrue(len(result) == 1)

		patient = result[0]
		self.assertEqual(patient.first_name, 'Minqi')
		self.assertEqual(patient.last_name, 'Jiang')
		self.assertEqual(patient.primary_phone_number, '+18569067308')
		self.assertEqual(patient.num_caregivers, 1)

		welcome_count = len(Notification.objects.filter(
			to=patient, reminder_type=Notification.WELCOME))
		self.assertEqual(welcome_count, 0)


# Unit tests for retrieve patient
class RetrievePatientTest(TestCase):
	def setUp(self):
		client_user = PatientProfile.objects.create (
			first_name='Test', last_name='User', primary_phone_number='+10000000000')
		client_user.set_password('testpassword')
		client_user.save()
		self.client_user = client_user
		c.login(phone_number='+10000000000', password='testpassword')

		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')

	def test_invalid_request(self):
		# empty patient id
		response = c.get('/fishfood/patients/', {'p_id':''})
		self.assertEqual(response.status_code, 400)

	def test_retrieve_nonexistent_patient(self):
		response = c.get('/fishfood/patients/', {'p_id':'100'})
		self.assertEqual(response.status_code, 400)

	def test_retrieve_existing_patient(self):
		# no permission
		response = c.get('/fishfood/patients/', {'p_id':str(self.patient1.id)})
		self.assertEqual(response.status_code, 400)

		# with permission
		assign_perm('manage_patient_profile', self.client_user, self.patient1)
		response = c.get('/fishfood/patients/', {'p_id':str(self.patient1.id)})
		self.assertEqual(response.status_code, 200)


# Unit tests for update patient
class UpdatePatientTest(TestCase):
	def setUp(self):
		client_user = PatientProfile.objects.create (
			first_name='Test', last_name='User', primary_phone_number='+10000000000')
		client_user.set_password('testpassword')
		client_user.save()
		self.client_user = client_user
		c.login(phone_number='+10000000000', password='testpassword')

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
			'p_id':str(self.patient1.id + 10)})
		self.assertEqual(response.status_code, 400)

	def test_update_existing_patient(self):
		# without permission
		response = c.post('/fishfood/patients/update/', 
			{'full_name':'Minch Jiang', 
			'primary_phone_number':'555-555-5555',
			'p_id':str(self.patient1.id)})
		self.assertEqual(response.status_code, 400)

		# with permission
		assign_perm('manage_patient_profile', self.client_user, self.patient1)
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
		client_user = PatientProfile.objects.create (
			first_name='Test', last_name='User', primary_phone_number='+10000000000')
		client_user.set_password('testpassword')
		client_user.save()
		self.client_user = client_user
		c.login(phone_number='+10000000000', password='testpassword')

		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308',
			num_caregivers=1)
		self.prescriber = client_user
		self.drug1 = Drug.objects.create(name='drug1')
		self.prescription1 = Prescription.objects.create(
			prescriber=self.prescriber, patient=self.patient1, drug=self.drug1)

		self.welcome_reminder = Notification.objects.create(
			to=self.patient1, reminder_type=Notification.WELCOME, repeat=Notification.DAILY,
			send_time=datetime.datetime.now())
		self.refill_reminder = Notification.objects.create(
			to=self.patient1, reminder_type=Notification.REFILL, repeat=Notification.DAILY,
			prescription=self.prescription1, send_time=datetime.datetime.now())
		self.medication_reminder = Notification.objects.create(
			to=self.patient1, reminder_type=Notification.MEDICATION, repeat=Notification.DAILY,
			prescription=self.prescription1, send_time=datetime.datetime.now())

		self.patient2 = PatientProfile.objects.create(
					first_name='A', last_name='Patient', primary_phone_number='+15555555555',
					num_caregivers=2, status=PatientProfile.ACTIVE)
		self.prescription2 = Prescription.objects.create(
			prescriber=self.prescriber, patient=self.patient2, drug=self.drug1)

		self.welcome_reminder2 = Notification.objects.create(
			to=self.patient2, reminder_type=Notification.WELCOME, repeat=Notification.DAILY,
			send_time=datetime.datetime.now())
		self.refill_reminder2 = Notification.objects.create(
			to=self.patient2, reminder_type=Notification.REFILL, repeat=Notification.DAILY,
			prescription=self.prescription2, send_time=datetime.datetime.now())
		self.medication_reminder2 = Notification.objects.create(
			to=self.patient2, reminder_type=Notification.MEDICATION, repeat=Notification.DAILY,
			prescription=self.prescription2, send_time=datetime.datetime.now())

		self.patient1.add_safety_net_contact(target_patient=self.patient2, relationship='Friend')
		self.patient2.add_safety_net_contact(target_patient=self.patient1, relationship='Friend')

	def test_invalid_request(self):
		# no patient id
		response = c.post('/fishfood/patients/delete/', {'p_id':''})
		self.assertEqual(response.status_code, 400)

	def test_delete_nonexistent_patient(self):
		response = c.post('/fishfood/patients/delete/', {'p_id':self.patient1.id + 10})
		self.assertEqual(response.status_code, 400)

	def test_delete_existing_patient(self):
		# no permission
		response = c.post('/fishfood/patients/delete/', {'p_id':self.patient1.id})
		self.assertEqual(response.status_code, 400) 

		# with permission
		assign_perm('manage_patient_profile', self.client_user, self.patient1)
		response = c.post('/fishfood/patients/delete/', {'p_id':self.patient1.id})
		self.assertEqual(response.status_code, 302) # redirected to main fishfood view

		result = PatientProfile.objects.filter(id=self.patient1.id)
		self.assertTrue(result.exists())

		patient = result.first()
		self.assertTrue(patient.status == PatientProfile.QUIT)
		self.assertTrue(patient.num_caregivers == 0)

		self.assertEqual(len(Prescription.objects.filter(patient=self.patient1)), 0)
		self.assertEqual(len(Notification.objects.filter(to=self.patient1)), 0)
		self.assertEqual(len(SafetyNetRelationship.objects.filter(
			source_patient=self.patient1)), 0)

		q = SafetyNetRelationship.objects.filter(
			source_patient__id=patient.id, target_patient__id=self.client_user.id)
		self.assertTrue(not q.exists())
		self.assertTrue(not self.client_user.has_perm('view_patient_profile', patient))
		self.assertTrue(not self.client_user.has_perm('manage_patient_profile', patient))

	def test_delete_existing_patient_multiple_caregivers(self):
		assign_perm('manage_patient_profile', self.client_user, self.patient2)
		response = c.post('/fishfood/patients/delete/', {'p_id':self.patient2.id})
		self.assertEqual(response.status_code, 302)

		result = PatientProfile.objects.filter(id=self.patient2.id)
		self.assertTrue(result.exists())

		patient = result.first()
		self.assertTrue(patient.status == PatientProfile.ACTIVE)
		self.assertTrue(patient.num_caregivers == 1)

		self.assertEqual(len(Prescription.objects.filter(patient=self.patient2)), 1)
		self.assertEqual(len(Notification.objects.filter(to=self.patient2)), 3)
		self.assertEqual(len(SafetyNetRelationship.objects.filter(
			source_patient=self.patient2)), 1)
		self.assertTrue(not self.client_user.has_perm('view_patient_profile', patient))
		self.assertTrue(self.client_user.has_perm('manage_patient_profile', patient))


# Unit tests for create reminder
class CreateReminderTest(TestCase):
	def setUp(self):
		client_user = PatientProfile.objects.create (
			first_name='Test', last_name='User', primary_phone_number='+10000000000')
		client_user.set_password('testpassword')
		client_user.save()
		c.login(phone_number='+10000000000', password='testpassword')

		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')
		self.patient2 = PatientProfile.objects.create(
			first_name='Matt', last_name='Gaba', primary_phone_number='+12147094720')
		self.prescriber = client_user
		self.drug1 = Drug.objects.create(name='drug1')
		self.prescription1 = Prescription.objects.create(
			prescriber=self.prescriber, patient=self.patient1, drug=self.drug1)
		self.prescription2 = Prescription.objects.create(
			prescriber=self.prescriber, patient=self.patient2, drug=self.drug1)

		assign_perm('manage_patient_profile', client_user, self.patient1)

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
			{'p_id':str(self.patient1.id + 10), 'drug_name':'drug1', 
			'reminder_time':'9:00 AM', 'mon':True})
		self.assertEqual(response.status_code, 400)

	def test_create_daily_reminder_with_colliding_daily_reminder(self):
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.DAILY,
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(Notification.objects.filter(to=self.patient1))

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 
			'mon':True, 'tue':True, 'wed':True,
			'thu':True, 'fri':True, 'sat':True, 'sun':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(Notification.objects.filter(to=self.patient1))
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.DAILY))
		weekly_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.WEEKLY))
		self.assertEqual(daily_reminder_count, 1)
		self.assertEqual(weekly_reminder_count, 0)

	def test_create_daily_reminder_with_colliding_weekly_reminder(self):
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.WEEKLY,
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(Notification.objects.filter(to=self.patient1))

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 
			'mon':True, 'tue':True, 'wed':True,
			'thu':True, 'fri':True, 'sat':True, 'sun':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(Notification.objects.filter(to=self.patient1))
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.DAILY))
		weekly_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.WEEKLY))
		self.assertEqual(daily_reminder_count, 1)
		self.assertEqual(weekly_reminder_count, 0)

	def test_create_weekly_reminder_with_colliding_daily_reminder(self):
		# create daily reminder to collide on Mon at 9:00 AM
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.DAILY,
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(Notification.objects.filter(to=self.patient1))

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(Notification.objects.filter(to=self.patient1))
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.DAILY))
		weekly_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.WEEKLY))
		self.assertEqual(daily_reminder_count, 1)
		self.assertEqual(weekly_reminder_count, 0)
		
	def test_create_weekly_reminder_with_colliding_weekly_reminder(self):
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		existing_daily_reminder = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.WEEKLY,
			prescription=self.prescription1,
			day_of_week=1)
		old_reminder_count = len(Notification.objects.filter(to=self.patient1))

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		new_reminder_count = len(Notification.objects.filter(to=self.patient1))
		self.assertEqual(old_reminder_count, new_reminder_count)

		daily_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.DAILY))
		weekly_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.WEEKLY))
		self.assertEqual(daily_reminder_count, 0)
		self.assertEqual(weekly_reminder_count, 1)

	def test_create_with_refill_and_prescription_not_filled(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True, 'send_refill_reminder':True})
		self.assertEqual(response.status_code, 200)

		weekly_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.WEEKLY))
		self.assertEqual(weekly_reminder_count, 1)

		refill_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.REFILL))
		self.assertEqual(refill_reminder_count, 1)

	def test_create_with_refill_and_prescription_filled(self):
		self.prescription1.filled = True # fill the prescription
		self.prescription1.save()

		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True, 'send_refill_reminder':True})
		self.assertEqual(response.status_code, 200)

		weekly_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.WEEKLY))
		self.assertEqual(weekly_reminder_count, 1)

		refill_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.REFILL))
		self.assertEqual(refill_reminder_count, 0)

	def test_create_daily_reminder_without_colliding_reminder(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00',
			'mon':True, 'tue':True, 'wed':True,
			'thu':True, 'fri':True, 'sat':True, 'sun':True})
		self.assertEqual(response.status_code, 200)

		daily_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.DAILY))
		self.assertEqual(daily_reminder_count, 1)

		refill_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.REFILL))
		self.assertEqual(refill_reminder_count, 0)

	def test_create_weekly_reminder_without_colliding_reminder(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		weekly_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, repeat=Notification.WEEKLY))
		self.assertEqual(weekly_reminder_count, 1)

		refill_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.REFILL))
		self.assertEqual(refill_reminder_count, 0)

	def test_create_reminder_without_refill_reminder(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient1.id), 'drug_name':'drug3', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 200)

		refill_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.REFILL))
		self.assertEqual(refill_reminder_count, 0)

		# if reminder created w/o refill reminder, filled should be true
		self.assertTrue(Prescription.objects.get(drug__name='drug3').filled, True)

	def test_create_reminder_without_permission(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient2.id), 'drug_name':'drug1', 
			'reminder_time':'9:00', 'mon':True})
		self.assertEqual(response.status_code, 400)


# Unit tests for delete reminder
class DeleteReminderTest(TestCase):
	def setUp(self):
		client_user = PatientProfile.objects.create (
			first_name='Test', last_name='User', primary_phone_number='+10000000000')
		client_user.set_password('testpassword')
		client_user.save()
		c.login(phone_number='+10000000000', password='testpassword')

		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308')
		self.patient2 = PatientProfile.objects.create(
			first_name='Matt', last_name='Gaba', primary_phone_number='+12147094720')
		self.prescriber = client_user
		self.drug1 = Drug.objects.create(name='drug1')
		self.prescription1 = Prescription.objects.create(
			prescriber=self.prescriber, patient=self.patient1, drug=self.drug1)
		self.prescription2 = Prescription.objects.create(
			prescriber=self.prescriber, patient=self.patient2, drug=self.drug1)

		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9,0))
		send_datetime = next_weekday(send_datetime, 0)
		self.refill_reminder = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.REFILL,
			send_time = send_datetime, 
			repeat=Notification.WEEKLY,
			prescription=self.prescription1)
		self.med_reminder1 = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.WEEKLY,
			prescription=self.prescription1,
			day_of_week=1)
		send_datetime = next_weekday(send_datetime, 1)
		self.med_reminder2 = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.WEEKLY,
			prescription=self.prescription1,
			day_of_week=2)
		send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(10,0))
		send_datetime = next_weekday(send_datetime, 1)
		self.med_reminder3 = Notification.objects.create(
			to=self.patient1, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.DAILY,
			prescription=self.prescription1,
			day_of_week=8)

		self.med_reminder4 = Notification.objects.create(
			to=self.patient2, 
			reminder_type=Notification.MEDICATION,
			send_time = send_datetime, 
			repeat=Notification.DAILY,
			prescription=self.prescription2,
			day_of_week=8)

		assign_perm('manage_patient_profile', client_user, self.patient1)

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
			{'p_id':str(self.patient1.id + 10), 'drug_name':'drug1', 
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

		remaining_med_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, prescription__drug__name='drug1'))
		self.assertEqual(remaining_med_reminder_count, 1)

		remaining_refill_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.REFILL, prescription__drug__name='drug1'))
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

		remaining_med_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.MEDICATION, prescription__drug__name='drug1'))
		self.assertEqual(remaining_med_reminder_count, 0)

		remaining_refill_reminder_count = len(Notification.objects.filter(
			to=self.patient1,
			reminder_type=Notification.REFILL, prescription__drug__name='drug1'))
		self.assertEqual(remaining_refill_reminder_count, 0)

	def test_delete_reminder_without_permission(self):
		response = c.post('/fishfood/reminders/new/', 
			{'p_id':str(self.patient2.id), 'drug_name':'drug1', 
			'reminder_time':'10:00', 'mon':True})
		self.assertEqual(response.status_code, 400)


class CreateSafetyNetContactTest(TestCase):
	def setUp(self):
		client_user = PatientProfile.objects.create(
			first_name='Test', last_name='User', primary_phone_number='+10000000000',
			num_caregivers=1)
		client_user.set_password('testpassword')
		client_user.save()
		c.login(phone_number='+10000000000', password='testpassword')

		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308',
			num_caregivers=1)
		self.patient2 = PatientProfile.objects.create(
			first_name='Matt', last_name='Gaba', primary_phone_number='+12147094720',
			num_caregivers=1)
		self.patient1.add_safety_net_contact(
			target_patient=self.patient2, relationship='friend')

		assign_perm('manage_patient_profile', client_user, self.patient1)

	def test_invalid_request(self):
		# no patient id
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':'', 'full_name':'Matt Gaba', 'relationship':'friend', 
			'primary_phone_number':'+12147094720'})
		self.assertEqual(response.status_code, 400)

		# no full name
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':'100', 'full_name':'', 'relationship':'friend', 
			'primary_phone_number':'+12147094720'})
		self.assertEqual(response.status_code, 400)

		# no relationship
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':'100', 'full_name':'Matt Gaba', 'relationship':'', 
			'primary_phone_number':'+12147094720'})
		self.assertEqual(response.status_code, 400)

		# no primary phone number
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':'100', 'full_name':'Matt Gaba', 'relationship':'friend', 
			'primary_phone_number':''})
		self.assertEqual(response.status_code, 400)

	def test_create_nonexistent_safety_net_contact(self):
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':self.patient1.id, 'full_name':'Matt Gaba', 'relationship':'friend', 
			'primary_phone_number':'5555555555'})
		self.assertEqual(response.status_code, 200)
		q = PatientProfile.objects.filter(primary_phone_number='+15555555555')
		self.assertTrue(q.exists())
		self.assertEqual(q[0].num_caregivers, 0)

	def test_create_existing_safety_net_contact(self):
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':self.patient1.id, 'full_name':'Matt Gaba', 'relationship':'friend', 
			'primary_phone_number':'2147094720'})
		self.assertEqual(response.status_code, 200)

		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':self.patient1.id, 'full_name':'Matthew Gaba', 'relationship':'friend', 
			'primary_phone_number':'2147094720'})
		self.assertEqual(response.status_code, 200)
		self.assertTrue(
			not PatientProfile.objects.filter(full_name='Matthew Gaba').exists())

	def test_create_safety_net_contact(self):
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':self.patient1.id, 'full_name':'Test User', 'relationship':'friend', 
			'primary_phone_number':'0000000000'})
		self.assertEqual(response.status_code, 200)

		target_patient = PatientProfile.objects.get(full_name='Test User')

		self.assertTrue(target_patient.has_perm('view_patient_profile', self.patient1))
		self.assertTrue(target_patient.has_perm('manage_patient_profile', self.patient1))

	def test_create_safety_net_contact_without_permission(self):
		response = c.post('/fishfood/patients/create_safety_net_contact/', 
			{'p_id':self.patient2, 'full_name':'Test User', 'relationship':'friend', 
			'primary_phone_number':'0000000000'})
		self.assertEqual(response.status_code, 400)


class DeleteSafetyNetContactTest(TestCase):
	def setUp(self):
		client_user = PatientProfile.objects.create(
			first_name='Test', last_name='User', primary_phone_number='+10000000000',
			num_caregivers=1)
		client_user.set_password('testpassword')
		client_user.save()
		c.login(phone_number='+10000000000', password='testpassword')
		self.client_user = client_user

		self.patient1 = PatientProfile.objects.create(
			first_name='Minqi', last_name='Jiang', primary_phone_number='+18569067308',
			num_caregivers=1)
		self.patient2 = PatientProfile.objects.create(
			first_name='Matt', last_name='Gaba', primary_phone_number='+12147094720',
			num_caregivers=1)
		self.patient1.add_safety_net_contact(
			target_patient=self.patient2, relationship='friend')
		self.patient2.add_safety_net_contact(
			target_patient=self.patient1, relationship='friend')

		assign_perm('manage_patient_profile', client_user, self.patient1)

	def test_invalid_request(self):
		# no patient id
		response = c.post('/fishfood/patients/delete_safety_net_contact/',
			{'p_id':'', 'target_p_id':self.patient2.id})
		self.assertEqual(response.status_code, 400)

		# no target patient id
		response = c.post('/fishfood/patients/delete_safety_net_contact/',
			{'p_id':self.patient1.id, 'target_p_id':''})
		self.assertEqual(response.status_code, 400)

	def test_delete_nonexistent_safety_net_contact(self):
		response = c.post('/fishfood/patients/delete_safety_net_contact/',
			{'p_id':self.patient1.id, 'target_p_id':self.patient2.id + 100})
		self.assertEqual(response.status_code, 400)	

	def test_delete_safety_net_contact_without_permission(self):
		response = c.post('/fishfood/patients/delete_safety_net_contact/',
			{'p_id':self.patient2.id, 'target_p_id':self.patient1.id})
		self.assertEqual(response.status_code, 400)	

	def test_delete_existing_safety_net_contact(self):
		response = c.post('/fishfood/patients/delete_safety_net_contact/',
			{'p_id':self.patient1.id, 'target_p_id':self.patient2.id})
		self.assertEqual(response.status_code, 200)

		q = SafetyNetRelationship.objects.filter(
			source_patient=self.patient1, target_patient=self.patient2)
		self.assertTrue(not q.exists())

		self.assertTrue(not self.patient2.has_perm('view_patient_profile', self.patient1))
		self.assertTrue(not self.patient2.has_perm('manage_patient_profile', self.patient1))


