from django.http import HttpResponseNotFound, HttpResponse
from django.template.loader import render_to_string
from reminders.models import Message
import random


class ResponseCenter(object):
	@staticmethod
	class Action:
		ACK, QUIT, RESUME, UNKNOWN, NOT_VALID_MESSAGE = range(5)
		def __init__(self):
			pass



	def _parse_is_ack(self, message):
		""" Returns true if the message is an acknowledgment message
		"""
		message = message.replace("\'", "").replace("\"", "") # Users may reply with quotation marks, so remove quotes
		try:
			if float(message) >= 0:
				return True
			else:
				return False
		except ValueError:
			return False

	def _parse_is_quit(self, message):
		""" Returns true if the message is a quit message
		"""
		if message.lower() == "q" or message.lower() == "quit":
			return True
		else:
			return False

	def _parse_is_resume(self, message):
		""" Returns true if the message is a resume
		"""
		if message.lower() == "resume":
			return True
		else:
			return False

	def parse_message_to_action(self, sender, message):
		""" Processes a message from sender and returns an action to perform
			in response to the message.
			sender is a PatientProfile object.
			message is the content of the text message sent to Smartdose
		"""
		if message == None or sender == None:
			return ResponseCenter.Action.NOT_VALID_MESSAGE

		if self._parse_is_ack(message):
			return ResponseCenter.Action.ACK
		elif self._parse_is_quit(message):
			return ResponseCenter.Action.QUIT
		elif self._parse_is_resume(message):
			return ResponseCenter.Action.RESUME
		else:
			return ResponseCenter.Action.UNKNOWN

	def _get_adherence_ratio_ack_response_content(self, sender, acked_messages):
		#TODO(mgaba): What kind of information should go in a message that reports
		# adherence ratio to a patient? Is it adherence to a particular drug?
		# Is it overall adherence? Over what time frame?
		raise Exception("Not yet implemented")

	def _get_motivational_ack_response_content(self, sender, acked_messages):
		#TODO(mgaba): Add multiple motivational messages
		content = render_to_string('messages/response_motivational_text_generic.txt')
		return HttpResponse(content=content, content_type="text/plain")

	def _get_best_ack_response_content(self, sender, acked_messages):
		#TODO(mgaba): Ideas for other types of responses:
		# Educational: Contains information about a drug you just acked
		# Social: How adherent are others on the system?
		# Family: How does your safety net feel when you take your medicine?
		# Gamification: How many adherence points have you gained?
		ack_message_types = [  self._get_motivational_ack_response_content,
		                       self._get_adherence_ratio_ack_response_content]

		# When we're ready we can simply randomize the choice. In the future, use what we know about the user to
		# choose the optimal type of message.
		#return random.choice(ack_message_types)(sender,acked_messages)

		# We will only call the motivational response for now. When we're ready, go to random approach that
		# is commented out above.
		return self._get_motivational_ack_response_content(sender, acked_messages)

	def _process_not_valid_response(self):
		return HttpResponseNotFound()

	def _process_ack_response(self, sender, message):
		message_number = message.replace("\'", "").replace("\"", "") # Users may reply with quotation marks, so remove quotes
		acked_messages = Message.objects.filter(patient=sender,
												message_number=message_number,
												state=Message.UNACKED)
		if not acked_messages:
			context = { 'message_number':message_number }
			content = render_to_string('messages/response_nothing_to_ack.txt', context)
		else:
			for acked_message in acked_messages:
				acked_message.processAck()
			content = self._get_best_ack_response_content(sender, acked_messages)

		return HttpResponse(content=content,content_type="text/plain")

	def _process_quit_response(self, sender):
		if sender.did_request_quit_within_quit_response_window():
			sender.quit()
			content = render_to_string('messages/response_quit_is_confirmed.txt')
		else:
			sender.record_quit_request()
			content = render_to_string('messages/response_quit_break_the_glass.txt')
		return HttpResponse(content=content)

	def _process_unknown_response(self):
		content = render_to_string('messages/response_unknown.txt')
		return HttpResponse(content=content, content_type="text/plain")

	def _process_resume_response(self, sender):
		if sender.did_quit():
			sender.resume()
			content = render_to_string('messages/response_resume_welcome_back.txt')
			return HttpResponse(content=content, content_type="text/plain")
		else:
			return self._process_unknown_response()

	def render_response_from_action(self, action, sender, message):
		""" Returns an HttpResponse object. Changes state of system based on action and sender's message
		"""

		if action == ResponseCenter.Action.NOT_VALID_MESSAGE or \
			(sender and sender.did_quit() and action != ResponseCenter.Action.RESUME):
			return self._process_not_valid_response()
		elif action == ResponseCenter.Action.ACK:
			return self._process_ack_response(sender, message)
		elif action == ResponseCenter.Action.QUIT:
			return self._process_quit_response(sender)
		elif action == ResponseCenter.Action.RESUME:
			return self._process_resume_response(sender)
		elif action == ResponseCenter.Action.UNKNOWN:
			return self._process_unknown_response()
		else:
			raise Exception("ResponseCenter asked to process an action it doesn't know about")
