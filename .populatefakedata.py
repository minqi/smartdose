import random
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from common.models import Country, Drug
import datetime
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from reminders.models import Prescription, Notification, Message, Feedback

# Get all patients
# For each patient
	# Add prescriptions for the patient
	# Simulate sent messages to patient
	# Simulate responses to the messages

drugs = []
drugs.append(Drug.objects.get_or_create(name='advil'))
drugs.append(Drug.objects.get_or_create(name='lipitor'))
drugs.append(Drug.objects.get_or_create(name='beta blocker'))
drugs.append(Drug.objects.get_or_create(name='aspirin'))
drugs.append(Drug.objects.get_or_create(name='vitamin b'))
drugs.append(Drug.objects.get_or_create(name='vitamin c'))
drugs.append(Drug.objects.get_or_create(name='vitamin d'))
drugs.append(Drug.objects.get_or_create(name='clopidogrel'))
drugs.append(Drug.objects.get_or_create(name='warfarin'))
drugs.append(Drug.objects.get_or_create(name='ace inhibitor'))
drugs.append(Drug.objects.get_or_create(name='ticagrelor'))
drugs.append(Drug.objects.get_or_create(name='prasugrel'))
drugs.append(Drug.objects.get_or_create(name='abilify'))
drugs.append(Drug.objects.get_or_create(name='oleptro'))

patients = PatientProfile.objects.all()
for patient in patients:
	num_drugs = random.randint(1,3)
	for x in range(0, num_drugs):
		prescription = Prescription.objects.create(prescriber=patient,
													 patient=patient, drug=random.choice(drugs)[0])
		notification = Notification.objects.create(to=patient, _type=Notification.MEDICATION, prescription=prescription,
		                            repeat=Notification.DAILY, send_datetime=datetime.datetime.now() + datetime.timedelta(weeks=50))
		now = datetime.datetime.now()
		five_hours_ago = now - datetime.timedelta(hours=5)
		while five_hours_ago < now:
			if random.randint(0,3) > 2:
				first_message = Message.objects.create(to=patient, _type=Message.MEDICATION, datetime_responded=five_hours_ago)
				response_message = Message.objects.create(to=patient, _type=Message.MEDICATION_QUESTIONNAIRE, datetime_responded=five_hours_ago, previous_message=first_message)
				feedback_choices = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
				feedback = Feedback.objects.create(_type=Message.MEDICATION, notification=notification, prescription=prescription, datetime_responded=five_hours_ago, completed=False, note=Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY[random.choice(feedback_choices)] )
				first_message.feedbacks.add(feedback)
				response_message.feedbacks.add(feedback)
			five_hours_ago = five_hours_ago + datetime.timedelta(hours=1)

