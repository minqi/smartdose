SMARTDOSE

1. Setting up the environment

- Set up virtualenv by running "source .make_virtualenv" and you're good to go.
- Note that manage is now set as an alias for "python $(pwd)/configs/dev/manage.py".
- E.g. to launch a local Django server, simply call "manage runserver"


RUNNING ON EC2

Managing Postgresql:
sudo -u postgres psql

Start rabbitmq-server:
sudo rabbitmq-server -detached

Run a celery worker with embedded beat scheduler:
celery -A celery_app worker -B -l info &

Kill all celery workers
ps auxww | grep 'celery_app worker' | awk '{print $2}' | xargs kill -9

Running gunicorn:
gunicorn common.wsgi:application

Restart nginx:
service nginx restart
