from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import Prescription
from reminders.models import Reminder
from common.models import Drug
from datetime import datetime, date, time

# Create a doctor named Bob
bob = DoctorProfile.objects.addDoctor("2029163381", "Bob", "Watcher", "2029163381", "4262 Cesar Chavez", "",
								   "94131", "San Francisco", "CA", "US")

# Create patient Minqi who takes a daily vitamin at 11pm o'clock

# Create a vitamin
vitamin = Drug.objects.create(name="Vitamin")

minqi = PatientProfile.objects.addPatient("8569067308", "Minqi", "Jiang", "8569067308", "4266 Cesar Chavez", "",
									 "94131", "San Francisco", "CA", "US", PatientProfile.MALE)
minqi_prescription = Prescription.objects.create(prescriber=bob, patient=minqi, drug=vitamin,
												 note="To make you strong", safety_net_on=True)

d = date.today()
t = time(23, 00)
send_time = datetime.combine(d,t)
minqi_reminder = Reminder.objects.create(prescription=minqi_prescription, repeat=Reminder.DAILY,
										 send_time=send_time, reminder_num=minqi_prescription.reminders_sent)

# Create patient Matt who takes a daily meditation at 8 o'clock

# Create meditation
meditation = Drug.objects.create(name="Meditation")

matt = PatientProfile.objects.addPatient("2147094720", "Matthew", "Gaba", "2147094720", "4266 Cesar Chavez", "",
									 "94131", "San Francisco", "CA", "US", PatientProfile.MALE)
matt_prescription = Prescription.objects.create(prescriber=bob, patient=matt, drug=meditation,
												 note="To make you stable", safety_net_on=True)

d = date.today()
t = time(8, 00)
send_time = datetime.combine(d,t)
matt_reminder = Reminder.objects.create(prescription=matt_prescription, repeat=Reminder.DAILY,
										 send_time=send_time, reminder_num=matt_prescription.reminders_sent)


