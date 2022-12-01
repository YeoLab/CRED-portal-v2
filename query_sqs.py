import django
import logging
import re
from django.conf import settings
import threading

from django.core.mail import send_mail
from u19_ncrcrg.apps.experiment_viewer.services import get_current_job_status, set_current_job_status
from u19_ncrcrg.apps.metadata_api.services import get_all_experiments

"""
This is a hack until I can get around to setting up celery.
Uses a cron job to run this script, which parses all 
experiments within the last 30 days, and sends emails to
the ones that are Complete or Failed.
"""
NOTIFY_USERS_JOB_STATUS = ['Complete!', 'Failed.', ]
logger = logging.getLogger(__name__)
settings.configure()
django.setup()


def get_experiments():
    threads = []
    # Set this process up as a daemon
    while True:
        for experiment in get_all_experiments(past=30):
            if experiment['user'] == 'public':
                pass
            else:

                try:
                    # Create multiple threads for the job status polling process
                    experiment_name = experiment['aggr_nickname']
                    t = threading.Thread(target=get_job_status, args=(experiment_name, experiment,))
                    threads.append(t)
                    t.start()

                except Exception as e:
                    logger.info(f'This is the error {str(e)}')


def get_job_status(experiment_name, experiment):
    thread_lock = threading.Lock()
    try:
        contact_email = experiment['contact_email']
        status, last_update_time = get_current_job_status(experiment_name)
        if 'Unknown queue' in status:
            status = 'Pending'
        elif 'Running' in status:
            try:
                status = status.split(':', 1)[1]
            # The h5ad file may be created successfully, but the URL may not be created
            except IndexError:
                status = 'Running, URL Not Available'
        if re.match('^Complete!', status) or re.match('^Failed', status):
            thread_lock.acquire()
            try:
                send_mail(
                    'Job {}'.format(experiment_name),
                    'Hello, you are receiving an update for this job: {}'.format(status),
                    'ncrcrg.u19@gmail.com',
                    [contact_email]
                )
                set_current_job_status(experiment_name, 'Done ({}) - email sent.'.format(status))
            finally:
                thread_lock.release()
    except Exception as e:
        logger.info(f'An error occurred in setting queue status {str(e)}')


if __name__ == '__main__':

    get_experiments()

