from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import Prescription, ReminderTime
from common.models import Country, Drug
from datetime import datetime, date, time, timedelta
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User

def get_unique_username(obj):
	original_username = str(hash(obj.first_name+obj.last_name))
	username = original_username
	for i in range(0, 10000): #aribtrarily choose max range to be 10000 on the assumption that there will not be more than 10,000 collisions.
		try:
			User.objects.get(username=username)
			username = original_username+str(i) # If there's a collision, add another integeter and begin incrementing
		except User.DoesNotExist:
			return username
	raise UsernameCollisionError

@receiver(pre_save)
def my_callback(sender, **kwargs):
	if not issubclass(sender, User):
		return
	obj = kwargs['instance'] 
	if not obj.id:
   		username = get_unique_username(obj)
   		obj.username = username
   		print username

# Create a doctor named Bob
bob = DoctorProfile.objects.get_or_create(primary_phone_number="2029163381", first_name="Robert", last_name="Wachter", birthday="1960-1-1")[0]

# test drugs
vitamin = Drug.objects.get_or_create(name="vitamin")[0]
meditation = Drug.objects.get_or_create(name="meditation")[0]
lucid_dream = Drug.objects.get_or_create(name="lucid dream check")[0]

# # Create a patient Matt who takes a vitamin once a day in the afternoon and meditation twice a day. He also gets two lucid dream reminders.
matt = PatientProfile.objects.get_or_create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday="1989-10-13")[0]
minqi = PatientProfile.objects.get_or_create(primary_phone_number="8569067308", first_name="Minqi", last_name="Jiang", birthday="1990-8-7")[0]

matt_prescription1 = Prescription.objects.get_or_create(prescriber=bob, patient=matt, drug=vitamin,
												 note="To make you healthy", safety_net_on=True)[0]
minqi_prescription1 = Prescription.objects.get_or_create(prescriber=bob, patient=minqi, drug=vitamin,
												 note="To make you healthy", safety_net_on=True)[0]

# schedule a bunch of reminders for immediate delivery over the next ten minutes
now = datetime.now()
for i in range(10):
	ReminderTime.objects.get_or_create(prescription=matt_prescription1, repeat=ReminderTime.DAILY, send_time=now + i*timedelta(minutes=1))
	ReminderTime.objects.get_or_create(prescription=minqi_prescription1, repeat=ReminderTime.DAILY, send_time=now + i*timedelta(minutes=1))


