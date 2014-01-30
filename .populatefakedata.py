from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import Prescription
from reminders.models import ReminderTime
from reminders.tasks import sendOneReminder
from common.models import Drug
from common.models import Country
from datetime import datetime, date, time

# Create a doctor named Bob

bob = DoctorProfile.objects.get(primary_phone_number="2029163381")

# Create a vitamin
vitamin = Drug.objects.create(name="vitamin")
# Create meditation
meditation = Drug.objects.create(name="meditation")
# Create a lucid dream check
lucid_dream = Drug.objects.create(name="lucid dream check")



# Create a patient Matt who takes a vitamin once a day in the afternoon and meditation twice a day. He also gets two lucid dream reminders.

matt = PatientProfile.objects.create(primary_phone_number="2147094720")
minqi = PatientProfile.objects.create(primary_phone_number="8569067308")

matt_prescription1 = Prescription.objects.create(prescriber=bob, patient=matt, drug=meditation,
												 note="To make you stable", safety_net_on=True)
matt_prescription2 = Prescription.objects.create(prescriber=bob, patient=matt, drug=vitamin,
												 note="To make you healthy", safety_net_on=True)
matt_prescription3 = Prescription.objects.create(prescriber=bob, patient=matt, drug=lucid_dream,
												 note="To make you lucid dream", safety_net_on=True)

minqi_prescription3 = Prescription.objects.create(prescriber=bob, patient=minqi, drug=lucid_dream,
												 note="To make you lucid dream", safety_net_on=True)

matt_reminder3 = ReminderTime.objects.create(prescription=matt_prescription3, repeat=ReminderTime.DAILY, send_time=time(hour=17, minute=15))
minqi_reminder3 = ReminderTime.objects.create(prescription=minqi_prescription3, repeat=ReminderTime.DAILY, send_time=time(hour=23, minute=59))





