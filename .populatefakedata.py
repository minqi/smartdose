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

# Create a doctor and patients
bob = DoctorProfile.objects.get_or_create(primary_phone_number="2029163381", first_name="Robert", last_name="Wachter", birthday="1960-1-1")[0]
matt = PatientProfile.objects.get_or_create(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", birthday="1989-10-13")[0]
minqi = PatientProfile.objects.get_or_create(primary_phone_number="8569067308", first_name="Minqi", last_name="Jiang", birthday="1990-8-7")[0]

# schedule reminders
now = datetime.now()
for i in range(12):
	drug_name1 = 'vitamin B' + str(i)
	drug_name2 = 'vitamin C' + str(i)
	drug1 = Drug.objects.get_or_create(name=drug_name1)[0]
	drug2 = Drug.objects.get_or_create(name=drug_name2)[0]
	prescription_minqi1 = Prescription.objects.get_or_create(prescriber=bob, patient=minqi, drug=drug1, filled=True)[0]
	prescription_minqi2 = Prescription.objects.get_or_create(prescriber=bob, patient=minqi, drug=drug2, filled=True)[0]
	prescription_matt1 = Prescription.objects.get_or_create(prescriber=bob, patient=matt, drug=drug1, filled=True)[0]
	prescription_matt2 = Prescription.objects.get_or_create(prescriber=bob, patient=matt, drug=drug2, filled=True)[0]
	
	ReminderTime.objects.get_or_create(
		to=minqi, 
		prescription=prescription_minqi1, 
		repeat=ReminderTime.DAILY, 
		send_time=now + i*timedelta(hours=1),
		reminder_type=ReminderTime.MEDICATION)
	ReminderTime.objects.get_or_create(
		to=minqi, 
		prescription=prescription_minqi2, 
		repeat=ReminderTime.DAILY, 
		send_time=now + i*timedelta(hours=1),
		reminder_type=ReminderTime.MEDICATION)
	
	ReminderTime.objects.get_or_create(
		to=matt, 
		prescription=prescription_matt1, 
		repeat=ReminderTime.DAILY, 
		send_time=now + i*timedelta(hours=1),
		reminder_type=ReminderTime.MEDICATION)
	ReminderTime.objects.get_or_create(
		to=matt, 
		prescription=prescription_matt2, 
		repeat=ReminderTime.DAILY, 
		send_time=now + i*timedelta(hours=1),
		reminder_type=ReminderTime.MEDICATION)
