import csv, random, datetime, json

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from patients.models import PatientProfile
from reminders.models import Feedback
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
		counts = []
		for response in ('A', 'B', 'C', 'D', 'E', 'F', 'G'):
			counts.append(Feedback.objects.filter(note__iexact=response).count())

		# COMMENT FOR PROD
		counts = [25, 25, 25, 25, 25, 25, 25]
		gain = [int(15*random.random()) for i in xrange(7)]
		counts = [x + y for x, y in zip(counts, gain)]
		# END COMMENT FOR PROD

		return HttpResponse(json.dumps(counts))
