import codecs
from django.test import TestCase
from common.models import UserProfile, Drug
from django.test import Client
from doctors.models import DoctorProfile
from freezegun import freeze_time
from patients.models import PatientProfile
from reminders.models import Notification, Prescription, Message, Feedback
from reminders import tasks as reminder_tasks
from common.utilities import SMSLogger
from configs.dev import settings
import datetime

class TestHelper():
	@staticmethod
	def advance_test_time_to_end_time_and_emulate_reminder_periodic_task(test, end_time, period):
		""" Advance test.current_time to end_time running sendRemindersForNow every period, where period is a timedelta object
		"""
		while test.current_time < end_time:
			reminder_tasks.sendRemindersForNow()
			test.current_time = test.current_time + period
			test.freezer = freeze_time(test.current_time)
			test.freezer.start()

class EndToEndScenariosTest(TestCase):
	def setUp(self):
		self.vitamin = Drug.objects.create(name="vitamin")
		self.bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",
		                                        primary_phone_number="2029163381",
		                                        username="2029163381",
		                                        birthday=datetime.date(year=1960, month=10, day=20),
		                                        address_line1="4262 Cesar Chavez", postal_code="94131",
		                                        city="San Francisco", state_province="CA", country_iso_code="US")
		# Set the time the test should begin
		self.current_time = datetime.datetime(year=2013, month=10, day=13, hour=11, minute=0)
		self.freezer = freeze_time(self.current_time)
		self.freezer.start()
		self.client = Client()
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = codecs.open(settings.MESSAGE_LOG_FILENAME, 'w', settings.SMS_ENCODING) # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close()
	def tearDown(self):
		self.freezer.stop()

	# 1. Patient is enrolled in Smartdose
	# 2. Patient picks up prescriptions from pharmacy
	# 3. Patient takes first med with no problem
	# 4. Patient forgets second med because he hasn't gotten the chance.
	# 5. He waits an hour and then takes it when he gets the second reminder
	def scenario_one(self):
		# Simulate enrolling the patient
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                           primary_phone_number="8569067308",
		                                           birthday=datetime.date(year=1990, month=4, day=21),
		                                           gender=PatientProfile.MALE,
		                                           address_line1="4266 Cesar Chavez",
		                                           postal_code="94131",
		                                           city="San Francisco", state_province="CA", country_iso_code="US")
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong")
		welcome_delivery_time = self.current_time + datetime.timedelta(hours=3)
		notification_schedule = [[Notification.DAILY, welcome_delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=minqi,
																		  prescription=prescription,
																		  notification_schedule=notification_schedule)
		Notification.objects.create(to=minqi, type=Notification.WELCOME, repeat=Notification.NO_REPEAT,
		                            send_datetime=welcome_delivery_time, enroller=self.bob)

		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, welcome_delivery_time,
		                                                                            datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		reminder_tasks.sendRemindersForNow()
		# There should have been 3 messages delivered: two welcome messages and a refill message
		messages = SMSLogger.getLastNSentMessages(3)
		expected_message_1 = "Hi, Minqi! Dr. Watcher is giving you Smartdose to improve your medication experience. "+\
							 "You can reply 'q' at any time to quit."
		self.assertEqual(messages[0]['datetime_sent'], welcome_delivery_time)
		self.assertEqual(messages[0]['to'], minqi.primary_phone_number)
		self.assertEqual(messages[0]['content'], expected_message_1)
		expected_message_2 = "Smartdose sends you simple medicine reminders, making it easy to take the right dose " \
		                     "at the right time.\n\n" \
		                     "For more info, you can visit www.smartdo.se"
		self.assertEqual(messages[1]['datetime_sent'], welcome_delivery_time)
		self.assertEqual(messages[1]['to'], minqi.primary_phone_number)
		self.assertEqual(messages[1]['content'], expected_message_2)
		expected_message_3 = "Have you picked up your new meds from the pharmacy? Reply:\n" \
		                     "y - yes\n" \
		                     "n - no\n\n" \
		                     "To see your meds reply m."
		self.assertEqual(messages[2]['datetime_sent'], welcome_delivery_time)
		self.assertEqual(messages[2]['to'], minqi.primary_phone_number)
		self.assertEqual(messages[2]['content'], expected_message_3)

		# Minqi responds 'y' to the message five minutes later
		five_minutes_later = self.current_time + datetime.timedelta(minutes=5)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, five_minutes_later, datetime.timedelta(minutes=1))

		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':'y' })
		expected_response = "Great. You'll receive your first reminder tomorrow at 2:00pm. To change the time of your " \
		                    "reminder, visit smartdo.se/1234567890/r?c=12345"
		self.assertEqual(response.content, expected_response)

		# Advance to 2:00pm the following day to see if we make good on our promise to Minqi.
		first_reminder_delivery_time = datetime.datetime.combine(self.current_time.date() + datetime.timedelta(days=1),
																 datetime.time(hour=14))
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, first_reminder_delivery_time,
		                                                                            datetime.timedelta(minutes=5))
		self.assertEqual(SMSLogger.getLastSentMessage()['datetime_sent'], welcome_delivery_time)
		reminder_tasks.sendRemindersForNow()
		# There should be a medication reminder for Minqi.
		medication_reminder = SMSLogger.getLastSentMessage()
		expected_message_4 = "Time to take your:\n" \
		                     "Vitamin\n\n" \
		                     "Did you take it?\n" \
		                     "y - yes\n" \
		                     "n - no\n\n" \
		                     "To see med info reply m."
		self.assertEqual(medication_reminder['datetime_sent'], first_reminder_delivery_time)
		self.assertEqual(medication_reminder['to'], minqi.primary_phone_number)
		self.assertEqual(medication_reminder['content'], expected_message_4)
		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':'y' })
		expected_response_fragment = "happy you're taking care"
		self.assertIn(expected_response_fragment, response.content)

		# Advance to 2:00pm the following day for the next reminder
		second_reminder_delivery_time = datetime.datetime.combine(self.current_time.date() + datetime.timedelta(days=1),
		                                                         datetime.time(hour=14))
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, second_reminder_delivery_time,
		                                                                            datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage()['datetime_sent'], first_reminder_delivery_time)
		reminder_tasks.sendRemindersForNow()
		# There should be a medication reminder for Minqi.
		medication_reminder = SMSLogger.getLastSentMessage()
		expected_message_4 = "Time to take your:\n" \
		                     "Vitamin\n\n" \
		                     "Did you take it?\n" \
		                     "y - yes\n" \
		                     "n - no\n\n" \
		                     "To see med info reply m."
		self.assertEqual(medication_reminder['datetime_sent'], second_reminder_delivery_time)
		self.assertEqual(medication_reminder['to'], minqi.primary_phone_number)
		self.assertEqual(medication_reminder['content'], expected_message_4)
		# He says he didn't take it and gets a response
		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':'n' })
		expected_response_fragment = "Why not?"
		self.assertIn(expected_response_fragment, response.content)
		# He says the reason was he didn't get the chance (a)
		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':'a' })
		expected_response_fragment = "No problem. We'll send you another reminder in an hour."
		self.assertEqual(expected_response_fragment, response.content)

		# He should get a reminder an hour later
		followup_reminder_delivery_time = second_reminder_delivery_time + datetime.timedelta(hours=1)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, followup_reminder_delivery_time,
		                                                                            datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage()['datetime_sent'], second_reminder_delivery_time)
		reminder_tasks.sendRemindersForNow()
		medication_reminder = SMSLogger.getLastSentMessage()
		expected_message_5 = "Time to take your:\n" \
		                     "Vitamin\n\n" \
		                     "Did you take it?\n" \
		                     "y - yes\n" \
		                     "n - no\n\n" \
		                     "To see med info reply m."
		self.assertEqual(medication_reminder['datetime_sent'], followup_reminder_delivery_time)
		self.assertEqual(medication_reminder['to'], minqi.primary_phone_number)
		self.assertEqual(medication_reminder['content'], expected_message_5)
		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':'y' })
		expected_response_fragment = "happy you're taking care"
		self.assertIn(expected_response_fragment, response.content)

		# Now let's go to the next day to be sure the reminder is sent at the correct time.
		third_reminder_delivery_time = second_reminder_delivery_time + datetime.timedelta(days=1)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, third_reminder_delivery_time,
		                                                                            datetime.timedelta(minutes=10))
		print(SMSLogger.getLastSentMessage()['content'])
		self.assertEqual(SMSLogger.getLastSentMessage()['datetime_sent'], followup_reminder_delivery_time)
		reminder_tasks.sendRemindersForNow()
		medication_reminder = SMSLogger.getLastSentMessage()
		expected_message_6 = "Time to take your:\n" \
		                     "Vitamin\n\n" \
		                     "Did you take it?\n" \
		                     "y - yes\n" \
		                     "n - no\n\n" \
		                     "To see med info reply m."
		self.assertEqual(medication_reminder['datetime_sent'], third_reminder_delivery_time)
		self.assertEqual(medication_reminder['to'], minqi.primary_phone_number)
		self.assertEqual(medication_reminder['content'], expected_message_6)

		# And once more, to be sure the followup isn't lingering
		fourth_reminder_delivery_time = third_reminder_delivery_time + datetime.timedelta(days=1)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, fourth_reminder_delivery_time,
		                                                                            datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage()['datetime_sent'], third_reminder_delivery_time)
		reminder_tasks.sendRemindersForNow()
		medication_reminder = SMSLogger.getLastSentMessage()
		expected_message_6 = "Time to take your:\n" \
		                     "Vitamin\n\n" \
		                     "Did you take it?\n" \
		                     "y - yes\n" \
		                     "n - no\n\n" \
		                     "To see med info reply m."
		self.assertEqual(medication_reminder['datetime_sent'], fourth_reminder_delivery_time)
		self.assertEqual(medication_reminder['to'], minqi.primary_phone_number)
		self.assertEqual(medication_reminder['content'], expected_message_6)

	# 1. Patient is enrolled in Smartdose
	# 2. Patient does not pick up medication because his car broke down
	# 3. Patient reports that his car broke down
	def scenario_two(self):
		# Simulate enrolling the patient
		minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                      primary_phone_number="8569067308",
		                                      birthday=datetime.date(year=1990, month=4, day=21),
		                                      gender=PatientProfile.MALE,
		                                      address_line1="4266 Cesar Chavez",
		                                      postal_code="94131",
		                                      city="San Francisco", state_province="CA", country_iso_code="US")
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong")
		welcome_delivery_time = self.current_time + datetime.timedelta(hours=3)
		notification_schedule = [[Notification.DAILY, welcome_delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=minqi,
		                                                                                  prescription=prescription,
		                                                                                  notification_schedule=notification_schedule)
		Notification.objects.create(to=minqi, type=Notification.WELCOME, repeat=Notification.NO_REPEAT,
		                            send_datetime=welcome_delivery_time, enroller=self.bob)

		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, welcome_delivery_time,
		                                                                            datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		reminder_tasks.sendRemindersForNow()
		# There should have been 3 messages delivered: two welcome messages and a refill message
		messages = SMSLogger.getLastNSentMessages(3)
		expected_message_1 = "Hi, Minqi! Dr. Watcher is giving you Smartdose to improve your medication experience. "+ \
		                     "You can reply 'q' at any time to quit."
		self.assertEqual(messages[0]['datetime_sent'], welcome_delivery_time)
		self.assertEqual(messages[0]['to'], minqi.primary_phone_number)
		self.assertEqual(messages[0]['content'], expected_message_1)
		expected_message_2 = "Smartdose sends you simple medicine reminders, making it easy to take the right dose " \
		                     "at the right time.\n\n" \
		                     "For more info, you can visit www.smartdo.se"
		self.assertEqual(messages[1]['datetime_sent'], welcome_delivery_time)
		self.assertEqual(messages[1]['to'], minqi.primary_phone_number)
		self.assertEqual(messages[1]['content'], expected_message_2)
		expected_message_3 = "Have you picked up your new meds from the pharmacy? Reply:\n" \
		                     "y - yes\n" \
		                     "n - no\n\n" \
		                     "To see your meds reply m."
		self.assertEqual(messages[2]['datetime_sent'], welcome_delivery_time)
		self.assertEqual(messages[2]['to'], minqi.primary_phone_number)
		self.assertEqual(messages[2]['content'], expected_message_3)

		# Minqi responds 'n' to the message five minutes later
		five_minutes_later = self.current_time + datetime.timedelta(minutes=5)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, five_minutes_later, datetime.timedelta(minutes=1))

		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':'n' })
		expected_response = "Why not? Reply:\n" \
		                    "a - Haven't gotten the chance\n" \
		                    "b - Too expensive\n" \
		                    "c - Concerned about side effects\n" \
		                    "d - Other"
		self.assertEqual(response.content, expected_response)
		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':'d' })
		expected_response = "Please tell us more. We'll pass it along to your doctor."
		self.assertEqual(response.content, expected_response)
		response = self.client.get('/textmessage_response/', {'From': minqi.primary_phone_number, 'Body':"My car broke down, so I won't be able to go for the next three days" })
		expected_response = "Thanks for sharing. We'll pass it along to your doctor."
		self.assertEqual(response.content, expected_response)
		feedback = Feedback.objects.filter(prescription=prescription)
		self.assertEqual(feedback[0].note, "My car broke down, so I won't be able to go for the next three days")



