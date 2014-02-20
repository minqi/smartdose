from django.conf.urls import patterns, include, url
from webapp.views import FishfoodPatientView

urlpatterns = patterns('',
    url(r'^$', 'webapp.views.landing_page', name='landing'),
    url(r'^textmessage_response/', 'reminders.views.handle_text'),

    # Fishfood URLs
    url(r'^fishfood/$', 'webapp.views.fishfood'),
	url(r'^fishfood/patient/search/$', 'webapp.views.patient_search_results'),
    url(r'^fishfood/patient/new/$', FishfoodPatientView.as_view()),
    url(r'^fishfood/patient/', FishfoodPatientView.as_view()),
)
