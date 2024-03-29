import datetime, itertools

from django.template.loader import render_to_string

from configs.dev import settings
from common.utilities import sendTextMessageToNumber, list_to_queryset
from common.models import UserProfile
from patients.models import PatientProfile, SafetyNetRelationship
from reminders.models import Notification, Message, Feedback


class NotificationCenter(object):

	def __init__(self, interval_sec=settings.REMINDER_MERGE_INTERVAL):
		self.interval_sec = interval_sec

	@staticmethod
	def get_cutoff_datetime():
		now = datetime.datetime.now()
		return now - datetime.timedelta(hours=settings.MESSAGE_CUTOFF_HOURS)

	def merge_notifications(self, notifications, interval_sec=None):
		"""
		Merge Notification objects <notifications> into <interval> chunks;
		Returns a tuple of tuples, where each sub-tuple consists of 
		notifications falling within the same chunk.
		"""
		if not interval_sec:
			interval_sec = self.interval_sec

		interval_sec_dt = datetime.timedelta(seconds=interval_sec)
		if notifications.exists():
			notifications_iter = notifications.order_by("send_datetime")
			first_notification = notifications[0]
			chunks = []
			current_chunk = []
			current_chunk_endtime = first_notification.send_datetime + interval_sec_dt
			for notification in notifications_iter:
				if notification.send_datetime < current_chunk_endtime:
					current_chunk.append(notification)
				else:
					chunks.append(tuple(current_chunk))
					current_chunk = [notification]
					current_chunk_endtime = notification.send_datetime + interval_sec_dt
			chunks.append(tuple(current_chunk))

			return tuple(chunks)
		return

	def resend_text_message(self, to, message):
		"""
		Resend a previously sent message <message> to patient <to>.
		"""
		# Perform record keeping in DB
		new_message = Message.objects.create(to=to, _type=message._type, content=message.content, previous_message=message,
		                                     nth_message_of_day_of_type=message.nth_message_of_day_of_type)
		notifications = message.notifications.all()
		for notification in notifications:
			new_message.notifications.add(notification)
		for feedback in message.feedbacks.all():
			new_message.feedbacks.add(feedback)

		# send message
		primary_phone_number = to.primary_phone_number or to.primary_contact.primary_phone_number
		cutoff_datetime = NotificationCenter.get_cutoff_datetime()
		if not [n for n in notifications if n.send_datetime < cutoff_datetime]:
			sendTextMessageToNumber(message.content, primary_phone_number)

		return

	def send_text_message(self, to, notifications, template=None, context=None, body=None):
		"""
		Send text message to patient <to>, where message body is a message template <template>
		filled with values from dictionary <context>
		"""
		# Initialize function
		if body is None:
			if template is None or context is None:
				raise Exception("Must supply template and context to send_text_message if no body")
		if notifications.__class__ == Notification:
			notifications = [notifications]

		# compose message
		if body is None:
			body = render_to_string(template, context)
		primary_phone_number = to.primary_phone_number or to.primary_contact.primary_phone_number

		# Perform record keeping in DB
		_type = notifications[0]._type
		message = Message.objects.create(to=to, _type=_type, content=body)
		for one_notification in notifications:
			message.notifications.add(one_notification)
			one_notification.update_to_next_send_time()
			if Feedback.is_valid_type(_type):
				feedback = Feedback.objects.create(_type=_type,
												   prescription=one_notification.prescription,
												   notification=one_notification)
				message.feedbacks.add(feedback)

		cutoff_datetime = NotificationCenter.get_cutoff_datetime()
		if not [n for n in notifications if n.send_datetime < cutoff_datetime]:
			sendTextMessageToNumber(body, primary_phone_number)

		return

	def send_refill_notifications(self, to, notifications):
		"""
		Send refill notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, _type=Notification.REFILL)
		if not notifications.exists() or to.status != PatientProfile.ACTIVE:
			return

		notification_groups = self.merge_notifications(notifications)

		for notification_group in notification_groups:
			# Construct content of message
			template = 'messages/refill_message.txt'
			def get_drug_name(notification):
				return notification.prescription.drug.name
			prescription_names = sorted(list(itertools.imap(get_drug_name, notification_group)))
			context = {'prescription_name_list': prescription_names,
			           'times_sent': notification_group[0].times_sent}
			self.send_text_message(to=to, notifications=notification_group, template=template, context=context)

	def send_medication_notifications(self, to, notifications):
		"""
		Send medication notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, _type=Notification.MEDICATION) \
			.exclude(prescription__filled=False)
		if not notifications.exists() or to.status != PatientProfile.ACTIVE:
			return

		notifications = notifications.order_by('prescription__drug__name')
		notification_groups = self.merge_notifications(notifications)

		for notification_group in notification_groups:
			# Construct content of message
			template = 'messages/medication_message.txt'
			def get_drug_name(notification):
				return notification.prescription.drug.name.capitalize()
			prescription_names = sorted(list(itertools.imap(get_drug_name, notification_group)))
			context = {'prescription_name_list': prescription_names}
			self.send_text_message(to=to, notifications=notification_group, template=template, context=context)

	def send_welcome_notifications(self, to, notifications):
		"""
		Send welcome notification in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, _type=Notification.WELCOME)
		if not notifications.exists() or to.status != PatientProfile.NEW:
			return
		notification = notifications[0]

		# Construct message 1 and send
		if to.enroller == None:
			enroller = None
		elif hasattr(to.enroller, "doctorprofile"):
			enroller = "Dr. " + to.enroller.last_name
		else:
			enroller = to.enroller.first_name + " " + to.enroller.last_name
		context = {'patient_first_name':to.first_name,
		           'enroller':enroller}
		template = 'messages/welcome_message_1.txt'
		self.send_text_message(to=to, notifications=notification, template=template, context=context)

		# Construct message 2 and send
		template = 'messages/welcome_message_2.txt'
		self.send_text_message(to=to, notifications=notification, template=template, context=context)

		# Update DB
		to.status = UserProfile.ACTIVE
		to.save()

	def send_safety_net_notifications(self, to, notifications):
		"""
		Send safety-net notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, _type=Notification.SAFETY_NET)

		if not notifications.exists() or to.status != PatientProfile.ACTIVE:
			return

		notifications = notifications.order_by("send_datetime")
		for notification in notifications:
			# Construct content of message
			self.send_text_message(to=to, notifications=notification, body=notification.content)

	def send_safety_net_welcome_notifications(self, to, notifications):
		"""
		Send a welcome safety-net notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, _type=Notification.SAFETY_NET_WELCOME)

		if not notifications.exists():
			return

		for notification in notifications:
			safety_nets = SafetyNetRelationship.objects.filter(target_patient=to, source_patient=notification.patient_of_safety_net)
			if not safety_nets:
				raise Exception("Sending safety net welcome notification to someone without a safety net")
			relationship = safety_nets[0].target_to_source_relationship
			context = {'patient_first_name': notification.patient_of_safety_net.first_name,
			           'patient_gender': notification.patient_of_safety_net.gender,
			           'patient_relationship': relationship,
			           'safety_net_first_name': to.first_name,}

			template = 'messages/safety_net_welcome_message_1.txt'
			self.send_text_message(to=to, notifications=notification, template=template, context=context)

			# Construct message 2 and send
			template = 'messages/safety_net_welcome_message_2.txt'
			self.send_text_message(to=to, notifications=notification, template=template, context=context)

			# Construct message 3 and send
			template = 'messages/safety_net_welcome_message_3.txt'
			self.send_text_message(to=to, notifications=notification, template=template, context=context)

	def send_static_one_off_notifications(self, to, notifications):
		"""
		Send safety-net notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, _type=Notification.STATIC_ONE_OFF)

		if not notifications.exists() or to.status != PatientProfile.ACTIVE:
			return

		notifications = notifications.order_by("send_datetime")
		for notification in notifications:
			# Construct content of message
			self.send_text_message(to=to, notifications=notification, body=notification.content)

	def send_repeat_message_notifications(self, to, notifications):
		"""
		Send repeat message notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, _type=Notification.REPEAT_MESSAGE)

		if not notifications.exists() or to.status != PatientProfile.ACTIVE:
			return

		notifications = notifications.order_by("send_datetime")
		for notification in notifications:
			notification.active = False
			notification.save()
			self.resend_text_message(to=to, message=notification.message)

	def send_notifications(self, to, notifications):
		"""
		Send Notifications QuerySet <notifications> to recipient <to>
		"""
		if to.status == PatientProfile.QUIT:
			return

		# if notifications is a list or single notification object, 
		# convert into QuerySet
		if isinstance(notifications, [].__class__):
			notifications = list_to_queryset(notifications)
		elif isinstance(notifications, Notification):
			notifications = list_to_queryset([notifications])

		self.send_welcome_notifications(to, notifications)
		self.send_refill_notifications(to, notifications)
		self.send_medication_notifications(to, notifications)
		self.send_safety_net_notifications(to, notifications)
		self.send_safety_net_welcome_notifications(to, notifications)
		self.send_static_one_off_notifications(to, notifications)
		self.send_repeat_message_notifications(to, notifications)
