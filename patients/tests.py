from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from common.utilities import InterpersonalRelationship
from patients.models import PatientProfile


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
		self.assertEqual(minqi.safety_net_contacts.all().count(), 0)
		# Add Matthew to Minqi's safety net
		safety_net_contact = PatientProfile.objects.create(
			primary_phone_number='2147094720', first_name='Matthew', last_name='Gaba')
		minqi.add_safety_net_contact(target_patient=safety_net_contact, relationship="friend")
		matt = PatientProfile.objects.get(primary_phone_number="+12147094720")
		minqi = PatientProfile.objects.get(id=minqi.id)
		self.assertEqual(minqi.safety_net_contacts.all().count(), 1)
		self.assertEqual(minqi.safety_net_contacts.all()[0], matt)
		self.assertEqual(matt.source_patient_safety_nets.all()[0].source_patient, minqi)


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
		self.assertEqual(InterpersonalRelationship.lookup_backwards_relationship(
			InterpersonalRelationship.MOTHER, self.male_patient), InterpersonalRelationship.SON)
		self.assertEqual(InterpersonalRelationship.lookup_backwards_relationship(
			InterpersonalRelationship.SON, self.male_patient), InterpersonalRelationship.FATHER)

	def test_female_backwards_relationship(self):
		self.assertEqual(
			InterpersonalRelationship.lookup_backwards_relationship(
				InterpersonalRelationship.MOTHER, self.female_patient), InterpersonalRelationship.DAUGHTER)
		self.assertEqual(InterpersonalRelationship.lookup_backwards_relationship(
			InterpersonalRelationship.SON, self.female_patient), InterpersonalRelationship.MOTHER)

	def test_gender_neutral_backwards_relationship(self):
		self.assertEqual(InterpersonalRelationship.lookup_backwards_relationship(
			InterpersonalRelationship.MOTHER, self.gender_neutral_patient), InterpersonalRelationship.CHILD)
		self.assertEqual(InterpersonalRelationship.lookup_backwards_relationship(
			InterpersonalRelationship.SON, self.gender_neutral_patient), InterpersonalRelationship.PARENT)
