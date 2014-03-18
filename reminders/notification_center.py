from common.utilities import sendTextMessageToNumber, list_to_queryset
from common.models import UserProfile
from patients.models import PatientProfile
from reminders.models import Notification, Message, SentReminder
from configs.dev import settings
from django.template.loader import render_to_string
import datetime

class NotificationCenter(object):
	def __init__(self, interval_sec=settings.REMINDER_MERGE_INTERVAL):
		self.interval_sec = interval_sec

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
			notifications_iter = notifications.order_by("send_time", "prescription__drug__name")
			first_notification = notifications[0]
			chunks = []
			current_chunk = []
			current_chunk_endtime = first_notification.send_time + interval_sec_dt
			for notification in notifications_iter:
				if notification.send_time < current_chunk_endtime:
					current_chunk.append(notification)
				else:
					chunks.append(tuple(current_chunk))
					current_chunk = [notification]
					current_chunk_endtime = notification.send_time + interval_sec_dt
			chunks.append(tuple(current_chunk))

			return tuple(chunks)
		return

	def send_message(self, to, notifications, body=None, template=None, context=None):
		"""
		Send text message to patient <to>, where message body is a message template <template> 
		filled with values from dictionary <context>

		In future, checks performed on additional recipient features will determine whether
		the message should be sent via SMS, as a native app notification, or as a voice call.
		"""
		if notifications.__class__ == Notification:
			notifications = [notifications]

		message = Message.objects.create(patient=to, message_type=notifications[0].reminder_type)
		if context:
			context['message_number'] = message.message_number
		else:
			context = {'message_number':message.message_number}

		# send message
		if not body and template:
			body = render_to_string(template, context)

		primary_phone_number = to.primary_phone_number or to.primary_contact.primary_phone_number
		sendTextMessageToNumber(body, primary_phone_number)

		# perform necessary record-keeping and updates to sent notifications
		for notification in notifications:
			if notification.reminder_type in (Notification.REFILL, Notification.MEDICATION):
				sent_reminder = SentReminder.objects.create(reminder_time=notification, 
					message=message, prescription=notification.prescription)
				notification.update_to_next_send_time()
			elif notification.reminder_type in (Notification.WELCOME, Notification.SAFETY_NET):
				sent_reminder = SentReminder.objects.create(reminder_time=notification, message=message)
				notification.active = False
				notification.save()
			else:
				raise Exception("You probably added a new reminder_type. Must specify logic for updating after sending a message")

	def send_welcome_notifications(self, to, notifications):
		"""
		Send welcome notification in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, reminder_type=Notification.WELCOME)
		if notifications.exists() and to.status == PatientProfile.NEW:
			welcome_notification = list(notifications.order_by('send_time'))[0]
			context = {'patient_first_name':to.first_name}
			self.send_message(to=to, notifications=welcome_notification, 
				template='messages/welcome_reminder.txt', context=context)

			# officially active recipient user's account
			to.status = UserProfile.ACTIVE 
			to.save()

	def send_refill_notifications(self, to, notifications):
		"""
		Send refill notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, reminder_type=Notification.REFILL)
		if notifications.exists() and to.status == PatientProfile.ACTIVE:
			notifications = notifications.order_by('prescription__drug__name')
			notification_groups = self.merge_notifications(notifications)
			for group in notification_groups:
				context = {'reminder_list': group}
				self.send_message(to=to, notifications=group,
					template='messages/refill_reminder.txt', context=context)

	def send_medication_notifications(self, to, notifications):
		"""
		Send medication notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to,
			reminder_type=Notification.MEDICATION, prescription__filled=True)
		if notifications.exists() and to.status == PatientProfile.ACTIVE:
			notifications = notifications.order_by('prescription__drug__name')
			notification_groups = self.merge_notifications(notifications)
			for group in notification_groups:
				context = {'reminder_list': group}
				self.send_message(to=to, notifications=group,
					template='messages/medication_reminder.txt', context=context)

	def send_safetynet_notifications(self, to, notifications):
		"""
		Send safety-net notifications in QuerySet <notifications> to recipient <to>
		"""
		notifications = notifications.filter(to=to, reminder_type=Notification.SAFETY_NET)
		if notifications.exists() and to.status in (PatientProfile.NEW, PatientProfile.ACTIVE):
			notifications = notifications.order_by("send_time")
			for notification in notifications:
				self.send_message(to=to, notifications=notification, body=notification.text)

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
		self.send_safetynet_notifications(to, notifications)
