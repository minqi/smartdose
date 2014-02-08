from reminders.models import ReminderTime
from configs.dev import settings
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
		notifications_iter = iter(notifications.order_by("send_time"))
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

