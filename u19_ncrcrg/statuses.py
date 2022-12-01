#!/usr/bin/env python

STATUS_MESSAGES = {
    'QUEUED': {'status': 'Queued.', 'progress': 1},
    'SUBMITDOWNLOAD': {'status': 'Submitting download job', 'progress': 10},
    'DOWNLOADING': {'status': 'Downloading.', 'progress': 15},
    'FINISHDOWNLOAD': {'status': 'Finished downloading, ready to run.', 'progress': 25},
    'FAILEDDOWNLOAD': {'status': 'Failed download.', 'progress': 100},
    'SUBMITTED': {'status': 'Submitted.', 'progress': 30},
    'FAILEDSUBMISSION': {'status': 'Failed submission.', 'progress': 100},
    'RUNNING': {'status': 'Running.', 'progress': 50},
    'CLEANING': {'status': 'Cleaning up.', 'progress': 80},
    'DOWNLOADCOMPLETE': {'status': 'Download complete!', 'progress': 100},
    'COMPLETE': {'status': 'Complete!', 'progress': 100},
    'FAILED': {'status': 'Failed', 'progress': 100},
    'URL': {'status': '', 'progress': 50}
}


def get_message(key, custom_msg=None):
    return STATUS_MESSAGES[key]['status'] if custom_msg is None else custom_msg


def get_progress(message):
    if message.startswith('http'):
        return 50
    for code, status in STATUS_MESSAGES.items():
        if message == status['status']:
            return status['progress']
    return 50