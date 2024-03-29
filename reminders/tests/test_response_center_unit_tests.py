import datetime, mock

from django.http import HttpResponseNotFound
from django.test import TestCase

from common.models import Drug, DrugFact
from common.utilities import list_to_queryset
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from reminders.models import Message, Prescription, Notification, Feedback
from reminders.response_center import ResponseCenter

from freezegun import freeze_time


class ResponseCenterTest(TestCase):
	def setUp(self):
		self.rc = ResponseCenter()
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                           primary_phone_number="8569067308",
		                                           birthday=datetime.date(year=1990, month=4, day=21),
		                                           gender=PatientProfile.MALE,
		                                           address_line1="4266 Cesar Chavez",
		                                           postal_code="94131",
		                                           city="San Francisco", state_province="CA", country_iso_code="US")
		self.doctor = DoctorProfile.objects.create(first_name="Bob", last_name="Wachter",
		                                           primary_phone_number="2029163381", birthday=datetime.date(1960, 1, 1))
		self.drug = Drug.objects.create(name='advil')
		self.prescription = Prescription.objects.create(prescriber=self.doctor,
		                                                 patient=self.minqi, drug=self.drug, filled=True)
		self.notification = Notification.objects.create(to=self.minqi, _type=Notification.MEDICATION,
		                                                prescription=self.prescription, repeat=Notification.DAILY,
		                                                send_datetime=datetime.datetime.now())
		self.refill_notification = Notification.objects.create(to=self.minqi, _type=Notification.REFILL,
		                                                prescription=self.prescription, repeat=Notification.DAILY,
		                                                send_datetime=datetime.datetime.now())

	def test_process_medication_response_yes(self):
		message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, False)
		self.assertIsNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)
		response = self.rc.process_medication_response(self.minqi, message, 'y')
		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, True)
		self.assertIsNotNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)

	def test_process_medication_response_no(self):
		message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, False)
		self.assertIsNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)
		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertFalse(Message.objects.filter(_type=Message.MEDICATION_QUESTIONNAIRE))
		response = self.rc.process_medication_response(self.minqi, message, 'n')
		expected_response = "Why not? Reply:\n" \
		                    "A - Haven't gotten the chance\n" \
		                    "B - Need to refill\n" \
		                    "C - Side effects\n" \
		                    "D - Meds don't work\n" \
		                    "E - Prescription changed\n" \
		                    "F - I feel sad :(\n" \
		                    "G - Other"
		self.assertEqual(response.content, expected_response)
		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, False)
		self.assertTrue(Message.objects.filter(_type=Message.MEDICATION_QUESTIONNAIRE))
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertIsNotNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)

	def test_process_medication_questionnaire_response_a(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertFalse(Notification.objects.filter(_type=Notification.REPEAT_MESSAGE))
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'a')
		expected_response = "No problem. We'll send you another reminder in an hour."
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertTrue(Notification.objects.filter(_type=Notification.REPEAT_MESSAGE))

	def test_process_medication_questionnaire_response_b(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'b')
		expected_response = "Taking your medicine is an important step in getting better. Please refill your meds at your earliest convenience."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_questionnaire_response_c(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'c')
		expected_response = "We'll let your doctor know you've been having trouble with side effects."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_questionnaire_response_d(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'd')
		expected_response = "Please let your doctor know that you don't think your meds are having the correct effects."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_questionnaire_response_e(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'e')
		expected_response = "We'll let your doctor know about your change in prescription."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_questionnaire_response_f(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'f')
		expected_response = "Confucious says, taking your meds is one small step to happiness. :)"
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_questionnaire_response_unknown_response(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'booga booga')
		expected_response = "We didn't understand that reply. Reply with a letter matching the options above."
		self.assertEqual(response.content, expected_response)
		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_response_yes(self):
		message = Message.objects.create(to=self.minqi, _type=Notification.REFILL)
		feedback = Feedback.objects.create(_type=Feedback.REFILL, notification=self.refill_notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.refill_notification)
		message.feedbacks.add(feedback)
		message.save()

		freezer = freeze_time(datetime.datetime.combine(datetime.datetime.today(), datetime.time(hour=9)))
		freezer.start()
		self.notification.send_datetime = datetime.datetime.combine(datetime.datetime.today() + datetime.timedelta(days=1), datetime.time(hour=8))
		self.notification.save()
		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, False)
		self.assertIsNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)
		response = self.rc.process_refill_response(self.minqi, message, 'y')
		expected_response = "Great! To support your new routine, you'll receive a simple med reminder daily at 8:00am. To adjust the time, visit www.smartdo.se/time?c=12345."
		self.assertEqual(response.content, expected_response)
		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, True)
		self.assertIsNotNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)

		self.notification.send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(hour=7))
		self.notification.save()
		response = self.rc.process_refill_response(self.minqi, message, 'y')
		expected_response = "Great! To support your new routine, you'll receive a simple med reminder daily at 7:00am. To adjust the time, visit www.smartdo.se/time?c=12345."
		self.assertEqual(response.content, expected_response)

		self.notification.send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(hour=14, minute=30))
		self.notification.save()
		response = self.rc.process_refill_response(self.minqi, message, 'y')
		expected_response = "Great! To support your new routine, you'll receive a simple med reminder daily at 2:30pm. To adjust the time, visit www.smartdo.se/time?c=12345."
		self.assertEqual(response.content, expected_response)

		self.notification.send_datetime = datetime.datetime.combine(datetime.datetime.today()-datetime.timedelta(days=3), datetime.time(hour=0, minute=30))
		self.notification.save()
		response = self.rc.process_refill_response(self.minqi, message, 'y')
		expected_response = "Great! To support your new routine, you'll receive a simple med reminder daily at 12:30am. To adjust the time, visit www.smartdo.se/time?c=12345."
		self.assertEqual(response.content, expected_response)
		freezer.stop()


	def test_process_refill_questionnaire_response_a(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.REFILL)
		feedback = Feedback.objects.create(_type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.REFILL_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_refill_questionnaire_response(self.minqi, message, 'a')
		expected_response = "We'll send you another reminder tomorrow. Try to pick up your meds today so you can begin your treatment as soon as possible."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_refill_questionnaire_response_b(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.REFILL)
		f = Feedback.objects.create(_type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(f)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.REFILL_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_refill_questionnaire_response(self.minqi, message, 'b')
		expected_response = "Medicine only works if you can afford to take it. Please let your doctor know so you can find the best treatment."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_refill_questionnaire_response_c(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.REFILL)
		feedback = Feedback.objects.create(_type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.REFILL_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_refill_questionnaire_response(self.minqi, message, 'c')
		expected_response = "Please contact your doctor immediately if you are experiencing any side-effects that bother you or do not go away."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_refill_questionnaire_response_d(self):
		preceding_message = Message.objects.create(to=self.minqi, _type=Notification.REFILL)
		feedback = Feedback.objects.create(_type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, _type=Message.REFILL_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_refill_questionnaire_response(self.minqi, message, 'd')
		expected_response = "Please tell us more."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_get_app_upsell_content_with_doctor_prescriber(self):
		message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		content = self.rc._get_app_upsell_content(self.minqi, message)
		dummy_response = "Dr. Wachter will be happy you're taking care of your health.\n\n"
		expected_response1 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+\
							 "You can add or remove safety net members at smartdo.se/1234567890?c=12345."

		expected_response2 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+\
							 "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345?"

		expected_response3 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345?"

		expected_response4 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345?"

		expected_responses = [dummy_response, expected_response1, expected_response2, expected_response3, expected_response4]
		self.assertIn(content, expected_responses)

	def test_get_app_upsell_content_with_self_prescriber(self):
		self_prescription = Prescription.objects.create(prescriber=self.minqi,
		                                                patient=self.minqi, drug=self.drug, filled=True)
		self_prescription_notification = Notification.objects.create(to=self.minqi, _type=Notification.MEDICATION,
		                                                prescription=self.prescription, repeat=Notification.DAILY,
		                                                send_datetime=datetime.datetime.now())
		message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self_prescription)
		message.notifications.add(self_prescription_notification)
		message.feedbacks.add(feedback)
		message.save()

		content = self.rc._get_app_upsell_content(self.minqi, message)
		dummy_response = "Your family will be happy you're taking care of your health.\n\n"

		expected_response1 = "Your family will be happy you're taking care of your health.\n\n"+ \
		                     "You can add or remove safety net members at smartdo.se/1234567890?c=12345."

		expected_response2 = "Your family will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345?"

		expected_response3 = "Your family will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345?"

		expected_response4 = "Your family will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345?"

		expected_responses = [dummy_response, expected_response1, expected_response2, expected_response3, expected_response4]
		self.assertIn(content, expected_responses)

	def test_get_app_upsell_content_with_safety_net(self):
		message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		self.minqis_safety_net = PatientProfile.objects.create(
			first_name='Jianna', last_name='Jiang', primary_phone_number='1234567890')
		self.minqi.add_safety_net_contact(
			target_patient=self.minqis_safety_net, relationship='mother')

		content = self.rc._get_app_upsell_content(self.minqi, message)
		dummy_response = "Dr. Wachter will be happy you're taking care of your health.\n\n"

		expected_response1 = "Dr. Wachter will be happy you're taking care of your health.\n\n" + \
		                     "You can add or remove safety net members at smartdo.se/1234567890?c=12345."

		expected_response2 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345?"

		expected_response3 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345?"

		expected_response4 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345?"

		expected_response5 = "Jianna will be happy you're taking care of your health.\n\n"+ \
		                     "You can add or remove safety net members at smartdo.se/1234567890?c=12345."

		expected_response6 = "Jianna will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345?"

		expected_response7 = "Jianna will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345?"

		expected_response8 = "Jianna will be happy you're taking care of your health.\n\n"
		                     # "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345?"
		expected_responses = [dummy_response, expected_response1, expected_response2, expected_response3, expected_response4,
		                      expected_response5, expected_response6, expected_response7, expected_response8]
		self.assertIn(content, expected_responses)

	def test_get_health_educational_content(self):
		message = Message.objects.create(to=self.minqi, _type=Notification.MEDICATION)
		feedback = Feedback.objects.create(_type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		# Test when there are no facts (same behavior as get_app_upsell_content)
		dummy_response = "Dr. Wachter will be happy you're taking care of your health.\n\n"
		
		expected_response1 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "You can add or remove safety net members at smartdo.se/1234567890?c=12345."

		expected_response2 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345?"

		expected_response3 = "Dr. Wachter will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345?"

		expected_response4 = "Dr. Wachter will be happy you're taking care of your health.\n\n"
		                     # "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345?"
		expected_responses = [dummy_response, expected_response1, expected_response2, expected_response3, expected_response4]
		content = self.rc._get_health_educational_content(self.minqi, message)
		self.assertIn(content, expected_responses)

		# Now test after we've added facts
		fact1 = "That vitamin you're taking helps protect your immune system from deficiencies."
		fact2 = "That vitamin you're taking gives you more energy."
		DrugFact.objects.create(drug=self.prescription.drug, fact=fact1)
		DrugFact.objects.create(drug=self.prescription.drug, fact=fact2)

		content = self.rc._get_health_educational_content(self.minqi, message)
		facts = [fact1, fact2]
		self.assertIn(content, facts)

	def test_pause(self):
		message = 'q'
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		self.assertEqual(self.minqi.quit_request_datetime, None)
		response = self.rc.process_response(self.minqi, message)
		self.assertEqual('You have quit Smartdose and will stop receiving reminders. Reply "r" or "resume" at any time to start receiving reminders again.', response.content)
		self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	# def test_quit_initial_quit(self):
	# 	message = 'q'
	# 	self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
	# 	self.assertEqual(self.minqi.quit_request_datetime, None)
	# 	response = self.rc.process_response(self.minqi, message)
	# 	self.assertEqual("Are you sure you'd like to quit? Reply 'quit' to quit using Smartdose.", response.content)
	# 	self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
	# 	self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	# def test_quit_confirm_quit(self):
	# 	message = 'q'
	# 	self.minqi.quit_request_datetime = datetime.datetime.now()
	# 	self.minqi.save()
	# 	self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
	# 	self.assertNotEqual(self.minqi.quit_request_datetime, None)
	# 	response = self.rc.process_response(self.minqi, message)
	# 	self.assertEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
	# 	self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	# def test_quit_long_after_initial_quit(self):
	# 	message = 'q'
	# 	self.minqi.quit_request_datetime = datetime.datetime.now() - datetime.timedelta(hours=2)
	# 	self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
	# 	response = self.rc.process_response(self.minqi, message)
	# 	self.assertEqual("Are you sure you'd like to quit? Reply 'quit' to quit using Smartdose.", response.content)
	# 	self.assertNotEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
	# 	self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
	# 	self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_resume_for_quit_patient(self):
		message = 'resume'
		self.minqi.status = PatientProfile.QUIT
		self.minqi.save()
		response = self.rc.process_response(self.minqi, message)
		self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.ACTIVE)
		self.assertEqual("Welcome back to Smartdose.", response.content)

	def test_resume_for_not_quit_patient(self):
		message = 'resume'
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		response = self.rc.process_response(self.minqi, message)
		expected_response = "We didn't understand that response.\n\n"+\
							"To change the delivery time of your previous reminder, reply with a time (e.g., 9am).\n\n"+\
							"For info about your meds, reply m."
		self.assertEqual(response.content, expected_response)

	def test_is_time_change(self):
		message = '9am'
		expected_time = datetime.time(hour=9)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '10am'
		expected_time = datetime.time(hour=10)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '10:27am'
		expected_time = datetime.time(hour=10, minute=27)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '1027am'
		expected_time = datetime.time(hour=10, minute=27)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '10'
		expected_time = datetime.time(hour=10)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '109am'
		expected_time = datetime.time(hour=1, minute=9)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '1pm'
		expected_time = datetime.time(hour=13)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '12pm'
		expected_time = datetime.time(hour=12)
		self.assertEqual(self.rc.is_time_change(message), expected_time)
		message = '13pm'
		self.assertFalse(self.rc.is_time_change(message))
		message = 'hello'
		self.assertFalse(self.rc.is_time_change(message))
		message = '31'
		self.assertFalse(self.rc.is_time_change(message))
		message = '10:2am'
		self.assertFalse(self.rc.is_time_change(message))
