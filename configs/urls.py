from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'webapp.views.landing', name='landing'),
    url(r'^early_signup/$', 'webapp.views.early_signup'),
    url(r'^textmessage_response/$', 'reminders.views.handle_text'),

    # Fishfood URLs
    url(r'^fishfood/$', 'webapp.views.fishfood'),
    url(r'^fishfood/dashboard/$', 'webapp.views.dashboard'),
    url(r'^fishfood/login/$', 'webapp.views.user_login'),
    url(r'^fishfood/signup/$', 'webapp.views.user_registration'),
    url(r'^fishfood/signup/verifymobile/$', 'webapp.views.verify_mobile'),
    url(r'^fishfood/logout/$', 'webapp.views.user_logout'),  
	url(r'^fishfood/patients/search/$', 'webapp.views.patient_search_results'),
    url(r'^fishfood/patients/new/$', 'webapp.views.create_patient'),
    url(r'^fishfood/patients/$', 'webapp.views.retrieve_patient', name="retrieve_patient"),
    url(r'^fishfood/patients/caregivers/$', 'webapp.views.retrieve_patient', name="retrieve_caregivers"),
    url(r'^fishfood/patients/update/$', 'webapp.views.update_patient'),
    url(r'^fishfood/patients/delete/$', 'webapp.views.delete_patient'),
    url(r'^fishfood/reminders/new/$', 'webapp.views.create_reminder'),
    url(r'^fishfood/reminders/delete/$', 'webapp.views.delete_reminder'),
    url(r'^fishfood/patients/create_safety_net_contact/$', 'webapp.views.create_safety_net_contact'),
    url(r'^fishfood/patients/delete_safety_net_contact/$', 'webapp.views.delete_safety_net_contact'),
    url(r'^fishfood/patients/adherence_history_csv/$', 'reminders.views.adherence_history_csv'),
)
