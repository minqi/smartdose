import datetime
from common.models import Drug, DrugFact
from common.utilities import list_to_queryset
from django.http import HttpResponseNotFound
from django.test import TestCase
from doctors.models import DoctorProfile
from freezegun import freeze_time
import mock
from patients.models import PatientProfile
from reminders.models import Message, Prescription, Notification, Feedback
from reminders.response_center import ResponseCenter
"""
class RenderResponseFromActionTest(TestCase):
	def setUp(self):
		self.rc = ResponseCenter()
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                           primary_phone_number="8569067308",
		                                           birthday=datetime.date(year=1990, month=4, day=21),
		                                           gender=PatientProfile.MALE,
		                                           address_line1="4266 Cesar Chavez",
		                                           postal_code="94131",
		                                           city="San Francisco", state_province="CA", country_iso_code="US")

	def test_ack_valid(self):
		message_number = 1
		ack_number = message_number
		valid_message = Message(to=self.minqi, message_number=message_number, type=Message.REFILL)
		valid_message_as_list = [valid_message]
		# Create a fake Message.objects.filter method to patch into our code.
		def fake_filter(message_number, **kwargs):
			if message_number == "1":
				return valid_message_as_list
			elif message_number != None:
				return []
			else:
				raise Exception("Must specify message_number here")
		self.assertIsNone(valid_message.datetime_responded)
		with mock.patch('reminders.models.Message.objects.filter', fake_filter):
			response = self.rc.render_response_from_action(ResponseCenter.Action.ACK, self.minqi, str(ack_number))
			self.assertEqual("Your family will be happy to know that you're taking care of your health.", response.content)
			self.assertIsNotNone(valid_message.datetime_responded)

	def test_ack_valid_quotes_in_message(self):
		message_number = 1
		response_message = "\'" + str(message_number) + "\'"
		valid_message = Message(to=self.minqi, type=Message.REFILL)
		valid_message_as_list = [valid_message]
		# Create a fake Message.objects.filter method to patch into our code.
		def fake_filter(message_number, **kwargs):
			if message_number == "1":
				return valid_message_as_list
			elif message_number != None:
				return []
			else:
				raise Exception("Must specify message_number here")
		self.assertEqual(valid_message.state, Message.UNACKED)
		with mock.patch('reminders.models.Message.objects.filter', fake_filter):
			response = self.rc.render_response_from_action(ResponseCenter.Action.ACK, self.minqi, response_message)
			self.assertEqual("Your family will be happy to know that you're taking care of your health.", response.content)
			self.assertEqual(valid_message.state, Message.ACKED)

	def test_ack_invalid(self):
		message_number = 1
		ack_number = 2
		valid_message = Message(to=self.minqi, type=Message.REFILL)
		valid_message_as_list = [valid_message]
		# Create a fake Message.objects.filter method to patch into our code.
		def fake_filter(message_number, **kwargs):
			if message_number == "1":
				return valid_message_as_list
			elif message_number != None:
				return []
			else:
				raise Exception("Must specify message_number here")
		self.assertIsNone(valid_message.datetime_responded)
		with mock.patch('reminders.models.Message.objects.filter', fake_filter):
			response = self.rc.render_response_from_action(ResponseCenter.Action.ACK, self.minqi, str(ack_number))
			self.assertEqual("Whoops - there is no reminder with number 2 that needs a response.", response.content)
			self.assertIsNotNone(valid_message.datetime_responded)

	def test_not_valid(self):
		not_valid_message = "heaoij"
		not_valid_sender = None
		response = self.rc.render_response_from_action(ResponseCenter.Action.NOT_VALID_MESSAGE, not_valid_sender, not_valid_message)
		self.assertEqual(HttpResponseNotFound().status_code, response.status_code)

	def test_quit_initial_quit(self):
		message = 'q'
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		self.assertEqual(self.minqi.quit_request_datetime, None)
		response = self.rc.render_response_from_action(ResponseCenter.Action.QUIT, self.minqi, message)
		self.assertEqual("Are you sure you'd like to quit? You can adjust your settings and learn more about Smartdose at PLACEHOLDER_URL. Reply 'quit' to quit using Smartdose.", response.content)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_quit_confirm_quit(self):
		message = 'q'
		self.minqi.quit_request_datetime = datetime.datetime.now()
		self.minqi.save()
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		self.assertNotEqual(self.minqi.quit_request_datetime, None)
		response = self.rc.render_response_from_action(ResponseCenter.Action.QUIT, self.minqi, message)
		self.assertEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
		self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_quit_long_after_initial_quit(self):
		message = 'q'
		self.minqi.quit_request_datetime = datetime.datetime.now() - datetime.timedelta(hours=2)
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		response = self.rc.render_response_from_action(ResponseCenter.Action.QUIT, self.minqi, message)
		self.assertEqual("Are you sure you'd like to quit? You can adjust your settings and learn more about Smartdose at PLACEHOLDER_URL. Reply 'quit' to quit using Smartdose.", response.content)
		self.assertNotEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_resume_for_quit_patient(self):
		message = 'resume'
		self.minqi.status = PatientProfile.QUIT
		self.minqi.save()
		response = self.rc.render_response_from_action(ResponseCenter.Action.RESUME, self.minqi, message)
		self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.ACTIVE)
		self.assertEqual("Welcome back to Smartdose.", response.content)

	def test_resume_for_not_quit_patient(self):
		message = 'resume'
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		response = self.rc.render_response_from_action(ResponseCenter.Action.RESUME, self.minqi, message)
		self.assertEqual("We did not understand your message. For more information on how to use Smartdose you can visit PLACEHOLDER_URL.", response.content)


	def test_unknown(self):
		message = 'Hello'
		response = self.rc.render_response_from_action(ResponseCenter.Action.UNKNOWN, self.minqi, message)
		self.assertEqual("We did not understand your message. For more information on how to use Smartdose you can visit PLACEHOLDER_URL.", response.content)

	def test_exceptional_action(self):
		message = "Make me breakfast"
		ResponseCenter.Action.MADE_UP_ACTION = -1
		with self.assertRaises(Exception):
		  self.rc.render_response_from_action(ResponseCenter.Action.MADE_UP_ACTION, self.minqi, message)


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

	def test_parse_message_to_action_ack_standard_ack(self):
		sender = self.minqi
		message = "1"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.ACK)

	def test_parse_message_to_action_ack_double_quotes_in_message(self):
		sender = self.minqi
		message = "\"1\""
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.ACK)

	def test_parse_message_to_action_ack_single_quotes_in_message(self):
		sender = self.minqi
		message = "\'1\'"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.ACK)

	def test_parse_message_to_action_ack_zero_ack(self):
		sender = self.minqi
		message = "0"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.ACK)

	def test_parse_message_to_action_ack_long_ack(self):
		sender = self.minqi
		message = "1231240"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.ACK)

	def test_parse_message_to_action_quit_lc_single_letter(self):
		sender = self.minqi
		message = "q"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.QUIT)

	def test_parse_message_to_action_quit_uc_single_letter(self):
		sender = self.minqi
		message = "Q"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.QUIT)

	def test_parse_message_to_action_quit_uc_word(self):
		sender = self.minqi
		message = "QUIT"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.QUIT)

	def test_parse_message_to_action_quit_lc_word(self):
		sender = self.minqi
		message = "quit"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.QUIT)

	def test_parse_message_to_action_quit_mc_word(self):
		sender = self.minqi
		message = "QuiT"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.QUIT)

	def test_parse_message_to_action_resume(self):
		sender = self.minqi
		message = "resume"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.RESUME)

	def test_parse_message_to_action_unknown_1(self):
		sender = self.minqi
		message = ""
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.UNKNOWN)

	def test_parse_message_to_action_unknown_2(self):
		sender = self.minqi
		message = "hello"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.UNKNOWN)

	def test_parse_message_to_action_unknown_3(self):
		sender = self.minqi
		message = "q1"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.UNKNOWN)

	def test_parse_message_to_action_unknown_4(self):
		sender = self.minqi
		message = "1q"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.UNKNOWN)

	def test_parse_message_to_action_unknown_5(self):
		sender = self.minqi
		message = "!#$3"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.UNKNOWN)

	def test_parse_message_to_action_unknown_6(self):
		sender = self.minqi
		message = "-1"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.UNKNOWN)

	def test_parse_message_to_action_not_valid_message(self):
		sender = self.minqi
		message = None
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.Action.NOT_VALID_MESSAGE)

	def test_parse_message_to_action_not_valid_user(self):
		unknown_sender = None
		message = "1"
		self.assertEqual(self.rc.parse_message_to_action(unknown_sender, message), ResponseCenter.Action.NOT_VALID_MESSAGE)
"""

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
		self.doctor = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",
		                                           primary_phone_number="2029163381", birthday=datetime.date(1960, 1, 1))
		self.drug = Drug.objects.create(name='advil')
		self.prescription = Prescription.objects.create(prescriber=self.doctor,
		                                                 patient=self.minqi, drug=self.drug, filled=True)
		self.notification = Notification.objects.create(to=self.minqi, type=Notification.MEDICATION,
		                                                prescription=self.prescription, repeat=Notification.DAILY,
		                                                send_datetime=datetime.datetime.now())
		self.refill_notification = Notification.objects.create(to=self.minqi, type=Notification.REFILL,
		                                                prescription=self.prescription, repeat=Notification.DAILY,
		                                                send_datetime=datetime.datetime.now())

	def test_process_medication_response_yes(self):
		message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
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
		message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, False)
		self.assertIsNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)
		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertFalse(Message.objects.filter(type=Message.MEDICATION_QUESTIONNAIRE))
		response = self.rc.process_medication_response(self.minqi, message, 'n')
		expected_response = "Why not? Reply:\n" \
		                    "a - Haven't gotten the chance\n" \
		                    "b - Need to refill\n" \
		                    "c - Side effects\n" \
		                    "d - Meds don't work\n" \
		                    "e - Prescription changed\n" \
		                    "f - I feel sad :(\n" \
		                    "g - Other"
		self.assertEqual(response.content, expected_response)
		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, False)
		self.assertTrue(Message.objects.filter(type=Message.MEDICATION_QUESTIONNAIRE))
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertIsNotNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)

	def test_process_medication_questionnaire_response_a(self):
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertFalse(Notification.objects.filter(type=Notification.REPEAT_MESSAGE))
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'a')
		expected_response = "No problem. We'll send you another reminder in an hour."
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)
		self.assertTrue(Notification.objects.filter(type=Notification.REPEAT_MESSAGE))

	def test_process_medication_questionnaire_response_b(self):
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'b')
		expected_response = "We'll let your doctor's office know you need a refill."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_questionnaire_response_c(self):
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.MEDICATION_QUESTIONNAIRE,
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
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'd')
		expected_response = "We'll let your doctor know that you don't think your meds are having the correct effects."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_questionnaire_response_e(self):
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.MEDICATION_QUESTIONNAIRE,
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
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.MEDICATION_QUESTIONNAIRE,
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
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.MEDICATION_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_medication_questionnaire_response(self.minqi, message, 'booga booga')
		expected_response = "We didn't understand that reply. Reply with a letter matching the options above.\n\n"+ \
							"For more information on how to use Smartdose, you can visit www.smartdo.se"
		self.assertEqual(response.content, expected_response)
		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_medication_response_yes(self):
		message = Message.objects.create(to=self.minqi, type=Notification.REFILL)
		feedback = Feedback.objects.create(type=Feedback.REFILL, notification=self.refill_notification,
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
		expected_response = "Great. You'll receive your first reminder tomorrow at 8:00am. To change the time of your reminder, simply reply with the time (e.g., 9am)."
		self.assertEqual(response.content, expected_response)
		self.assertEqual(Feedback.objects.get(pk=feedback.pk).completed, True)
		self.assertIsNotNone(Feedback.objects.get(pk=feedback.pk).datetime_responded)

		self.notification.send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(hour=7))
		self.notification.save()
		response = self.rc.process_refill_response(self.minqi, message, 'y')
		expected_response = "Great. You'll receive your first reminder tomorrow at 7:00am. To change the time of your reminder, simply reply with the time (e.g., 9am)."
		self.assertEqual(response.content, expected_response)

		self.notification.send_datetime = datetime.datetime.combine(datetime.datetime.today(), datetime.time(hour=14, minute=30))
		self.notification.save()
		response = self.rc.process_refill_response(self.minqi, message, 'y')
		expected_response = "Great. You'll receive your first reminder today at 2:30pm. To change the time of your reminder, simply reply with the time (e.g., 9am)."
		self.assertEqual(response.content, expected_response)

		self.notification.send_datetime = datetime.datetime.combine(datetime.datetime.today()-datetime.timedelta(days=3), datetime.time(hour=0, minute=30))
		self.notification.save()
		response = self.rc.process_refill_response(self.minqi, message, 'y')
		expected_response = "Great. You'll receive your first reminder tomorrow at 12:30am. To change the time of your reminder, simply reply with the time (e.g., 9am)."
		self.assertEqual(response.content, expected_response)


	def test_process_refill_questionnaire_response_a(self):
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.REFILL)
		feedback = Feedback.objects.create(type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.REFILL_QUESTIONNAIRE,
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
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.REFILL)
		feedback = Feedback.objects.create(type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.REFILL_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_refill_questionnaire_response(self.minqi, message, 'b')
		expected_response = "Medicine only works if you can afford to take it. We'll let your doctor know and someone will be in touch to help you find the best treatment."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_refill_questionnaire_response_c(self):
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.REFILL)
		feedback = Feedback.objects.create(type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.REFILL_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_refill_questionnaire_response(self.minqi, message, 'c')
		expected_response = "Your doctor wants to help. We'll let your doc know you're concerned.\n\n"+\
							"You can read more about what your meds do at smartdo.se/1234567890?c=12345"
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_process_refill_questionnaire_response_d(self):
		preceding_message = Message.objects.create(to=self.minqi, type=Notification.REFILL)
		feedback = Feedback.objects.create(type=Feedback.REFILL, notification=self.notification,
		                                   prescription=self.prescription)
		preceding_message.notifications.add(self.notification)
		preceding_message.feedbacks.add(feedback)
		preceding_message.save()
		message = Message.objects.create(to=preceding_message.to, type=Message.REFILL_QUESTIONNAIRE,
		                                 previous_message=preceding_message)
		for feedback in preceding_message.feedbacks.all():
			message.feedbacks.add(feedback)

		self.assertIsNone(Message.objects.get(pk=message.pk).datetime_responded)
		for feedback in preceding_message.feedbacks.all():
			self.assertFalse(feedback.note)
			self.assertEqual(feedback.completed, False)
		response = self.rc.process_refill_questionnaire_response(self.minqi, message, 'd')
		expected_response = "Please tell us more. We'll pass it along to your doctor."
		for feedback in preceding_message.feedbacks.all():
			self.assertTrue(feedback.note)
			self.assertEqual(feedback.completed, False)
		self.assertEqual(response.content, expected_response)
		self.assertIsNotNone(Message.objects.get(pk=message.pk).datetime_responded)

	def test_get_app_upsell_content(self):
		message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		content = self.rc._get_app_upsell_content(self.minqi, message)
		expected_response1 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+\
							 "You can add or remove safety net members at smartdo.se/1234567890?c=12345"

		expected_response2 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+\
							 "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345"

		expected_response3 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345"

		expected_response4 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345"
		expected_responses = [expected_response1, expected_response2, expected_response3, expected_response4]
		self.assertIn(content, expected_responses)

	def test_get_app_upsell_content_with_safety_net(self):
		message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		self.minqis_safety_net = PatientProfile.objects.create(
			first_name='Jianna', last_name='Jiang', primary_phone_number='1234567890')
		self.minqi.add_safety_net_contact(
			target_patient=self.minqis_safety_net, relationship='mother')

		content = self.rc._get_app_upsell_content(self.minqi, message)
		expected_response1 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "You can add or remove safety net members at smartdo.se/1234567890?c=12345"

		expected_response2 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345"

		expected_response3 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345"

		expected_response4 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345"

		expected_response5 = "Jianna will be happy you're taking care of your health.\n\n"+ \
		                     "You can add or remove safety net members at smartdo.se/1234567890?c=12345"

		expected_response6 = "Jianna will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345"

		expected_response7 = "Jianna will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345"

		expected_response8 = "Jianna will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345"
		expected_responses = [expected_response1, expected_response2, expected_response3, expected_response4,
		                      expected_response5, expected_response6, expected_response7, expected_response8]
		print content
		self.assertIn(content, expected_responses)

	def test_get_health_educational_content(self):
		message = Message.objects.create(to=self.minqi, type=Notification.MEDICATION)
		feedback = Feedback.objects.create(type=Feedback.MEDICATION, notification=self.notification,
		                                   prescription=self.prescription)
		message.notifications.add(self.notification)
		message.feedbacks.add(feedback)
		message.save()

		# Test when there are no facts (same behavior as get_app_upsell_content)
		expected_response1 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "You can add or remove safety net members at smartdo.se/1234567890?c=12345"

		expected_response2 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can view every dose you've ever taken at smartdo.se/1234567890?c=12345"

		expected_response3 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can adjust reminder times at smartdo.se/1234567890?c=12345"

		expected_response4 = "Dr. Watcher will be happy you're taking care of your health.\n\n"+ \
		                     "Did you know you can learn about your meds at smartdo.se/1234567890?c=12345"
		expected_responses = [expected_response1, expected_response2, expected_response3, expected_response4]
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

	def test_quit_initial_quit(self):
		message = 'q'
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		self.assertEqual(self.minqi.quit_request_datetime, None)
		response = self.rc.process_response(self.minqi, message)
		self.assertEqual("Are you sure you'd like to quit? You can adjust your settings and learn more about Smartdose at PLACEHOLDER_URL. Reply 'quit' to quit using Smartdose.", response.content)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_quit_confirm_quit(self):
		message = 'q'
		self.minqi.quit_request_datetime = datetime.datetime.now()
		self.minqi.save()
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		self.assertNotEqual(self.minqi.quit_request_datetime, None)
		response = self.rc.process_response(self.minqi, message)
		self.assertEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
		self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_quit_long_after_initial_quit(self):
		message = 'q'
		self.minqi.quit_request_datetime = datetime.datetime.now() - datetime.timedelta(hours=2)
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		response = self.rc.process_response(self.minqi, message)
		self.assertEqual("Are you sure you'd like to quit? You can adjust your settings and learn more about Smartdose at PLACEHOLDER_URL. Reply 'quit' to quit using Smartdose.", response.content)
		self.assertNotEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

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
