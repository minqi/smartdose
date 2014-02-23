import datetime
from common.utilities import list_to_queryset
from django.http import HttpResponseNotFound
from django.test import TestCase
import mock
from patients.models import PatientProfile
from reminders.models import Message
from reminders.response_center import ResponseCenter

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
		valid_message = Message(patient=self.minqi, message_number=message_number, state=Message.UNACKED)
		valid_message_as_list = [valid_message]
		# Create a fake Message.objects.filter method to patch into our code.
		def fake_filter(message_number, **kwargs):
			if message_number is "1":
				return valid_message_as_list
			elif message_number is not None:
				return []
			else:
				raise Exception("Must specify message_number here")
		self.assertEqual(valid_message.state, Message.UNACKED)
		with mock.patch('reminders.models.Message.objects.filter', fake_filter):
			response = self.rc.render_response_from_action(ResponseCenter.ACTION.ACK, self.minqi, str(ack_number))
			self.assertEqual("Your family will be happy to know that you're taking care of your health.", response.content)
			self.assertEqual(valid_message.state, Message.ACKED)

	def test_ack_invalid(self):
		message_number = 1
		ack_number = 2
		valid_message = Message(patient=self.minqi, message_number=message_number, state=Message.UNACKED)
		valid_message_as_list = [valid_message]
		# Create a fake Message.objects.filter method to patch into our code.
		def fake_filter(message_number, **kwargs):
			if message_number is "1":
				return valid_message_as_list
			elif message_number is not None:
				return []
			else:
				raise Exception("Must specify message_number here")
		self.assertEqual(valid_message.state, Message.UNACKED)
		with mock.patch('reminders.models.Message.objects.filter', fake_filter):
			response = self.rc.render_response_from_action(ResponseCenter.ACTION.ACK, self.minqi, str(ack_number))
			self.assertEqual("Whoops - there is no reminder with number 2 that needs a response.", response.content)
			self.assertEqual(valid_message.state, Message.UNACKED)

	def test_not_valid(self):
		not_valid_message = "heaoij"
		not_valid_sender = None
		response = self.rc.render_response_from_action(ResponseCenter.ACTION.NOT_VALID_MESSAGE, not_valid_sender, not_valid_message)
		self.assertEqual(HttpResponseNotFound().status_code, response.status_code)

	def test_quit_initial_quit(self):
		message = 'q'
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		self.assertEqual(self.minqi.quit_request_datetime, None)
		response = self.rc.render_response_from_action(ResponseCenter.ACTION.QUIT, self.minqi, message)
		self.assertEqual("Are you sure you'd like to quit? You can adjust your settings and learn more about Smartdose at PLACEHOLDER_URL. Reply 'quit' to quit using Smartdose.", response.content)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_quit_confirm_quit(self):
		message = 'q'
		self.minqi.quit_request_datetime = datetime.datetime.now()
		self.minqi.save()
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		self.assertNotEqual(self.minqi.quit_request_datetime, None)
		response = self.rc.render_response_from_action(ResponseCenter.ACTION.QUIT, self.minqi, message)
		self.assertEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
		self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_quit_long_after_initial_quit(self):
		message = 'q'
		self.minqi.quit_request_datetime = datetime.datetime.now() - datetime.timedelta(hours=2)
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		response = self.rc.render_response_from_action(ResponseCenter.ACTION.QUIT, self.minqi, message)
		self.assertEqual("Are you sure you'd like to quit? You can adjust your settings and learn more about Smartdose at PLACEHOLDER_URL. Reply 'quit' to quit using Smartdose.", response.content)
		self.assertNotEqual("You have been unenrolled from Smartdose. You can reply \"resume\" at any time to resume using the Smartdose service.", response.content)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).quit_request_datetime, None)
		self.assertNotEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.QUIT)

	def test_resume_for_quit_patient(self):
		message = 'resume'
		self.minqi.status = PatientProfile.QUIT
		self.minqi.save()
		response = self.rc.render_response_from_action(ResponseCenter.ACTION.RESUME, self.minqi, message)
		self.assertEqual(PatientProfile.objects.get(pk=self.minqi.pk).status, PatientProfile.ACTIVE)
		self.assertEqual("Welcome back to Smartdose.", response.content)

	def test_resume_for_not_quit_patient(self):
		message = 'resume'
		self.assertNotEqual(self.minqi.status, PatientProfile.QUIT)
		response = self.rc.render_response_from_action(ResponseCenter.ACTION.RESUME, self.minqi, message)
		self.assertEqual("We did not understand your message. For more information on how to use Smartdose you can visit PLACEHOLDER_URL.", response.content)


	def test_unknown(self):
		message = 'Hello'
		response = self.rc.render_response_from_action(ResponseCenter.ACTION.UNKNOWN, self.minqi, message)
		self.assertEqual("We did not understand your message. For more information on how to use Smartdose you can visit PLACEHOLDER_URL.", response.content)

	def test_exceptional_action(self):
		message = "Make me breakfast"
		ResponseCenter.ACTION.MADE_UP_ACTION = -1
		with self.assertRaises(Exception):
		  self.rc.render_response_from_action(ResponseCenter.ACTION.MADE_UP_ACTION, self.minqi, message)


