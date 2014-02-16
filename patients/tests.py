"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from patients.models import PatientProfile
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
		minqi.add_safetynet_member(primary_phone_number="2147094720", first_name="Matthew", last_name="Gaba", 
								 birthday=date(year=1989, month=10, day=13), 
								 patient_relationship="friend")

		minqi = PatientProfile.objects.get(id=minqi.id)
		self.assertEqual(minqi.has_safety_net, True)
		self.assertEqual(minqi.safety_net_members.all().count(), 1)

