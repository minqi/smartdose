import csv, random, datetime

from django.http import HttpResponse

from patients.models import PatientProfile
from reminders.response_center import ResponseCenter

def handle_text(request):
	try:
		patient = PatientProfile.objects.get(primary_phone_number=request.GET['From'])
	except:
		patient = None
	rc = ResponseCenter()
	action = rc.parse_message_to_action(patient, request.GET['Body'])
	return rc.render_response_from_action(action, patient, request.GET['Body'])


def adherence_history_csv(request):
	if request.GET:
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
			adherence_count += random.randint(0,1)
			data = {
				'date':current_datetime.strftime('%e-%b-%y').strip(),
				'adherence_rate':float(adherence_count)/(i+1),
			}
			csv_writer.writerow(data)
		response.content = response.content.strip('\r\n')

		return response