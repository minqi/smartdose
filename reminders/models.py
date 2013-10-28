from django.db import models
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from common.models import Drug
from datetime import datetime, timedelta


class Prescription(models.Model):
	"""Model for prescriptions"""
	prescriber     		= models.ForeignKey(DoctorProfile, blank=False)
	patient        		= models.ForeignKey(PatientProfile, blank=False)
	drug           		= models.ForeignKey(Drug, blank=False)
	with_food      		= models.BooleanField(default=False)
	with_water     		= models.BooleanField(default=False)
	last_edited    		= models.DateTimeField(auto_now=True)
	note		  		= models.CharField(max_length=300)
	reminders_sent 		= models.PositiveIntegerField(default=0)
	safety_net_on		= models.BooleanField(default=False)

# Returns a query_set containing all of the reminders occuring within a
# predefined offset from datetime.now()
# WIP
# TODO: Hook up manager to Reminder model. Test with fake data.
"""
class RemindersForNowManager(models.Manager):
	def get_query_set(self):
		now = datetime.now()
		offset = 10
		earliest_reminder = now.replace(minute=now.minute-offset)
		latest_reminder = now.replace(minute=now.minute+offset)

		return super(RemindersForNowManager, self).get_query_set()
						.filter(send_time > earliest_reminder, 
								send_time < latest_reminder)
"""

#TODO(mgaba): Write code that will create this next reminder pointer when a prescription is created
class NextReminderPointer(models.Model):
	"""Model for a pointer to the next reminder"""
	# repeat choices
	DAILY   = 'd'
	WEEKLY  = 'w'
	MONTHLY = 'm'
	YEARLY  = 'y'
	CUSTOM  = 'c'
	REPEAT_CHOICES = (
		(DAILY,   'daily'),
		(WEEKLY,  'weekly'),
		(MONTHLY, 'monthly'),
		(YEARLY,  'yearly'),
		(CUSTOM,  'custom'),
	)

	prescription = models.ForeignKey(Prescription, blank=False)
	repeat       = models.CharField(max_length=2,
							        choices=REPEAT_CHOICES,
							        default=DAILY)
	send_time    = models.DateTimeField(blank=False)
	reminder_num = models.PositiveIntegerField(blank=False)

	def incrementSendTime(self):
		current_send_time = self.send_time
		if self.repeat == NextReminderPointer.DAILY:
			self.send_time += timedelta(days=1)
		elif self.repeat == NextReminderPointer.WEEKLY:
			self.send_time += timedelta(days=7)
		elif self.repeat == NextReminderPointer.MONTHLY:
			self.send_time += timedelta(weeks=4)
		elif self.repeat == NextReminderPointer.YEARLY:
			#TODO(mgaba): Account for leap years
			self.send_time += timedelta(days=365)
		self.save()

class SentReminder(models.Model):
	"""Model for reminders that have been sent"""
	prescription 			= models.ForeignKey(Prescription, blank=False)
	time_sent    			= models.DateTimeField(auto_now_add=True)
	# set this equal to the reminder_num of corresponding Reminder
	reminder_num 			= models.PositiveIntegerField(blank=False)
	ack 					= models.BooleanField(default=False)
	contacted_safety_net 	= models.BooleanField(default=False)

class Message(models.Model):
	"""Model for messages that have been sent to users"""
	patient 					= models.ForeignKey(PatientProfile, blank=False)
	time_sent					= models.DateTimeField(auto_now_add=True)

class MessageReminderRelationship(models.Model):
	"""Model that connects messages that have been sent to patients with the reminders"""
	"""contained in that message. 													  """
	sent_reminder			= models.ForeignKey(SentReminder, blank=False, null=False)
	message 				= models.ForeignKey(Message, blank=False, null=False)
