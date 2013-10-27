from doctors.models import DoctorProfile
from patients.models import PatientProfile
from reminders.models import Prescription
from reminders.models import Reminder
from common.models import Drug
from common.models import Country
from datetime import datetime, date, time

# Create a doctor named Bob
bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",  
								   primary_phone_number="2029163381", 
								   username="2029163381",
								   address_line1="4262 Cesar Chavez", postal_code="94131", 
								   city="San Francisco", state_province="CA", country_iso_code="US")

# Create patient Minqi who takes a daily vitamin at 11pm o'clock

# Create a vitamin
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

d = date.today()
t = time(23, 00)
send_time = datetime.combine(d,t)
minqi_reminder = Reminder.objects.create(prescription=minqi_prescription, repeat=Reminder.DAILY,
										 send_time=send_time, reminder_num=minqi_prescription.reminders_sent)

# Create patient Matt who takes a daily meditation at 8 o'clock

# Create meditation
meditation = Drug.objects.create(name="Meditation")

matt = PatientProfile.objects.create(first_name="Matt", last_name="Gaba",
						 				  primary_phone_number="2147094720", 
						 				  username="2147094720",
						 				  gender=PatientProfile.MALE,
						 				  address_line1="4266 Cesar Chavez",
									 	  postal_code="94131",
									 	  city="San Francisco", state_province="CA", country_iso_code="US")
matt_prescription = Prescription.objects.create(prescriber=bob, patient=matt, drug=meditation,
												 note="To make you stable", safety_net_on=True)

d = date.today()
t = time(8, 00)
send_time = datetime.combine(d,t)
matt_reminder = Reminder.objects.create(prescription=matt_prescription, repeat=Reminder.DAILY,
										 send_time=send_time, reminder_num=matt_prescription.reminders_sent)


