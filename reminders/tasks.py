# Tasks that will be executed by Celery.
from celery import task
from reminders.models import Reminder

# Example task that adds two numbers
# @task()
# def add(x, y):
#  	return x + y

"""
@task()
def sendRemindersNow():
	reminders_to_send = Reminder.objects.remindersForNow()

	for reminder_to_send in reminders_to_send:
		reminder_to_send.sendReminder()
"""