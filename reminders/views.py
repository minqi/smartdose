import csv, random, datetime, json
from django.db.models import Q

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string

from patients.models import PatientProfile
from reminders.models import Feedback, Message
from reminders.response_center import ResponseCenter

def handle_text(request):
	try:
		patient = PatientProfile.objects.get(primary_phone_number=request.GET['From'])
	except:
		patient = None
	rc = ResponseCenter()
	return rc.process_response(patient, request.GET['Body'])

@login_required
def adherence_history_csv(request):
	if request.method == 'GET':
		AVG_RATE = .60
		headers = [
			'date',
			'adherence_rate',
		]
		response = HttpResponse(content_type='text/csv')
		csv_writer = csv.DictWriter(response, headers, extrasaction='ignore')
		csv_writer.writeheader()

		current_datetime = datetime.datetime(2012, 12, 31)
		dt = datetime.timedelta(days=1)
		adherence_count = 0
		for i in range(100):
			current_datetime += dt
			gain = 1 if random.random() < AVG_RATE else 0 
			adherence_count += gain
			data = {
				'date':current_datetime.strftime('%e-%b-%y').strip(),
				'adherence_rate':float(adherence_count)/(i+1),
			}
			csv_writer.writerow(data)
		response.content = response.content.strip('\r\n')

		return response

@login_required
def medication_response_counts(request):
	if request.method == 'GET':
		# Sort medication questionnaire responses to be in the order the user sees them
		sorted_keys = sorted(Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY, key=lambda key: key)
		counts = []
		for key in sorted_keys:
			counts.append(Feedback.objects.filter(note__iexact=Message.MEDICATION_QUESTIONNAIRE_RESPONSE_DICTIONARY[key]).distinct("message").count())

		# COMMENT FOR PROD
		# counts = [25, 25, 25, 25, 25, 25, 25]
		# gain = [int(15*random.random()) for i in xrange(7)]
		# counts = [x + y for x, y in zip(counts, gain)]
		# END COMMENT FOR PROD

		return HttpResponse(json.dumps(counts))

@login_required
#TODO(mgaba): Clean up this function after YC
def new_activity_for_activity_feed(request):
	if request.method == 'GET':
		latest_id = int(request.GET.get('latest_activity_feed_item'))
		activity = []
		messages = Message.objects.filter((Q(_type=Message.MEDICATION_QUESTIONNAIRE) | Q(_type=Message.REFILL_QUESTIONNAIRE)) & Q(id__gt=latest_id)).\
			           exclude(datetime_responded=None).order_by("datetime_responded")
		for message in messages:
			if not message.feedbacks.all():
				continue
			if message.feedbacks.all()[0].note == "Haven't gotten the chance":
				reason = "not getting the chance"
			elif message.feedbacks.all()[0].note == "Need to refill":
				reason = "needing to refill"
			elif message.feedbacks.all()[0].note == "Side effects":
				reason = "side effects"
			elif message.feedbacks.all()[0].note == "Meds don't work":
				reason = "meds aren't working correctly"
			elif message.feedbacks.all()[0].note == "Prescription changed":
				reason = "prescription changed"
			elif message.feedbacks.all()[0].note == "I feel sad :(":
				reason = "feeling sad"
			elif message.feedbacks.all()[0].note == "Other":
				reason = "other"
			context = {'patient_first_name': message.to.first_name,
			           'patient_last_name': message.to.last_name,
			           'feedback_list': message.feedbacks.all(),
			           'reason': reason}
			activity_string = render_to_string('fishfood/activity_feed_messages/generic_activity_feed_message.txt',
			                                   context)
			context = {'number': message.to.primary_phone_number}
			fancy_phone_number = render_to_string('fishfood/activity_feed_messages/phone_number_in_activity_feed.txt',
			                                   context)
			context = {'datetime':message.datetime_responded}
			formatted_date = render_to_string('fishfood/activity_feed_messages/date_in_activity_feed.txt',
			                                   context)
			activity_item = {'id':message.id,
			                 'number':fancy_phone_number,
			                 'activity_string':activity_string,
			                 'datetime':formatted_date}
			activity.append(activity_item)
		return HttpResponse(json.dumps(activity))