class ReminderDeliveryTest(TestCase):
	def setUp(self):
		self.vitamin = Drug.objects.create(name="vitamin")
		self.bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",
		                                        primary_phone_number="2029163381",
		                                        username="2029163381",
		                                        birthday=datetime.date(year=1960, month=10, day=20),
		                                        address_line1="4262 Cesar Chavez", postal_code="94131",
		                                        city="San Francisco", state_province="CA", country_iso_code="US")
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                           primary_phone_number="8569067308",
		                                           birthday=datetime.date(year=1990, month=4, day=21),
		                                           gender=PatientProfile.MALE,
		                                           address_line1="4266 Cesar Chavez",
		                                           postal_code="94131",
		                                           city="San Francisco", state_province="CA", country_iso_code="US")
		# Set the time the test should begin
		self.current_time = datetime.datetime(year=2013, month=10, day=13, hour=11, minute=0)
		self.freezer = freeze_time(self.current_time)
		self.freezer.start()
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = codecs.open(settings.MESSAGE_LOG_FILENAME, 'w', settings.SMS_ENCODING) # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close()
	def tearDown(self):
		self.freezer.stop()

	# Test that a refill reminder is delivered daily.
	def test_daily_delivery(self):
		# Minqi is signed up for his daily vitamin reminder. He'll receive refill reminders
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong")
		expected_delivery_time = self.current_time + datetime.timedelta(hours=3)
		notification_schedule = [[Notification.DAILY, expected_delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=self.minqi,
		                                                                          prescription=prescription,
		                                                                          notification_schedule=notification_schedule)
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		# Emulate the scheduler task and make sure no reminders are sent
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now expected_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Advance time by a day
		old_delivery_time = expected_delivery_time
		expected_delivery_time = expected_delivery_time + datetime.timedelta(hours=24)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		# Make sure no reminders were sent in that time
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now expected_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

	# Test that a prescription reminder is delivered bi-weekly.
	def test_biweekly_delivery(self):
		# Minqi is signed up for his biweekly vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           filled=True) # Mark as filled to receive medication reminders
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		sunday_delivery_time = self.current_time + datetime.timedelta(hours=3)
		tuesday_delivery_time = sunday_delivery_time + datetime.timedelta(days=2)
		notification_schedule = [[Notification.WEEKLY, sunday_delivery_time], [Notification.WEEKLY, tuesday_delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=self.minqi,
		                                                                          prescription=prescription,
		                                                                          notification_schedule=notification_schedule)
		# Test the first weeks worth of messages
		# Emulate the scheduler task and make sure no reminders are sent
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, sunday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now sunday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], sunday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Next sunday's delivery time is a week away
		old_delivery_time = sunday_delivery_time
		sunday_delivery_time = sunday_delivery_time + datetime.timedelta(weeks=1)
		# Advance to tuesday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, tuesday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now tuesday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], tuesday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

		# Test the second weeks worth of messages
		# Next Tuesday's delivery time is a week away, so increment
		old_delivery_time = tuesday_delivery_time
		tuesday_delivery_time = tuesday_delivery_time + datetime.timedelta(weeks=1)
		# Advance to second week, sunday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, sunday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now sunday_delivery_time, so make sure the reminder is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], sunday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Advance to tuesday_delivery_time
		old_delivery_time = sunday_delivery_time
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, tuesday_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# This time, we should send the message at the appropriate time
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], tuesday_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

	# Test that a prescription reminder is delivered monthly
	def test_monthly_delivery(self):
		# Minqi is signed up for his daily vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           filled=True) # Mark as filled to avoid refill reminders
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		expected_delivery_time = self.current_time + datetime.timedelta(hours=3)
		notification_schedule = [[Notification.MONTHLY, expected_delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=self.minqi,
																			  prescription=prescription,
																			  notification_schedule=notification_schedule)
		# Test the first months message
		# Emulate the scheduler task and make sure no reminders are sent
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now expected_delivery_time, so make sure the message is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Advance to next month
		old_delivery_time = expected_delivery_time
		# First reminder is sent on 10/13/2013. Second reminder will be sent a month later on 11/13/2013
		expected_delivery_time = datetime.datetime.combine(datetime.date(year=2013, month=11, day=13), expected_delivery_time.time())
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, expected_delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(message['datetime_sent'], old_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		# Time is now expected_delivery_time, so make sure the message is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], expected_delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)

	# Test the behavior after a user says "n" to a med reminder and answers a questionnaire
	def test_medication_reminder_and_questionnaire_response(self):
		# Minqi is signed up for his daily vitamin reminder
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           filled=True,
		                                           note="To make you strong")
		delivery_time = self.current_time + datetime.timedelta(hours=3)
		notification_schedule = [[Notification.DAILY, delivery_time]]
		(refill_reminder, reminder_times) = \
			Notification.objects.create_prescription_notifications_from_notification_schedule(
				to=self.minqi,
				prescription=prescription,
				notification_schedule=notification_schedule)
		# Mark Minqi as active so that he can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		# Emulate the scheduler task and make sure no reminders are sent until it's time to send a reminder
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, delivery_time, datetime.timedelta(hours=1))
		self.assertEqual(SMSLogger.getLastSentMessage(), None)
		# Time is now expected_delivery_time, so make sure the message is sent
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		expected_content = "Time to take your:\n"+\
						   "Vitamin\n\n"+\
						   "Did you take it?\n"+\
						   "y - yes\n"+\
						   "n - no\n\n"+\
						   "To see med info reply m."


		self.assertEqual(message['datetime_sent'], delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		self.assertEqual(message['content'], expected_content)

		# Send a no response and get back a questionnaire
		c = Client()
		response = c.get('/textmessage_response/', {'From': self.minqi.primary_phone_number, 'Body': 'n'})
		expected_content = "Why not? Reply:\n" \
		                    "a - Haven't gotten the chance\n" \
		                    "b - Need to refill\n" \
		                    "c - Side effects\n" \
		                    "d - Meds don't work\n" \
		                    "e - Prescription changed\n" \
		                    "f - I feel sad :(\n" \
		                    "g - Other"
		self.assertEqual(response.content, expected_content)

		# Send an "a" response and get back a message
		response = c.get('/textmessage_response/', {'From': self.minqi.primary_phone_number, 'Body': 'a'})
		expected_content = "No problem. We'll send you another reminder in an hour."
		self.assertEqual(response.content, expected_content)

		# Advance an hour to see if the message gets sent
		delivery_time = delivery_time + datetime.timedelta(hours=1)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, delivery_time, datetime.timedelta(hours=1))
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		expected_content = "Time to take your:\n"+ \
		                   "Vitamin\n\n"+ \
		                   "Did you take it?\n"+ \
		                   "y - yes\n"+ \
		                   "n - no\n\n"+ \
		                   "To see med info reply m."
		self.assertEqual(message['datetime_sent'], delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_phone_number)
		self.assertEqual(message['content'], expected_content)

	def test_primary_contact_delivery(self):
		# create a primary contact
		primary_contact = PatientProfile.objects.create(
			full_name='Test User', primary_phone_number='+10000000000')

		# create patient with primary contact
		self.minqi.primary_phone_number = ''
		self.minqi.primary_contact = primary_contact

		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong")
		delivery_time = self.current_time + datetime.timedelta(hours=1)
		notification_schedule = [[Notification.DAILY, delivery_time]]
		(refill_reminder, reminder_times) = \
			Notification.objects.create_prescription_notifications_from_notification_schedule(
				to=self.minqi,
				prescription=prescription,
				notification_schedule=notification_schedule)
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, delivery_time, datetime.timedelta(hours=1))
		reminder_tasks.sendRemindersForNow()
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['datetime_sent'], delivery_time)
		self.assertEqual(message['to'], self.minqi.primary_contact.primary_phone_number)


