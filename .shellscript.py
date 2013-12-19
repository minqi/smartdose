from celery import task
from django.template.loader import render_to_string
from reminders.models import NextReminderPointer
from common.utilities import sendTextMessage
from reminders.tasks import sendOneReminder
from patients.models import PatientProfile
from datetime import datetime,timedelta
from django.conf import settings
from reminders.models import Message
from reminders.models import SentReminder
from MessageReminderRelationship
from datetime import datetime
from reminders.tasks import REMINDER_INTERVAL





"""
REMINDER_INTERVAL = 10000

now = datetime.now()
earliest_reminder = now - timedelta(days=REMINDER_INTERVAL)
latest_reminder = now + timedelta(days=REMINDER_INTERVAL)

reminders_for_now_list = NextReminderPointer.objects.select_related('prescription__patient').filter(send_time__gte=earliest_reminder, send_time__lte=latest_reminder)
patients_list = reminders_for_now_list.values_list('prescription__patient__primary_phone_number', flat=True).distinct()
for patient in patients_list:
	p = PatientProfile.objects.get(primary_phone_number=patient)
	p_pills = reminders_for_now_list.filter(prescription__patient__primary_phone_number=patient)
	sendOneReminder(p, p_pills, False)
"""
#matts_pills = reminders_for_now_list.filter(prescription__patient__primary_phone_number=patients_list[1].values()[0])
#print patients_list[1].values()[0]
#print matts_pills