class ParseMessageToActionTest(TestCase):
	#TODO(mgaba): Write tests for SMSResponsesToReminders:
	#TODO(mgaba): Test "hello" response
	#TODO(mgaba): Test number and letter response
	#TODO(mgaba): Test proper acknowledgment
	#TODO(mgaba): Test acknowledgment of just-acknowledged message
	#TODO(mgaba): Test acknowledgment with wrong message number
	#TODO(mgaba): Test a text from an unknown number
	#TODO(mgaba): Test an ack of a pharmacy refill reminder
	#TODO(mgaba): Test opt-out interaction
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
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.ACK)

	def test_parse_message_to_action_ack_zero_ack(self):
		sender = self.minqi
		message = "0"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.ACK)

	def test_parse_message_to_action_ack_long_ack(self):
		sender = self.minqi
		message = "1231240"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.ACK)

	def test_parse_message_to_action_quit_lc_single_letter(self):
		sender = self.minqi
		message = "q"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.QUIT)

	def test_parse_message_to_action_quit_uc_single_letter(self):
		sender = self.minqi
		message = "Q"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.QUIT)

	def test_parse_message_to_action_quit_uc_word(self):
		sender = self.minqi
		message = "QUIT"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.QUIT)

	def test_parse_message_to_action_quit_lc_word(self):
		sender = self.minqi
		message = "quit"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.QUIT)

	def test_parse_message_to_action_quit_mc_word(self):
		sender = self.minqi
		message = "QuiT"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.QUIT)

	def test_parse_message_to_action_resume(self):
		sender = self.minqi
		message = "resume"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.RESUME)

	def test_parse_message_to_action_unknown_1(self):
		sender = self.minqi
		message = ""
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.UNKNOWN)

	def test_parse_message_to_action_unknown_2(self):
		sender = self.minqi
		message = "hello"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.UNKNOWN)

	def test_parse_message_to_action_unknown_3(self):
		sender = self.minqi
		message = "q1"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.UNKNOWN)

	def test_parse_message_to_action_unknown_4(self):
		sender = self.minqi
		message = "1q"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.UNKNOWN)

	def test_parse_message_to_action_unknown_5(self):
		sender = self.minqi
		message = "!#$3"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.UNKNOWN)

	def test_parse_message_to_action_unknown_6(self):
		sender = self.minqi
		message = "-1"
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.UNKNOWN)

	def test_parse_message_to_action_not_valid_message(self):
		sender = self.minqi
		message = None
		self.assertEqual(self.rc.parse_message_to_action(sender, message), ResponseCenter.ACTION.NOT_VALID_MESSAGE)

	def test_parse_message_to_action_not_valid_user(self):
		unknown_sender = None
		message = "1"
		self.assertEqual(self.rc.parse_message_to_action(unknown_sender, message), ResponseCenter.ACTION.NOT_VALID_MESSAGE)