class TestSafetyNetDelivery(TestCase):
	def setUp(self):
		self.vitamin = Drug.objects.create(name="vitamin")
		self.bob = DoctorProfile.objects.create(first_name="Bob", last_name="Watcher",
		                                        primary_phone_number="2029163381",
		                                        username="2029163381",
		                                        birthday=datetime.date(year=1960, month=10, day=20),
		                                        address_line1="4262 Cesar Chavez", postal_code="94131",
		                                        city="San Francisco", state_province="CA", country_iso_code="US")
		self.minqi = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                           primary_phone_number="8569067308",
		                                           birthday=datetime.date(year=1990, month=4, day=21),
		                                           gender=PatientProfile.MALE,
		                                           address_line1="4266 Cesar Chavez",
		                                           postal_code="94131",
		                                           city="San Francisco", state_province="CA", country_iso_code="US")

		self.minqis_safety_net = PatientProfile.objects.create(
			first_name='Jianna', last_name='Jiang', primary_phone_number='1234567890')
		self.minqi.add_safety_net_contact(
			target_patient=self.minqis_safety_net, relationship='mother')
		self.no_safety_net_patient = PatientProfile.objects.create(first_name="Minqi", last_name="Jiang",
		                                           primary_phone_number="8569067301",
		                                           birthday=datetime.date(year=1990, month=4, day=21),
		                                           gender=PatientProfile.MALE,
		                                           address_line1="4266 Cesar Chavez",
		                                           postal_code="94131",
		                                           city="San Francisco", state_province="CA", country_iso_code="US")
		self.current_time = datetime.datetime(year=2013, month=10, day=13, hour=11, minute=0)
		self.freezer = freeze_time(self.current_time)
		self.freezer.start()
		settings.MESSAGE_LOG_FILENAME="test_message_output"
		f = codecs.open(settings.MESSAGE_LOG_FILENAME, 'w', settings.SMS_ENCODING) # Open file with 'w' permission to clear log file. Will get created in logging code when it gets written to.
		f.close()
		self.client = Client()
	def tearDown(self):
		self.freezer.stop()

	# Test the case where Minqi goes a week without acknowledging his medication
	def test_nonadherent_message(self):
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           safety_net_on=True,
		                                           filled=True)
		delivery_time = self.current_time + datetime.timedelta(hours=3)
		# Mark patients as active so that they can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		self.minqis_safety_net.status = PatientProfile.ACTIVE
		self.minqis_safety_net.save()
		notification_schedule = [[Notification.WEEKLY, delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=self.minqi,
																		  prescription=prescription,
																		  notification_schedule=notification_schedule)
		safety_net_notification_time = delivery_time + datetime.timedelta(weeks=1)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, safety_net_notification_time, datetime.timedelta(days=1))
		reminder_tasks.schedule_safety_net_messages()
		reminder_tasks.sendRemindersForNow()

		safety_net_message_content = "Your son, Minqi, has had trouble with his medicine this week. He's reported taking 0% of his meds. Maybe you should give him a call?"
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['to'], self.minqis_safety_net.primary_phone_number)
		self.assertEqual(message['content'], safety_net_message_content)

	# Test the case where Minqi goes a week and acknowledges every message
	def test_adherent_message(self):
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           safety_net_on=True,
		                                           filled=True)
		delivery_time = self.current_time + datetime.timedelta(hours=3)
		# Mark patients as active so that they can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		self.minqis_safety_net.status = PatientProfile.ACTIVE
		self.minqis_safety_net.save()
		notification_schedule = [[Notification.DAILY, delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=self.minqi,
																		  prescription=prescription,
																		  notification_schedule=notification_schedule)
		safety_net_notification_time = delivery_time + datetime.timedelta(weeks=1)
		while (safety_net_notification_time > self.current_time):
			TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, self.current_time + datetime.timedelta(days=1), datetime.timedelta(days=1))
			reminder_tasks.sendRemindersForNow()
			self.client.get('/textmessage_response/', {'From': self.minqi.primary_phone_number, 'Body': 'y'})
		reminder_tasks.schedule_safety_net_messages()
		reminder_tasks.sendRemindersForNow()

		safety_net_message_content = "Great news - your son, Minqi, has been taking care this week. He's reported taking 100% of his meds."
		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message['to'], self.minqis_safety_net.primary_phone_number)
		self.assertEqual(message['content'], safety_net_message_content)

	# Test the case where Minqi goes a week and gets no reminders
	def test_no_reminder_message(self):
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.minqi,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           safety_net_on=True,
		                                           filled=True)
		delivery_time = self.current_time + datetime.timedelta(weeks=4)
		# Mark patients as active so that they can receive reminders
		self.minqi.status = PatientProfile.ACTIVE
		self.minqi.save()
		self.minqis_safety_net.status = PatientProfile.ACTIVE
		self.minqis_safety_net.save()
		notification_schedule = [[Notification.MONTHLY, delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=self.minqi,
																		  prescription=prescription,
																		  notification_schedule=notification_schedule)
		safety_net_notification_time = self.current_time + datetime.timedelta(weeks=1)
		TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, safety_net_notification_time, datetime.timedelta(days=1))
		reminder_tasks.schedule_safety_net_messages()
		reminder_tasks.sendRemindersForNow()

		message = SMSLogger.getLastSentMessage()
		self.assertEqual(message, None)

	# Test the case where a patient has no safety net. Be sure the safety net does not get contacted
	def test_reminders_to_no_safety_net(self):
		prescription = Prescription.objects.create(prescriber=self.bob,
		                                           patient=self.no_safety_net_patient,
		                                           drug=self.vitamin,
		                                           note="To make you strong",
		                                           safety_net_on=True,
		                                           filled=True)
		delivery_time = self.current_time + datetime.timedelta(hours=3)
		# Mark patients as active so that they can receive reminders
		self.no_safety_net_patient.status = PatientProfile.ACTIVE
		self.no_safety_net_patient.save()
		notification_schedule = [[Notification.DAILY, delivery_time]]
		Notification.objects.create_prescription_notifications_from_notification_schedule(to=self.no_safety_net_patient,
																		  prescription=prescription,
																		  notification_schedule=notification_schedule)
		safety_net_notification_time = delivery_time + datetime.timedelta(weeks=1)
		while (safety_net_notification_time > self.current_time):
			TestHelper.advance_test_time_to_end_time_and_emulate_reminder_periodic_task(self, self.current_time + datetime.timedelta(days=1), datetime.timedelta(days=1))
			reminder_tasks.sendRemindersForNow()
			self.client.get('/textmessage_response/', {'From': self.minqi.primary_phone_number, 'Body': 'y'})
		reminder_tasks.schedule_safety_net_messages()
		reminder_tasks.sendRemindersForNow()

		safety_net_message_content = "Great news - your son, Minqi, has been taking care this week. He's reported taking 100% of his meds."
		message = SMSLogger.getLastSentMessage()
		self.assertNotEqual(message['to'], self.minqis_safety_net.primary_phone_number)
		self.assertNotEqual(message['content'], safety_net_message_content)
