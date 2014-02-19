from patients.models import PatientProfile
from reminders.response_center import ResponseCenter

def handle_text(request):
	try:
		patient = PatientProfile.objects.get(primary_phone_number=request.GET['from'])
	except:
		patient = None
	rc = ResponseCenter()
	action = rc.parse_message_to_action(patient, request.GET['body'])
	return rc.render_response_from_action(action, patient, request.GET['body'])


