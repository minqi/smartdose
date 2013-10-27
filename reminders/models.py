from django.db import models
from doctors.models import DoctorProfile
from patients.models import PatientProfile
from common.models import Drug
from datetime import datetime


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


class Reminder(models.Model):
	"""Model for reminders yet to be sent"""
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

class LiveReminder(models.Model):
	"""Model for live reminders that have been sent and that
	are not yet ACKed or expired"""
	prescription = models.ForeignKey(Prescription, blank=False)
	time_sent    = models.DateTimeField(auto_now_add=True)
	# set this equal to the reminder_num of corresponding Reminder
	reminder_num = models.PositiveIntegerField(blank=False)


class CompletedReminder(models.Model):
	"""Model for completed reminders that have been sent and
	ACKed or expired"""
	prescription = models.ForeignKey(Prescription, blank=False)
	time_sent    = models.DateTimeField(blank=False)
	ack          = models.BooleanField(default=False)

	# set this equal to the reminder_num of corresponding Reminder
	reminder_num = models.PositiveIntegerField(blank=False)