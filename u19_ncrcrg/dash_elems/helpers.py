import base64
import io
import logging
import os
import urllib

from dash import html
from minio import Minio

from .. import settings

logger = logging.getLogger(__name__)

THEME = settings.BOOTSTRAP_THEME


def get_minio_client(user, pw, endpoint=os.environ.get("MINIO_ENDPOINT")):
    return Minio(
        endpoint,
        access_key=user,
        secret_key=pw,
    )


def return_breadcrumbs_row(current=None, custom_url="#"):
    """
    current: string
        should match a label option, which underlines where a user currently is within the analysis workflow.
    """
    workflow = []
    for label, url in zip(["Upload Data", "Submit Job", "Dashboard"],
                          ["/upload-data/", "/submit-job/", "/job-status/"]):
        if current == label:
            if custom_url != "#":
                url = custom_url
            workflow.append(html.U(html.Li(html.A(label, href=url), className="breadcrumb-item")))
            workflow.append(html.Div(" > ", className='mr-2 ml-2'))
        else:
            workflow.append(html.Li(html.A(label, href=url), className="breadcrumb-item"))
            workflow.append(html.Div(" > ", className='mr-2 ml-2'))
    workflow = workflow[:-1]  # remove last caret

    return html.Div(
        [
            html.Ul(workflow, className='breadcrumb')
        ],

    )


def return_breadcrumbs_row_sharing(share_url="#", group_url="#", fm_link="#"):
    """
    current: string
        should match a label option, which underlines where a user currently is within the analysis workflow.
    custom_url: string
        IF not None, modifies the "current" step's link.
    """
    workflow = []
    for label, url in zip(
            ["Upload Data", "Create Group", "Select Folder", "Select Group"],
            ["#", "https://app.globus.org/groups", "#", "#"]
    ):
        if "Upload Data" == label:
            workflow.append(html.Li(html.A(label, href=fm_link, target="_blank"), className="breadcrumb-item"))
            workflow.append(html.Div(" > ", className='mr-2 ml-2'))
        elif "Select Folder" == label:
            workflow.append(html.Li(html.A(label, href=share_url, target="_blank"), className="breadcrumb-item"))
            workflow.append(html.Div(" > ", className='mr-2 ml-2'))
        elif "Select Group" == label:
            workflow.append(html.Li(html.A(label, href=group_url, target="_blank"), className="breadcrumb-item"))
            workflow.append(html.Div(" > ", className='mr-2 ml-2'))
        else:
            workflow.append(html.Li(html.A(label, href=url, target="_blank"), className="breadcrumb-item"))
            workflow.append(html.Div(" > ", className='mr-2 ml-2'))
    workflow = workflow[:-1]  # remove last caret

    return html.Div(
        [
            html.Ul(workflow, className='breadcrumb')
        ],

    )


def humansize(nbytes):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, suffixes[i])


def save_file(name, folder, content, user_name, pw):
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    """Decode and store a file uploaded with Plotly Dash."""
    """data = content.encode("utf8").split(b";base64,")[1]
    with open(os.path.join(UPLOAD_DIRECTORY, name), "wb") as fp:
        fp.write(base64.decodebytes(data))"""
    client = get_minio_client(user_name, pw)
    if folder is not None:
        while folder.startswith('/'):
            folder = folder[1:]
    else:
        folder = ''
    client.put_object(
        user_name, os.path.join(folder, name), io.BytesIO(decoded), -1, part_size=10 * 1024 * 1024
    )


def list_recursive(transfer_client, o, root):
    endpoint_id = settings.GLOBUS_USS_EP_ID
    ls = transfer_client.operation_ls(endpoint_id=endpoint_id, path=root)
    root_no_user = '/'.join(root.split('/')[1:], )  # basically turns bay001/some/path/ -> some/path/
    for fd in ls['DATA']:
        if fd['type'] == 'file':
            o.append(os.path.join(root_no_user, fd['name']))
        elif fd['type'] == 'dir' and fd['name'] != 'json_files':
            o.append(os.path.join(root_no_user, fd['name'] + '/'))
            list_recursive(transfer_client, o, os.path.join(str(root), fd['name'] + '/'))

    return o


def get_platform_url():
    """Provide the base url depending on the platform the app is running
        :return: url
    """
    platform = os.environ['PLATFORM']
    url = ''
    if platform == 'DEV':
        url = 'http://localhost:8000'
    elif platform == 'TST':
        url = 'https://cred-portal-test.com'
    elif platform == 'PRD':
        url = 'https://cred-portal.com'

    return url


def get_filemanager_url(username):
    base_url = f'https://{settings.GLOBUS_BASE_URL}file-manager/'
    ep_id = f'{settings.GLOBUS_USS_EP_ID}'
    url_params = urllib.parse.urlencode(
        {
            'destination_id': ep_id,
            'destination_path': username
        }
    )
    fm_link = f'{base_url}?{url_params}'
    return fm_link


def get_jupyter_filemanager_url(username):
    base_url = f'https://{settings.GLOBUS_BASE_URL}file-manager/'
    ep_id = f'{settings.GLOBUS_USS_EP_ID}'
    jp_id = f'{settings.GLOBUS_JUPYTER_EP_ID}'
    url_params = urllib.parse.urlencode(
        {
            'destination_id': jp_id,
            'destination_path': username,
            'origin_id': ep_id,
            'origin_path': username,
        }
    )
    fm_link = f'{base_url}?{url_params}'
    return fm_link


def get_example_data_url(username):
    base_url = f'https://{settings.GLOBUS_BASE_URL}file-manager/'
    ep_id = f'{settings.GLOBUS_USS_EP_ID}'
    url_params = urllib.parse.urlencode(
        {
            'origin_id': ep_id,
            'origin_path': 'share',
            'destination_id': ep_id,
            'destination_path': f"{username}/raw_files/"
        }
    )
    fm_link = f'{base_url}?{url_params}'
    return fm_link
