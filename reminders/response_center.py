import glob
import itertools
from common.models import DrugFact
from django.http import HttpResponseNotFound, HttpResponse
from django.template import Context
from django.template.loader import render_to_string
from patients.models import SafetyNetRelationship
from reminders.models import Message, Notification
import datetime
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
		message = message.replace("\'", "").replace("\"", "")  # Users may reply with quotation marks, so remove quotes
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

	def _is_resume(self, message):
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
		ack_message_types = [self._get_motivational_ack_response_content,
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
		message_number = message.replace("\'", "").replace("\"",
		                                                   "")  # Users may reply with quotation marks, so remove quotes
		acked_messages = Message.objects.filter(patient=sender,
		                                        message_number=message_number,
		                                        state=Message.UNACKED)
		if not acked_messages:
			context = {'message_number': message_number}
			content = render_to_string('messages/response_nothing_to_ack.txt', context)
		else:
			for acked_message in acked_messages:
				acked_message.processAck()
			content = self._get_best_ack_response_content(sender, acked_messages)

		return HttpResponse(content=content, content_type="text/plain")

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

	def _get_adherence_ratio_ack_response_content(self, sender, acked_messages):
		#TODO(mgaba): What kind of information should go in a message that reports
		# adherence ratio to a patient? Is it adherence to a particular drug?
		# Is it overall adherence? Over what time frame?
		raise Exception("Not yet implemented")

	def _get_app_upsell_content(self, sender, acked_message):
		# Select path to the appropriate upsell content
		upsell_content_choices = glob.glob("templates/messages/medication_yes_responses/app_upsell/*.txt")
		remove_preceding_content = "templates/"
		upsell_content	= random.choice(upsell_content_choices)
		upsell_content = upsell_content[remove_preceding_content.__len__():]

		# Find the happy person in string <happy_person> will be happy you're taking care of your health.
		happy_people = []
		safety_net_members = SafetyNetRelationship.objects.filter(source_patient=sender, opt_out=False)
		if safety_net_members:
			for safety_net_member in safety_net_members:
				happy_people.append(safety_net_member.target_patient.first_name)
		happy_people.append("Dr. " + acked_message.feedbacks.all()[0].prescription.prescriber.last_name)
		happy_person = random.choice(happy_people)

		dict = {'app_upsell_content' : upsell_content,
		        'happy_person' : happy_person}
		# TODO: Make this template so that if it gets too long it will choose the shorter name
		content = render_to_string('messages/medication_yes_responses/app_upsell.txt', dict)
		return content

	def _get_health_educational_content(self, sender, acked_message):
		drug_choices = []
		for feedback in acked_message.feedbacks.all():
			drug_choices.append(feedback.prescription.drug)
		drug = random.choice(drug_choices)
		drug_fact_choices = DrugFact.objects.filter(drug=drug)
		if drug_fact_choices:
			drug_fact = random.choice(list(drug_fact_choices))
			return drug_fact.fact
		else:
			return self._get_app_upsell_content(sender, acked_message)

	def _return_best_ack_response_content(self, sender, acked_message):
		random_ack_message_choices = [self._get_app_upsell_content,
									 self._get_health_educational_content]

		#TODO add gamification content.

		return random.choice(random_ack_message_choices)(sender,acked_message)


	def is_yes(self, response):
		if response.lower() in ['y', 'yes']:
			return True
		else:
			return False

	def is_no(self, response):
		if response.lower() in ['n', 'no']:
			return True
		else:
			return False

	def is_med_info(self, response):
		if response.lower() in ['m', 'info']:
			return True
		else:
			return False

	def process_medication_response(self, sender, message, response):
		""" Process a response to a medication message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()

		# Switch on type of response
		if self.is_yes(response):
			# Send out a medication ack message
			# Update state
			feedbacks = message.feedbacks.all()
			for feedback in feedbacks:
				feedback.completed = True
				feedback.datetime_responded = now
				feedback.save()

			# Create new message
			content = self._get_best_ack_response_content(sender, message)
			Message.objects.create(to=sender, type=Message.MEDICATION_ACK, previous_message=message, content=content)
			return HttpResponse(content=content, content_type='text/plain')

		elif self.is_no(response):
			# Send out a medication questionnaire message
			# Update state
			feedbacks = message.feedbacks.all()
			for feedback in feedbacks:
				feedback.completed = False
				feedback.datetime_responded = now
				feedback.save()

			# Create a questionnaire message
			template = 'messages/medication_questionnaire_message.txt'
			context = {'response_dict': iter(sorted(Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY.items()))}
			content = render_to_string(template, context)

			# Create new message
			new_m = Message.objects.create(to=sender, type=Message.MEDICATION_QUESTIONNAIRE, previous_message=message,
			                               content=content)
			for feedback in feedbacks:
				new_m.feedbacks.add(feedback)
			return HttpResponse(content=content, content_type='text/plain')

		elif self.is_med_info(response):
			# Send out a med info message
			pass

		elif self.is_time_change(response):
			# Update reminder time and send out a time change ack
			pass

	def process_medication_questionnaire_response(self, sender, message, response):
		""" Process a response to a medication questionnaire message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()

		def process_response(return_message_type):
			for feedback in message.feedbacks.all():
				feedback.note = Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY[response.lower()]
				feedback.save()
			template = 'messages/medication_questionnaire_responses/' + \
			           Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY[response.lower()] + \
			           '.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, type=return_message_type, content=content)
			return HttpResponse(content=content, content_type='text/plain')


		# Switch on type of response
		# a - Haven't gotten the chance
		if response.lower() == 'a':
			# Schedule a medication reminder for later
			one_hour = datetime.datetime.now() + datetime.timedelta(hours=1)
			n = Notification.objects.create(to=sender, type=Notification.REPEAT_MESSAGE, repeat=Notification.NO_REPEAT,
			                                message=message.previous_message, send_datetime=one_hour)

			# Send response
			return process_response(Message.STATIC_ONE_OFF)

		# b - Need to refill
		elif response.lower() == 'b':
			#TODO(mgaba): Figure out what else should happen if someone needs to refill
			# Send response
			return process_response(Message.STATIC_ONE_OFF)

		# c - Side effects
		elif response.lower() == 'c':
			#TODO(mgaba): Figure out what else should happen if someone has side effects
			#TODO(mgaba): Add doctors name to personalize messages
			# Send response
			return process_response(Message.STATIC_ONE_OFF)

		# d - Meds don't work
		elif response.lower() == 'd':
			#TODO(mgaba): Add doctors name to personalize messages
			return process_response(Message.STATIC_ONE_OFF)

		# e - Prescription changed
		elif response.lower() == 'e':
			#TODO(mgaba): Add doctors name to personalize messages
			return process_response(Message.STATIC_ONE_OFF)

		# f - I feel sad :(
		elif response.lower() == 'f':
			return process_response(Message.STATIC_ONE_OFF)

		# g - Other
		elif response.lower() == 'g':
			#TODO(mgaba): Add doctors name to personalize message
			return process_response(Message.OPEN_ENDED_QUESTION)
		# Unknown response
		else:
			message.datetime_responded = None
			message.save()
			template = 'messages/medication_questionnaire_responses/Unknown_Response.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, type=Message.STATIC_ONE_OFF, content=content)
			return HttpResponse(content=content, content_type='text/plain')


	def process_refill_response(self, sender, message, response):
		""" Process a response to a refill message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()
		raise Exception("Not yet implemented")

	def process_refill_questionnaire_response(self, sender, message, response):
		""" Process a response to a refill questionnaire message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()
		raise Exception("Not yet implemented")

	def process_med_info_response(self, sender, message, response):
		""" Process a response to a med info message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()
		raise Exception("Not yet implemented")

	def process_non_adherent_response(self, sender, message, response):
		""" Process a response to a non adherence message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()
		raise Exception("Not yet implemented")

	def process_non_adherent_questionnaire_response(self, sender, message, response):
		""" Process a response to a non adherence questionnaire message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()
		raise Exception("Not yet implemented")

	def process_open_ended_question_response(self, sender, message, response):
		""" Process a response to a open ended question message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()
		raise Exception("Not yet implemented")


	RESPONSE_MAP = \
		{Message.MEDICATION: process_medication_response,
		 Message.MEDICATION_QUESTIONNAIRE: process_medication_questionnaire_response,
		 Message.REFILL: process_refill_response,
		 Message.REFILL_QUESTIONNAIRE: process_refill_questionnaire_response,
		 Message.MED_INFO: process_med_info_response,
		 Message.NON_ADHERENT: process_non_adherent_response,
		 Message.NON_ADHERENT_QUESTIONNAIRE: process_non_adherent_questionnaire_response,
		 Message.OPEN_ENDED_QUESTION: process_open_ended_question_response}

	def process_response(self, sender, response):
		""" Returns an HttpResponse object. Changes state of system based on action and sender's message
		"""

		if sender is None or (sender.did_quit() and not self._is_resume(response)):
			return self._process_not_valid_response()

		# Generic logic for responding to any type of message goes here
		# PUT IT HERE

		last_sent_message = Message.objects.get_last_sent_message_requiring_response(to=sender)
		if not last_sent_message:
			#TODO Implement code for when there is no sent message
			return HttpResponseNotFound()
		return ResponseCenter.RESPONSE_MAP[last_sent_message.type](self, sender, last_sent_message, response)

"""
		elif action == ResponseCenter.Action.QUIT:
			return self._process_quit_response(sender)
		elif action == ResponseCenter.Action.RESUME:
			return self._process_resume_response(sender)
"""
"""
		if action == ResponseCenter.Action.NOT_VALID_MESSAGE or \
			(sender and sender.did_quit() and action != ResponseCenter.Action.RESUME):
			return self._process_not_valid_response()
		elif action == ResponseCenter.Action.ACK:
			return self._process_ack_response(sender, message)
		elif action == ResponseCenter.Action.UNKNOWN:
			return self._process_unknown_response()
		else:
			raise Exception("ResponseCenter asked to process an action it doesn't know about")
			"""
