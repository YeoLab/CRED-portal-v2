"""
Utility functions

Copyright (c) 2018 Gibbs Consulting and others - see CONTRIBUTIONS.md

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import base64
import json
from uuid import uuid4
import logging

import boto3
import globus_sdk
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.module_loading import import_string
# from omero.gateway import BlitzGateway
from social_core.pipeline.user import USER_FIELDS
from social_core.utils import slugify, module_member
from .accounts.views import get_globus_https_server, get_https_token
import os
from u19_ncrcrg.accounts.views import setup_uss_env
import pymongo
import requests
from botocore.config import Config
import ssl
import urllib
from .dash_elems.job_status import add_new_experiment_to_project
from .accounts.views import access_omero_server

logger = logging.getLogger(__name__)


def _get_settings():
    try:
        the_settings = settings.PLOTLY_DASH
    except AttributeError:
        the_settings = None

    return the_settings if the_settings else {}


def pipe_ws_endpoint_name():
    '''Return the endpoint for pipe websocket connections'''
    return _get_settings().get('ws_route', 'dpd/ws/channel')


def dpd_http_endpoint_root():
    '''Return the root of the http endpoint for direct insertion of pipe messages'''
    return _get_settings().get('http_route', 'dpd/views')


def http_endpoint(stem):
    'Form the http endpoint for a specific stem'
    return "^%s/%s/$" % (dpd_http_endpoint_root(), stem)


def insert_demo_migrations():
    'Check settings and report if objects for demo purposes should be inserted during migration'

    return _get_settings().get('insert_demo_migrations', False)


def http_poke_endpoint_enabled():
    'Return true if the http endpoint is enabled through the settings'
    return _get_settings().get('http_poke_enabled', True)


def cache_timeout_initial_arguments():
    'Return cache timeout, in seconds, for initial arguments'
    return _get_settings().get('cache_timeout_initial_arguments', 60)


def initial_argument_location():
    'Return True if cache to be used for setting and getting initial arguments, or False for a session'

    setget_location = _get_settings().get('cache_arguments', True)

    return setget_location


def store_initial_arguments(request, initial_arguments=None):
    'Store initial arguments, if any, and return a cache identifier'

    if initial_arguments is None:
        return None

    # convert to dict is json string
    if isinstance(initial_arguments, str):
        initial_arguments = json.loads(initial_arguments)

    # Generate a cache id
    cache_id = "dpd-initial-args-%s" % str(uuid4()).replace('-', '')

    # Store args in json form in cache
    if initial_argument_location():
        cache.set(cache_id, initial_arguments, cache_timeout_initial_arguments())
    else:
        request.session[cache_id] = initial_arguments

    return cache_id


def get_initial_arguments(request, cache_id=None):
    'Extract initial arguments for the dash app'

    if cache_id is None:
        return None

    if initial_argument_location():
        return cache.get(cache_id)

    return request.session[cache_id]


def static_asset_root():
    return _get_settings().get('static_asset_root', 'dpd/assets')


def full_asset_path(module_name, asset_path):
    path_contrib = "%s/%s/%s" % (static_asset_root(),
                                 "/".join(module_name.split(".")),
                                 asset_path)
    return path_contrib


def static_asset_path(module_name, asset_path):
    return static_path(full_asset_path(module_name, asset_path))


def serve_locally():
    return _get_settings().get('serve_locally', False)


def static_path(relative_path):
    try:
        static_url = settings.STATIC_URL
    except:
        pass
        static_url = '/static/'
    return "%s%s" % (static_url, relative_path)


def stateless_app_lookup_hook():
    'Return a function that performs lookup for aa stateless app, given its name, or returns None'

    func_name = _get_settings().get('stateless_loader', None)
    if func_name:
        func = import_string(func_name)
        return func

    # Default is no additional lookup
    return lambda _: None


def load_portal_client():
    """Create an AuthClient for the portal
        :params None
        :return a Globus ConfidentialAppAuthClient object
    """
    return globus_sdk.ConfidentialAppAuthClient(
        settings.SOCIAL_AUTH_GLOBUS_KEY, settings.SOCIAL_AUTH_GLOBUS_SECRET)


def get_username(strategy, details, backend, user=None, *args, **kwargs):
    if 'username' not in backend.setting('USER_FIELDS', USER_FIELDS):
        return
    storage = strategy.storage
    # hack for existing users that do not fit into this registration process
    og_users = get_og_users()

    if not user:
        email_as_username = strategy.setting('USERNAME_IS_FULL_EMAIL', True)
        uuid_length = strategy.setting('UUID_LENGTH', 16)
        max_length = storage.user.username_max_length()
        do_slugify = strategy.setting('SLUGIFY_USERNAMES', True)
        do_clean = strategy.setting('CLEAN_USERNAMES', False)

        def identity_func(val):
            return val

        if do_clean:
            override_clean = strategy.setting('CLEAN_USERNAME_FUNCTION')
            if override_clean:
                clean_func = module_member(override_clean)
            else:
                clean_func = storage.user.clean_username
        else:
            clean_func = identity_func

        if do_slugify:
            override_slug = strategy.setting('SLUGIFY_FUNCTION')
            if override_slug:
                slug_func = module_member(override_slug)
            else:
                slug_func = slugify
        else:
            slug_func = identity_func

        og_user = False
        og_username = ''
        email = details.get('email', None)
        for og_email in og_users.keys():
            if og_email == email:
                og_user = True
                og_username = og_users[og_email]

        if og_user:
            username = og_username
        elif email_as_username and details.get('email') and not og_user:
            username = details['email']
        elif details.get('username') and not og_user:
            username = details['username']
        else:
            username = uuid4().hex

        # this takes the user's email and drops the domain name before slugifying
        trim_username = username.split('@')
        new_username = trim_username[0]

        short_username = (new_username[:max_length - uuid_length]
                          if max_length is not None
                          else new_username)
        final_username = slug_func(clean_func(new_username[:max_length]))

        # Generate a unique username for current user using username
        # as base but adding a unique hash at the end. Original
        # username is cut to avoid any field max_length.
        # The final_username may be empty and will skip the loop.

        if not og_user:
            while not final_username or storage.user.user_exists(
                    username=final_username
            ):
                username = short_username + uuid4().hex[:uuid_length]
                final_username = slug_func(clean_func(username[:max_length]))
    else:
        final_username = storage.user.get_username(user)
    return {'username': final_username}


def user_details(strategy, details, backend, user=None, *args, **kwargs):
    """Update user details using data from provider."""
    if not user:
        return
    # this is the only override of this pipeline method. it provisions new users with a
    # directory strucure on the USS
    setup_uss_env(user)
    changed = False  # flag to track changes

    # Default protected user fields (username, id, pk and email) can be ignored
    # by setting the SOCIAL_AUTH_NO_DEFAULT_PROTECTED_USER_FIELDS to True
    if strategy.setting('NO_DEFAULT_PROTECTED_USER_FIELDS') is True:
        protected = ()
    else:
        protected = ('username', 'id', 'pk', 'email', 'password',
                     'is_active', 'is_staff', 'is_superuser',)

    protected = protected + tuple(strategy.setting('PROTECTED_USER_FIELDS', []))

    # Update user model attributes with the new data sent by the current
    # provider. Update on some attributes is disabled by default, for
    # example username and id fields. It's also possible to disable update
    # on fields defined in SOCIAL_AUTH_PROTECTED_USER_FIELDS.
    field_mapping = strategy.setting('USER_FIELD_MAPPING', {}, backend)
    for name, value in details.items():
        # Convert to existing user field if mapping exists
        name = field_mapping.get(name, name)
        if value is None or not hasattr(user, name) or name in protected:
            continue

        current_value = getattr(user, name, None)
        if current_value == value:
            continue

        immutable_fields = tuple(strategy.setting('IMMUTABLE_USER_FIELDS', []))
        if name in immutable_fields and current_value:
            continue

        changed = True
        setattr(user, name, value)

    if changed:
        strategy.storage.user.changed(user)


def get_og_users():
    """
    Returns a dictionary containing all current active users
    {user.email:user.username}
    """
    User = get_user_model()
    users = User.objects.all()
    og_users = {}
    for user in users:
        og_users[user.email] = user.username
    return og_users


def create_job(job_metadata, request, submitter=None):  # TODO: validate form and return a message.
    """
    Main function to create/kickoff a job on TSCC. This function wraps:

    Saving job_metadata (as json) onto TSCC (json_files/)
    insert_new_experiment(): inserts new experiment document into mongodb's "experiments" db
    insert_new_project(): if the specified 'project' does not exist in mongodb, create one.
    add_new_experiment_to_project(): inserts a new experiment document into mongodb's "projects" db
    create_job_queue(): creates an SQS queue

    Returns 0 iff ALL of the above execute without raising errors, 1 otherwise.
    """
    sqs_access_key_id = os.environ.get("SQS_ACCESS_KEY_ID")
    sqs_secret_access_key = os.environ.get("SQS_SECRET_ACCESS_KEY")
    config = Config(s3={"use_accelerate_endpoint": True})
    errors = []

    try:
        logger.debug("SUBMITTING TO QUEUE")
        sqs = boto3.resource(
            'sqs',
            aws_access_key_id=sqs_access_key_id,
            aws_secret_access_key=sqs_secret_access_key,  # noqa
            config=config,
            region_name="us-west-1"
        )

        try:
            user = request.user
            username = user.username
        except AttributeError:
            username = submitter

        endpoint_id = settings.GLOBUS_USS_EP_ID
        https_server = get_globus_https_server(endpoint_id)
        bvalue = base64.b64encode(
            bytes(json.dumps(job_metadata, indent=4, separators=(',', ':'), default=str), 'utf-8'))
        decoded = base64.b64decode(bvalue)

        # open file to stream out
        transfer_url = f'{https_server}/{username}/json_files/{job_metadata["aggr_nickname"]}.json'

        https_token = None
        try:
            https_token = get_https_token(endpoint_id)
        except Exception as e:
            logger.debug(f'\n\nThe exception is {e}\n\n')

        header = {"Authorization": f"Bearer {https_token}"}
        response = requests.put(transfer_url, data=decoded, headers=header, allow_redirects=False)
        logger.info(f'RESPONSE: \n\n{response.text} -- {header}\n\n')
        insert_new_experiment(job_metadata)
        insert_new_project({
            "project_name": job_metadata['project'],
            "description": "default",
            "user": username,
            "tags": ["CREDV2"],
            "removed": 0,
            "trashed": "no",
        })
        add_new_experiment_to_project(job_metadata, job_metadata['project'], username)
        create_job_queue(
            username=username,
            experiment_name=job_metadata['aggr_nickname'],
            sqs=sqs
        )
        return 0
    except Exception as ie:
        errors.append(ie)
        logger.error(ie)
        return 1


def connect_mongodb(database, user, password):
    client = pymongo.MongoClient(
        "mongodb+srv://{}:{}@cluster0-hcum8.mongodb.net/test?retryWrites=true".
            format(urllib.parse.quote_plus(user),
                   urllib.parse.quote_plus(password)),
        ssl=True,
        ssl_cert_reqs=ssl.CERT_NONE
    )
    return client[database]


db = connect_mongodb(database='u19', user=bytes(settings.MONGODB_USER, 'utf-8'),
                     password=bytes(settings.MONGODB_PASSWORD, 'utf-8'))


def insert_new_experiment(experiment_record):
    """
    INSERTING A NEW EXPERIMENT RECORD INITIATED BY THE CREATE EXPERIMENT MODAL
    :param experiment_record: The Experiment Object being inserted
    :return True/False: Return True if the record is inserted successfully
    """

    try:

        db['Experiments'].insert_one(experiment_record)
        return 0
    except Exception as e:
        logger.error(e)
        raise


def create_job_queue(username, experiment_name, sqs):
    """
    Creates an SQS queue (FIFO) whose name matches experiment_name.
    """
    boto3.setup_default_session(region_name='us-west-1')
    queue = sqs.create_queue(QueueName=(experiment_name + '.fifo'),
                             Attributes={
                                 'FifoQueue': 'true',
                                 'ContentBasedDeduplication': 'true',
                                 # Max is 14 days
                                 'MessageRetentionPeriod': '1209600',
                             })
    queue.send_message(
        MessageBody='Queued.',
        MessageGroupId=(username + ':' + experiment_name),
        MessageAttributes={
            'Status': {
                'StringValue': 'Queued.',
                'DataType': 'String'
            },
        },
    )


def insert_new_project(project_record):
    """
    INSERTING A NEW PROJECT RECORD INITIATED BY THE CREATE PROJECT MODAL
    :param project_record: The JSON POST data containing the project name,
    description, and tags
    :return True/False: Return True if the record is inserted successfully
    """
    # Add some extra fields to the record that weren't populated by the form
    try:
        if db.Projects.find_one({"project_name": project_record['project_name'], "user": project_record["user"]}):
            logger.debug("Project found, not creating a new one.".format(project_record['project_name']))
            return True
        else:
            db.Projects.insert_one(project_record)
            return True
    except:  # noqa
        return False


# def get_omero_objects(omero_id):
#     """
#     Get the list of OMERO images from the OMERO server
#     :param omero_id: The OMERO accession number
#     :return omero_list: The list containing tuples of OMERO images names and paths
#     """
#     omero_id = str(omero_id)
#     omero_list = []
#     conn_list = access_omero_server(user=settings.OMERO_USER)
#     omero_id = str(omero_id).split('.')
#
#     try:
#         with BlitzGateway(conn_list[0], conn_list[1], host=conn_list[2], port=conn_list[3], secure=True) as conn:
#             for objects in conn.getObjects('Project', attributes={'id': omero_id[0]}):
#                 for dataset in objects.listChildren():
#                     for image in dataset.listChildren():
#                         path = None
#                         fileset = image.getFileset()
#                         for file in fileset.listFiles():
#                             path = file.getPath()
#                         omero_list.append({'id': image.id, 'name': image.name, 'path': path+'/'+image.name})
#
#     except Exception as e:
#         logger.error('Omero server connection error ', e)
#         return False
#
#     return omero_list

