from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'webapp.views.landing_page', name='landing'),
    url(r'^textmessage_response/$', 'reminders.views.handle_text'),

    # Fishfood URLs
    url(r'^fishfood/$', 'webapp.views.fishfood'),
	url(r'^fishfood/patients/search/$', 'webapp.views.patient_search_results'),
    url(r'^fishfood/patients/new/$', 'webapp.views.create_patient'),
    url(r'^fishfood/patients/$', 'webapp.views.retrieve_patient', name="retrieve_patient"),
    url(r'^fishfood/patients/delete/$', 'webapp.views.delete_patient'),
    url(r'^fishfood/reminders/new/$', 'webapp.views.create_reminder'),
    url(r'^fishfood/reminders/delete/$', 'webapp.views.delete_reminder'),
)
