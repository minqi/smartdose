import os, datetime, random, csv

from configs.dev.settings import PROJECT_ROOT
from common.utilities import convert_to_e164
from common.models import Drug
from reminders.models import Prescription, Notification
from doctors.models import DoctorProfile
from patients.models import PatientProfile

from faker import Factory


DEFAULT_NUM = 10 # default amount of data to generate in fake data generators

# FAKE DATA GENERATORS ================================================
def get_fake_datasources_path(dirname="fake_datasources"):
	dirname = "fake_datasources"
	fake_datasources_path = os.path.join(PROJECT_ROOT, dirname)
	if not os.path.exists(fake_datasources_path):
		os.makedirs(fake_datasources_path)

	return fake_datasources_path

def make_fake_csv_patient_data(num=DEFAULT_NUM, filename="fake_patient_data.csv"):
	"""
	Generates fake patient and prescription data in csv format.
	Outputs fake data to fake_patient_data.csv
	"""
	# get path to fake_datasources directory in project root
	fake_datasources_path = get_fake_datasources_path()

	# open file for writing
	f_out_path = os.path.join(fake_datasources_path, filename)
	f_out = open(f_out_path, 'wb')

	# generate fake data
	fake_fields = {}
	headers = ["patient_first_name", 
			   "patient_last_name", 
			   "patient_primary_phone_number",
			   "patient_birthday",
			   "patient_address_line1", 
			   "patient_postal_code", 
			   "patient_city", 
			   "patient_state_province",
			   "patient_country_iso_code",
			   "doctor_first_name", 
			   "doctor_last_name", 
			   "doctor_primary_phone_number",
			   "doctor_email",
			   "doctor_birthday",
			   "drug_name",
			   "with_food",
			   "with_water",
			   "repeat",
			   "send_time"]

	csv_writer = csv.DictWriter(f_out, headers, extrasaction='ignore')
	csv_writer.writeheader()

	fake = Factory.create()
	for i in range(num):
		fake_fields["patient_first_name"] = fake.first_name()
		fake_fields["patient_last_name"] = fake.last_name()
		fake_fields["patient_primary_phone_number"] = str(random.randint(1e9, 1e10 - 1))
		fake_fields["patient_birthday"] = fake.date()
		fake_fields["patient_address_line1"] = fake.street_address()
		fake_fields["patient_postal_code"] = fake.postcode()
		fake_fields["patient_city"] = fake.city()
		fake_fields["patient_state_province"] = fake.state()
		fake_fields["patient_country_iso_code"] = random.randint(10,99)
		fake_fields["doctor_first_name"] = fake.first_name()
		fake_fields["doctor_last_name"] = fake.last_name()
		fake_fields["doctor_primary_phone_number"] = str(random.randint(1e9, 1e10 - 1))
		fake_fields['doctor_email'] = fake.email()
		fake_fields["doctor_birthday"] = fake.date()
		fake_fields["drug_name"] = fake.domain_word()

		# TODO(minqi): replace with actual sigs/sig codes + write a parser
		fake_fields["with_food"] = (random.randint(0,1) == 0) and True or False
		fake_fields["with_water"] = (random.randint(0,1) == 0) and True or False
		fake_fields["repeat"] = Notification.DAILY
		fake_fields["send_time"] = \
			datetime.datetime.now() + datetime.timedelta(minutes=random.randint(0,59), 
				hours=random.randint(0,24))

		# write out as csv to fake_patient_data.csv
		csv_writer.writerow(fake_fields)

	f_out.close()
	return f_out_path

def make_fake_ncpdp_patient_data(num=DEFAULT_NUM):
	"""
	Generates fake patient and prescription data in NCPDP XML format.
	Outputs fake data to fake_patient_data_ncpdp.xml
	"""
	pass


# FAKE DATA LOADERS ================================================
def load_fake_csv_patient_data(filename="fake_patient_data.csv"):
	"""
	Populates models with fake patient and prescription data 
	from fake_patient_data.csv
	"""
	fake_datasources_path = get_fake_datasources_path()
	f_in_path = os.path.join(fake_datasources_path, filename)
	if not os.path.exists(f_in_path):
		make_fake_csv_patient_data(filename=filename)

	f_in = open(f_in_path, 'rb')
	csv_reader = csv.DictReader(f_in)

	for row in csv_reader:
		patient = \
			PatientProfile.objects.get_or_create(
				first_name=row['patient_first_name'],
				last_name=row['patient_last_name'],
				primary_phone_number=row['patient_primary_phone_number'],
				birthday=row['patient_birthday'],
				address_line1=row['patient_address_line1'],
				postal_code=row['patient_postal_code'],
				city=row['patient_city'],
				state_province=row['patient_state_province'],
				country_iso_code=row['patient_country_iso_code'])[0]
		doctor = DoctorProfile.objects.get_or_create(
				first_name=row['doctor_first_name'],
				last_name=row['doctor_last_name'],
				primary_phone_number=row['doctor_primary_phone_number'],
				email=row['doctor_email'],
				birthday=row['doctor_birthday'])[0]
		drug = Drug.objects.get_or_create(name=row['drug_name'])[0]
		prescription = Prescription.objects.get_or_create(
				prescriber=doctor,
				patient=patient,
				drug=drug,
				with_food=row['with_food'],
				with_water=row['with_water'])[0]
		# add reminder time scheduling
	f_in.close()

def load_fake_ncpdp_patient_data(filename):
	"""
	Populates models with fake patient and prescription data 
	from fake_patient_data_ncpdp.xml
	"""
	pass

def load_clarity_patient_data():
	"""
	Populate models from clarity report data sources
	"""
	pass

# master patient data-loader
def load_patient_data(source='fake_csv'):
	load_function_name = 'load_' + source + '_patient_data'
	try:
		load_function = globals()[load_function_name]()
	except KeyError:
		return
