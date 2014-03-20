import datetime
from common.models import Drug
from django.test import TestCase
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import Prescription, MedicationMessage, Message, MedicationNotification, Notification

__author__ = 'matthewgaba'

class MessageTest(TestCase):
	def test_1(self):
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
		self.drug1 = Drug.objects.create(name='advil')
		self.prescription1 = Prescription.objects.create(prescriber=self.bob,
		                                                 patient=self.minqi, drug=self.drug1, filled=True)
		self.prescription2 = Prescription.objects.create(prescriber=self.bob,
		                                                 patient=self.minqi, drug=self.drug1)
		send_datetime = datetime.datetime.now()
		notification1 = MedicationNotification.objects.create(to=self.minqi, repeat=Notification.DAILY, send_time=send_datetime, prescription=self.prescription1)

		m = MedicationMessage.objects.create(to=self.minqi)
		m.notifications.add(notification1)
		m.save()
		message = Message.objects.get(id=1)
		print message.prepare_to_send()


