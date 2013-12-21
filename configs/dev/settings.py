# Django settings for smartdose project.
from __future__ import absolute_import
import djcelery
from celery.schedules import crontab


DEBUG = False
TEMPLATE_DEBUG = DEBUG
SEND_TEXT_MESSAGES = True

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
    ('minqi', 'mnqjng@gmail.com'),
    ('matt', 'matthew.gaba.2@gmail.com'),
    ('pasha', 'pnahass@gmail.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'smartdose_db',
        'USER': 'smartdose_dev',
        'PASSWORD': 'cesarchavez',
        'HOST': 'localhost',  
        'PORT': '',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.

USE_TZ = True
if DEBUG == True:
    USE_TZ = False;

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'qiv+zydik$p!57te+byjb=*vqmgchib018*d0s309^a(6^b^3d'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'configs.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'common.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #TODO(mgaba): How do we make this general?
    "/Users/matthewgaba/smartdose/smartdose"
)

INSTALLED_APPS = (
    # django apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    # smartdose apps
    'common',
    'doctors',
    'patients',
    'reminders',

    # external apps
    'djcelery',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# Account Sid and Auth Token from twilio.com/user/account
TWILIO_ACCOUNT_SID = "AC31efceab15417e2e544393253ecd31fc"
TWILIO_AUTH_TOKEN = "e315c85df8ca8b54b954a9145fca481c"
TWILIO_NUMBER =  "+16179368157"

MESSAGE_LOG_FILENAME="message_output"

# Celery settings
# To get celery to work, you will need to install a Rabbitmq server: see http://docs.celeryproject.org/en/latest/getting-started/brokers/rabbitmq.html#installing-rabbitmq-on-os-x
# After installing the rabbitmq server, begin running the server with the following command
# >sudo rabbitmq-server
# Now that rabbitmq-server is running, we'll need to setup our celery worker and celery scheduler.
# To setup the celery worker, run the following command from the smartdose home directory
# >manage celery worker
# To setup the celery schedule, run the following command from the smartdose home directory
# >manage celery beat
# Now celery beat will schedule tasks that are consumed by the celery worker.

djcelery.setup_loader() 
# Celery message broker identifying URL
# TODO(mgaba) Setup appropriate URL for server and figure out how 
#   the server stuff will work in productiion
BROKER_URL = 'amqp://guest:guest@localhost:5672' 
CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
CELERYBEAT_SCHEDULE = {
    'send-reminders': {
        'task' : 'reminders.tasks.sendRemindersForNow',
        'schedule': crontab(minute='0,15,30,45')
    }
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}
