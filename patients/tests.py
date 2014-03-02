"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase
from patients.models import PatientProfile, PatientUtilities
from datetime import date

class PatientTest(TestCase):
	def test_add_safety_net(self):
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
								 				  primary_phone_number="8569067308", 
								 				  username="8569067308",
								 				  birthday=date(year=1990, month=4, day=21),
								 				  gender=PatientProfile.MALE,
								 				  address_line1="4266 Cesar Chavez",
											 	  postal_code="94131", 
											 	  city="San Francisco", state_province="CA", country_iso_code="US")
		# Verify Minqi does not have a safety net member
		self.assertEqual(minqi.has_safety_net, False)
		self.assertEqual(minqi.safety_net_members.all().count(), 0)
		# Add Matthew to Minqi's safety net
		minqi.add_safety_net_member(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba",
								 birthday=date(year=1989, month=10, day=13), 
								 patient_relationship="friend")
		matt = PatientProfile.objects.get(primary_phone_number="+12147094720")
		minqi = PatientProfile.objects.get(id=minqi.id)
		self.assertEqual(minqi.has_safety_net, True)
		self.assertEqual(minqi.safety_net_members.all().count(), 1)
		self.assertEqual(minqi.safety_net_members.all()[0], matt)
		self.assertEqual(matt.source_patient_safety_nets.all()[0].source_patient, minqi)

class PrimaryContactTest(TestCase):
	# TEST 1: Test that a patient without a phone number and with a primary contact gets created
	def test_create_primary_contact_patient(self):
		with self.assertRaises(ValidationError):
			minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
												  birthday=date(year=1990, month=4, day=21),
												  gender=PatientProfile.MALE,
												  address_line1="4266 Cesar Chavez",
												  postal_code="94131",
												  city="San Francisco", state_province="CA", country_iso_code="US")

			minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
			                                      birthday=date(year=1990, month=4, day=21),
			                                      gender=PatientProfile.MALE,
			                                      address_line1="4266 Cesar Chavez",
			                                      postal_code="94131",
			                                      city="San Francisco", state_province="CA", country_iso_code="US",
			                                      has_primary_contact=True)

	# TEST 2: Test the add_primary_contact function adds a primary contact
	def test_add_primary_contact(self):
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                      birthday=date(year=1990, month=4, day=21),
		                                      gender=PatientProfile.MALE,
		                                      address_line1="4266 Cesar Chavez",
		                                      postal_code="94131",
		                                      city="San Francisco", state_province="CA", country_iso_code="US",
		                                      has_primary_contact=True)
		minqi.add_primary_contact_member(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba",
		                            birthday=date(year=1989, month=10, day=13),
		                            patient_relationship="friend")
		matt = PatientProfile.objects.get(primary_phone_number="+12147094720")
		minqi = PatientProfile.objects.get(id=minqi.id)
		self.assertEqual(minqi.has_primary_contact, True)
		self.assertEqual(minqi.primary_contact_members.all().count(), 1)
		self.assertEqual(minqi.primary_contact_members.all()[0], matt)
		self.assertEqual(matt.source_patient_primary_contacts.all()[0].source_patient, minqi)

class LookupBackwardsRelationshipTest(TestCase):
	def setUp(self):
		self.male_patient = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                      primary_phone_number="+12147984729",
		                                      birthday=date(year=1990, month=4, day=21),
		                                      gender=PatientProfile.MALE,
		                                      address_line1="4266 Cesar Chavez",
		                                      postal_code="94131",
		                                      city="San Francisco", state_province="CA", country_iso_code="US")
		self.female_patient = PatientProfile.objects.create(first_name="Minqina", last_name="Jiang",
														  primary_phone_number="+12147984720",
		                                                  birthday=date(year=1990, month=4, day=21),
		                                                  gender=PatientProfile.FEMALE,
		                                                  address_line1="4266 Cesar Chavez",
		                                                  postal_code="94131",
		                                                  city="San Francisco", state_province="CA", country_iso_code="US")
		self.gender_neutral_patient = PatientProfile.objects.create(first_name="Minq", last_name="Jiang",
		                                                    primary_phone_number="+12147984721",
		                                                    birthday=date(year=1990, month=4, day=21),
		                                                    gender=PatientProfile.UNKNOWN,
		                                                    address_line1="4266 Cesar Chavez",
		                                                    postal_code="94131",
		                                                    city="San Francisco", state_province="CA", country_iso_code="US")

	def test_male_backwards_relationship(self):
		self.assertEqual(PatientUtilities.lookup_backwards_relationship(PatientUtilities.MOTHER, self.male_patient), PatientUtilities.SON)
		self.assertEqual(PatientUtilities.lookup_backwards_relationship(PatientUtilities.SON, self.male_patient), PatientUtilities.FATHER)

	def test_female_backwards_relationship(self):
		self.assertEqual(PatientUtilities.lookup_backwards_relationship(PatientUtilities.MOTHER, self.female_patient), PatientUtilities.DAUGHTER)
		self.assertEqual(PatientUtilities.lookup_backwards_relationship(PatientUtilities.SON, self.female_patient), PatientUtilities.MOTHER)

	def test_gender_neutral_backwards_relationship(self):
		self.assertEqual(PatientUtilities.lookup_backwards_relationship(PatientUtilities.MOTHER, self.gender_neutral_patient), PatientUtilities.CHILD)
		self.assertEqual(PatientUtilities.lookup_backwards_relationship(PatientUtilities.SON, self.gender_neutral_patient), PatientUtilities.PARENT)
