from django.http import HttpResponse

def landing_page(request):
	return HttpResponse(content="STAY TUNED", content_type="text/plain")
