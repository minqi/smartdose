import glob, itertools, re, datetime, random

from django.http import HttpResponseNotFound, HttpResponse
from django.template import Context
from django.template.loader import render_to_string

from common.models import DrugFact
from patients.models import SafetyNetRelationship
from reminders.models import Message, Notification


class ResponseCenter(object):
	def _is_quit(self, message):
		""" 
		Returns true if the message is a quit message
		"""
		return message.lower() in ("q", "quit")

	def _is_pause(self, message):
		return message.lower() in ("p", "pause")

	def _is_resume(self, message):
		""" 
		Returns true if the message is a resume
		"""
		return message.lower() in ("r", "resume")

	def is_yes(self, response):
		return response.lower() in ['y', 'yes']

	def is_no(self, response):
		return response.lower() in ['n', 'no']

	def is_med_info(self, response):
		return response.lower() in ['m', 'info']

	def is_time_change(self, response):
		# Parse time from response
		time_with_minutes_re = "^(?P<hour>[0-9]{1,2})(:)?(?P<minute>[0-9][0-9])(\\s)?(?i)(?P<ampm>am|pm)?$"
		time_without_minutes_re = "^(?P<hour>[0-9]{1,2})(\\s)?(?i)(?P<ampm>am|pm)?$"
		time_res = [time_with_minutes_re, time_without_minutes_re]
		for regex in time_res:
			formatted_time = re.match(regex, response.lower())
			if formatted_time:
				break

		if formatted_time:
			extracted_hour = formatted_time.group("hour")
			try:
				extracted_minute = formatted_time.group("minute")
			except:
				extracted_minute = None
			if int(extracted_hour) < 24:
				hours = int(extracted_hour)
			else:
				return False
			if extracted_minute:
				if int(extracted_minute) < 60:
					minutes = int(extracted_minute)
				else:
					return False
			else:
				minutes = 0

			# Hours greater than 12 shouldn't have ampm. For example 13pm. Or 13am
			if formatted_time.group("ampm") != "" and hours > 12:
				return False

			if formatted_time.group("ampm") == 'pm' and hours < 12:
				hours = hours+12

			time = datetime.time(hour=hours, minute=minutes)
			return time
		else:
			return False

	def process_invalid_response(self):
		return HttpResponseNotFound()

	def process_quit_response(self, sender):
		if sender.did_request_quit_within_quit_response_window():
			sender.quit()
			content = render_to_string('messages/response_quit_is_confirmed.txt')
		else:
			sender.record_quit_request()
			content = render_to_string('messages/response_quit_break_the_glass.txt')
		return HttpResponse(content=content)

	def process_pause_response(self, sender):
		sender.pause()
		content = render_to_string('messages/response_pause_is_confirmed.txt')
		return HttpResponse(content=content, content_type="text/plain")

	def process_resume_response(self, sender):
		if sender.did_quit():
			sender.resume()
			content = render_to_string('messages/response_resume_welcome_back.txt')
			return HttpResponse(content=content, content_type="text/plain")

	def _get_adherence_ratio_ack_response_content(self, sender, acked_messages):
		#TODO: What kind of information should go in a message that reports
		# adherence ratio to a patient? Is it adherence to a particular drug?
		# Is it overall adherence? Over what time frame?
		raise Exception("Not yet implemented")

	def _get_app_upsell_content(self, sender, acked_message):
		# Select path to the appropriate upsell content
		upsell_content_choices = glob.glob("templates/messages/medication_responses/yes_responses/app_upsell/*.txt")
		remove_preceding_content = "templates/"
		upsell_content	= random.choice(upsell_content_choices)
		upsell_content = upsell_content[remove_preceding_content.__len__():]
		upsell_content = 'messages/medication_responses/yes_responses/app_upsell/dummy.txt'

		# Find the happy person in string <happy_person> will be happy you're taking care of your health.
		happy_people = []
		safety_net_members = SafetyNetRelationship.objects.filter(source_patient=sender, opt_out=False)
		if safety_net_members:
			for safety_net_member in safety_net_members:
				happy_people.append(safety_net_member.target_patient.first_name)
		prescriber = acked_message.feedbacks.all()[0].prescription.prescriber
		if hasattr(prescriber, "doctorprofile"):
			happy_people.append("Dr. " + prescriber.last_name)
		else:
			happy_people.append("Your family")
		happy_person = random.choice(happy_people)

		# upsell_content = ''
		dict = {'app_upsell_content' : upsell_content,
		        'happy_person' : happy_person}
		# TODO: Make this template so that if it gets too long it will choose the shorter name
		content = render_to_string('messages/medication_responses/app_upsell.txt', dict)
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
		random_ack_message_choices = [
			self._get_app_upsell_content,
			self._get_health_educational_content,
		]
		#TODO add gamification content.

		return random.choice(random_ack_message_choices)(sender, acked_message)

	def process_medication_response(self, sender, message, response):
		"""
		Process a response to a medication message
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
			content = self._return_best_ack_response_content(sender, message)
			Message.objects.create(to=sender, _type=Message.MEDICATION_ACK, previous_message=message, content=content)
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
			new_m = Message.objects.create(to=sender, _type=Message.MEDICATION_QUESTIONNAIRE, previous_message=message,
			                               content=content)
			for feedback in feedbacks:
				new_m.feedbacks.add(feedback)
			return HttpResponse(content=content, content_type='text/plain')

		elif self.is_med_info(response):
			# Send out a med info message
			message.datetime_responded = None
			message.save()
			content = "Medication information is a work in progress.\n\n"+ \
			          "Did you take your meds?\n"+ \
			          "y - yes\n"+ \
			          "n - no"
			return HttpResponse(content=content, content_type='text/plain')
			pass

		elif self.is_time_change(response):
			# Update reminder time and send out a time change ack
			pass
		# Unknown response
		else:
			message.datetime_responded = None
			message.save()
			template = 'messages/unknown_response.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, _type=Message.STATIC_ONE_OFF, content=content)
			return HttpResponse(content=content, content_type='text/plain')

	def process_medication_questionnaire_response(self, sender, message, response):
		""" Process a response to a medication questionnaire message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()

		def process_response(return_message_type):
			for feedback in message.feedbacks.all():
				feedback.note = Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY[response.upper()]
				feedback.save()
			template = 'messages/medication_questionnaire_responses/' + \
			           Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY[response.upper()] + \
			           '.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, _type=return_message_type, content=content, previous_message=message)
			return HttpResponse(content=content, content_type='text/plain')

		# Switch on type of response
		# a - Haven't gotten the chance
		if response.lower() == 'a':
			# Schedule a medication reminder for later
			one_hour = datetime.datetime.now() + datetime.timedelta(hours=1)
			n = Notification.objects.create(to=sender, _type=Notification.REPEAT_MESSAGE, repeat=Notification.NO_REPEAT,
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
			template = 'messages/unknown_response.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, _type=Message.STATIC_ONE_OFF, content=content)
			return HttpResponse(content=content, content_type='text/plain')

	def process_refill_response(self, sender, message, response):
		""" Process a response to a refill message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()

		# Switch on type of response
		if self.is_yes(response):
			# TODO(mgaba): Implement questions about weekly, monthly prescriptions. What's the right day?
			# Send out a medication ack message
			# Update state
			feedbacks = message.feedbacks.all()
			for feedback in feedbacks:
				feedback.completed = True
				feedback.datetime_responded = now
				feedback.save()

			notifications = message.notifications.all()
			for notification in notifications:
				notification.active = False
				notification.save()

			# Calculate the time of the next earliest notification to put in the message that gets sent back
			earliest_notification = None
			now = datetime.datetime.now()
			for feedback in feedbacks:
				feedback.prescription.filled = True
				feedback.prescription.save()
				med_notifications = Notification.objects.filter(prescription=feedback.prescription, _type=Notification.MEDICATION)
				for med_notification in med_notifications:
					if med_notification.send_datetime < now:
						med_notification.update_to_next_send_time()
					if earliest_notification == None or earliest_notification.send_datetime > med_notification.send_datetime:
						earliest_notification = med_notification

			# Convert the time of the next earliest notification to a string for the template
			hour = earliest_notification.send_datetime.hour
			minute = earliest_notification.send_datetime.minute
			if hour == 0:
				hour = 12
				ampm = 'am'
			elif hour == 12:
				hour = 12
				ampm = 'pm'
			elif hour > 12:
				hour = hour - 12
				ampm = 'pm'
			else:
				ampm = 'am'
			if earliest_notification.send_datetime.date() == now.date():
				day = "today"
			elif earliest_notification.send_datetime.date() == now.date() + datetime.timedelta(days=1):
				day = "tomorrow"
			elif earliest_notification.send_datetime.date() <  now.date() + datetime.timedelta(days=7):
				weekdays = {'0':'Monday',
				            '1':'Tuesday',
				            '2':'Wednesday',
				            '3':'Thursday',
				            '4':'Friday',
				            '5':'Saturday',
				            '6':'Sunday'}
				day = "on " + weekdays[str(earliest_notification.send_datetime.weekday())]

			# Create new message
			context = {'hour':hour,
			           'minute':minute,
			           'ampm':ampm,
			           'day':day}
			template = 'messages/refill_ack_message.txt'
			content = render_to_string(template, context)
			Message.objects.create(to=sender, _type=Message.STATIC_ONE_OFF, previous_message=message, content=content)
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
			template = 'messages/refill_questionnaire_message.txt'
			context = {'response_dict': iter(sorted(Message.REFILL_QUESTIONNAIRE_RESPONSE_DICTIONARY.items()))}
			content = render_to_string(template, context)

			# Create new message
			new_m = Message.objects.create(to=sender, _type=Message.REFILL_QUESTIONNAIRE, previous_message=message,
			                               content=content)
			for feedback in feedbacks:
				new_m.feedbacks.add(feedback)
			return HttpResponse(content=content, content_type='text/plain')

		elif self.is_med_info(response):
			# Send out a med info message
			# TODO:Implement med info for real
			message.datetime_responded = None
			message.save()
			content = "Medication information is a work in progress.\n\n"+\
					  "Did you pick up your meds?\n"+\
					  "y - yes\n"+\
					  "n - no"
			return HttpResponse(content=content, content_type='text/plain')
			pass
		# Unknown response
		else:
			message.datetime_responded = None
			message.save()
			template = 'messages/unknown_response.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, _type=Message.STATIC_ONE_OFF, content=content)
			return HttpResponse(content=content, content_type='text/plain')
		raise Exception("Not yet implemented")

	def process_refill_questionnaire_response(self, sender, message, response):
		""" Process a response to a refill questionnaire message
		"""
		now = datetime.datetime.now()
		message.datetime_responded = now
		message.save()

		def process_response(return_message_type):
			for feedback in message.feedbacks.all():
				feedback.note = Message.REFILL_QUESTIONNAIRE_RESPONSE_DICTIONARY[response.upper()]
				feedback.save()
			template = 'messages/refill_questionnaire_responses/' + \
			           Message.REFILL_QUESTIONNAIRE_RESPONSE_DICTIONARY[response.upper()] + \
			           '.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, _type=return_message_type, content=content, previous_message=message)
			return HttpResponse(content=content, content_type='text/plain')


		# Switch on type of response
		# a - Haven't gotten the chance
		if response.lower() == 'a':
			# Schedule a medication reminder for later
			one_hour = datetime.datetime.now() + datetime.timedelta(hours=1)

			# Send response
			return process_response(Message.STATIC_ONE_OFF)

		# b - Too expensive
		elif response.lower() == 'b':
			#TODO(mgaba): Figure out what else should happen if someone needs to refill
			# Send response
			return process_response(Message.STATIC_ONE_OFF)

		# c - Concerned about side effects
		elif response.lower() == 'c':
			#TODO(mgaba): Figure out what else should happen if someone has side effects
			#TODO(mgaba): Add doctors name to personalize messages
			# Send response
			return process_response(Message.STATIC_ONE_OFF)

		# d - Other
		elif response.lower() == 'd':
			#TODO(mgaba): Add doctors name to personalize messages
			return process_response(Message.OPEN_ENDED_QUESTION)

		# Unknown response
		else:
			message.datetime_responded = None
			message.save()
			template = 'messages/unknown_response.txt'
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, _type=Message.STATIC_ONE_OFF, content=content)
			return HttpResponse(content=content, content_type='text/plain')

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

		previous_message = message.previous_message
		while hasattr(previous_message, "previous_message") and previous_message.previous_message != None:
			previous_message = previous_message.previous_message

		for feedback in previous_message.feedbacks.all():
			feedback.note=response
			feedback.datetime_responded=now
			feedback.save()

		template = 'messages/response_open_ended_question.txt'
		content = render_to_string(template)
		new_m = Message.objects.create(to=sender, _type=Message.STATIC_ONE_OFF, content=content)
		return HttpResponse(content=content, content_type='text/plain')

	def process_no_recent_message_response(self, sender, response):
		if self.is_med_info(response):
			raise Exception("Not yet implemented")
		elif self.is_time_change(response):
			#TODO(mgaba): Figure out the best way to allow a user to change times (right now just an upsell)
			raise Exception("Not yet implemented")
		else:
			template = "messages/no_messages_to_reply_to.txt"
			content = render_to_string(template)
			new_m = Message.objects.create(to=sender, _type=Message.STATIC_ONE_OFF, content=content)
			return HttpResponse(content=content, content_type='text/plain')

	def process_unrequired_response(self, sender, response):
		# handles responses to messages that do not require responses
		pass

	RESPONSE_MAP = {
		Message.MEDICATION: process_medication_response,
		Message.MEDICATION_QUESTIONNAIRE: process_medication_questionnaire_response,
		Message.REFILL: process_refill_response,
		Message.REFILL_QUESTIONNAIRE: process_refill_questionnaire_response,
		Message.MED_INFO: process_med_info_response,
		Message.NON_ADHERENT: process_non_adherent_response,
		Message.NON_ADHERENT_QUESTIONNAIRE: process_non_adherent_questionnaire_response,
		Message.OPEN_ENDED_QUESTION: process_open_ended_question_response,
	}

	def process_response(self, sender, response):
		""" 
		Returns an HttpResponse object. Changes state of system based on action and sender's message
		"""
		if sender is None or (sender.did_quit() and not self._is_resume(response)):
			return self.process_invalid_response()

		# Generic logic for responding to any type of message goes here
		# if self._is_quit(response):
		# 	return self.process_quit_response(sender)
		if self._is_quit(response):
			return self.process_pause_response(sender)
		elif sender.did_quit() and self._is_resume(response):
			return self.process_resume_response(sender)

		last_sent_message = Message.objects.get_last_sent_message_requiring_response(to=sender)

		if not last_sent_message:
			return self.process_no_recent_message_response(sender, response)

		response_generator = ResponseCenter.RESPONSE_MAP.get(
			last_sent_message._type, self.process_unrequired_response)

		return response_generator(self, sender, last_sent_message, response)

