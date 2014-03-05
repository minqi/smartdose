import datetime
from django.template.loader import render_to_string
from patients.models import PatientProfile, SafetyNetRelationship
from reminders.models import SentReminder, ReminderTime

class SafetyNetCenter(object):

	def __init__(self, 
		window=datetime.timedelta(days=7), 
		threshold=0.8, timeout=datetime.timedelta(hours=4)):
		self.window = window
		self.threshold = threshold
		self.timeout =  timeout

	def _compute_adherence_percentage_by_patients(self, window_start, window_finish, time, timeout):
		"""
		Returns a list of [patient, missed_dose] tuples for doses missed between 
		window_start and window_finish at time time. A dose is considered missed 
		if it's gone unacknowledged for longer than timeout.
		"""
		reminders = SentReminder.objects.filter(
			time_sent__gte=window_start,
			time_sent__lte=window_finish,
			reminder_time__reminder_type=ReminderTime.MEDICATION).exclude(time_sent__gte=time - timeout)
		# Cache reminder_time for quick reminder_time__reminder_type and reminder_time__patient lookup
		reminders = reminders.prefetch_related('reminder_time').prefetch_related('reminder_time__prescription')

		patients = PatientProfile.objects.all()
		if patients == None:
			return
		adherence_percentage_for_patients_list = []
		for patient in patients:
			dose_count = 0
			acked_dose_count = 0
			patient_reminders = reminders.filter(reminder_time__to=patient)
			for patient_reminder in patient_reminders:
				if patient_reminder.prescription.safety_net_on:
					dose_count += 1
					if patient_reminder.ack == True:
						acked_dose_count += 1
			if dose_count != 0:
				adherence_percentage_for_patients_list.append(
					[patient, float(acked_dose_count)/float(dose_count)])
		return adherence_percentage_for_patients_list

	def _schedule_safety_net_messages_from_adherence_percentage_list(self, 
		adherence_percentage_by_patients_list, threshold):
		"""
		Schedules notifications to safety net members.
		threshold is a threshold we use to calculate the cutoff of the adherence message to a patient
		"""
		if adherence_percentage_by_patients_list == None:
			return

		for adherence_percentage_by_patient in adherence_percentage_by_patients_list:
			patient = adherence_percentage_by_patient[0]
			adherence_percentage = adherence_percentage_by_patient[1]
			# render prescriptions to template
			dictionary = {
			'adherence_percentage':adherence_percentage*100, #Multiply by 100 for formatting in the template
			'threshold':threshold*100, #Multiply by 100 for comparing with adherence_percentage
			'patient_first':patient.first_name,
			'patient_gender':patient.gender
			}
			safety_net_contacts = patient.safety_net_contacts.all()
			for safety_net_contact in safety_net_contacts:
				dictionary['patient_relationship'] = \
					SafetyNetRelationship.objects.get(source_patient=patient, 
						target_patient=safety_net_contact).target_to_source_relationship
				message_body = render_to_string('messages/safety_net_message.txt', dictionary)
				ReminderTime.objects.create_safety_net_notification(to=safety_net_contact, text=message_body)

	def schedule_safety_net_messages(self, window_start, window_finish, threshold, timeout):
		"""
		Schedules a message to a safety net member to notify about missed doses. 
		Safety net member will be notified of the number of
		doses missed between window_start and window_finish. 
		A medication is considered not taken if it has gone
		unacknowledged for longer than timeout. threshold is 0 <= threshold <= 1 (e.g. .8) 
		and represents the cutoff between adherence and non adherence
		"""
		if threshold < 0 or threshold > 1:
			raise Exception("0 <= threshold <= 1 must be true")

		adherence_percentage_by_patients_list = \
			self._compute_adherence_percentage_by_patients(
				window_start, window_finish, datetime.datetime.now(), timeout)

		self._schedule_safety_net_messages_from_adherence_percentage_list(
			adherence_percentage_by_patients_list, threshold)
