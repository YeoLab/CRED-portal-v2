import json
import re

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output, State
from django_plotly_dash import DjangoDash

from .helpers import *
from .navbars import navbar_authenticated
from .. import settings
from ..accounts.views import get_admin_client
from ..settings import GLOBUS_USS_EP_ID, CRED_BASE_URL

logger = logging.getLogger(__name__)

THEME = settings.BOOTSTRAP_THEME

share_app = DjangoDash('ShareDataApp', external_stylesheets=[settings.BOOTSTRAP_THEME])


def share_data(user, path, group_name, my_groups):
    share_app.layout = return_page_layout(user, path, group_name, my_groups)

    return share_app


def return_page_layout(username, path, group_name, my_groups):
    """Layout for the File sharing page.
    :param username: string representation of the logged in Globus user
    :param path: list of paths representating folders to be shared (eg. ['/myuser/folder1/', ...]
    :param group_name: string of the group
    :param my_groups: list of dictionaries containing a user's group information.
    :return: Dash page layout """
    cred_base_url = CRED_BASE_URL
    endpoint_id = GLOBUS_USS_EP_ID
    file_limit = 0
    folder_limit = 1

    share_url = f'https://app.globus.org/file-manager?method=GET&action={cred_base_url}/sharing/&origin_id={endpoint_id}' \
                f'&origin_path=%2F{username}%2F' \
                f'&filelimit={file_limit}' \
                f'&folderlimit={folder_limit}'
    folder_url = f'https://app.globus.org/select-group?method=GET&action={cred_base_url}/sharing/&multiple=no'

    fm_link = get_filemanager_url(username)
    example_link = get_example_data_url(username)

    acl_list_dict = dict(get_group_acl(my_groups))
    user_acl = get_user_acl(username, acl_list_dict)
    unshare_modal_content = (
        dbc.Form(
            [
                dcc.Dropdown(
                    id="unshare_select",
                    options=[{'label': f'{v["path"]} -> {v["group_name"]}', 'value': k} for (k, v) in user_acl.items()],
                    value='', multi=False),
            ],
            id="share_form",
            method='POST',
        ),
    )
    groups_content = (
        dbc.Form(
            [
                dcc.Dropdown(
                    id="group_select",
                    options=[{'label': g['name'], 'value': g['id']} for g in my_groups],
                    multi=False),
            ],
            id="group_form",
            method='POST',
        ),
    )

    return html.Div([
        navbar_authenticated(username),
        dbc.Container([
            html.H1("Share & Unshare Data with Globus"),
            return_breadcrumbs_row_sharing(fm_link=fm_link, share_url=share_url, group_url=folder_url),
            dbc.Row([html.H2("Before you begin...")], className='mb-4 mt-4'),
            dbc.Row([
                html.H4("Upload", className='font-weight-bold pr-2'),
                html.H4("or ensure the files you want to share are uploaded.")
            ], className='mb-2 mt-2 px-3'),
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Use Globus connect to establish an endpoint between your machine and TSCC.",
                                        className="card-subtitle mb-2"),
                                html.A(
                                    "Download and install Globus Connect Personal",
                                    href="https://www.globus.org/globus-connect-personal",
                                    target="_blank",
                                    className="btn btn-success m-2",
                                ),
                                html.A(
                                    "Go to File Manager",
                                    href=fm_link,
                                    target="_blank",
                                    className="btn btn-primary m-2",
                                ),
                                html.A(
                                    "View/Transfer example data",
                                    href=example_link,
                                    target="_blank",
                                    className="btn btn-info m-2",
                                ),
                            ]
                        ),
                    ),
                ]),
            ], className='mb-1 mt-1'),
            dbc.Row([
                html.H4("Create", className='font-weight-bold pr-2'),
                html.H4("a group of users for data to be shared with (if one does not already exist).")
            ], className='mb-2 mt-2 px-3'),
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6(
                                    """
                                    Use Globus to create a group that includes users who will have read access to  
                                    data, which you will select below. This will only need to be done once per group of 
                                    users, and you may use any number or combination of users who have signed up with 
                                    CReD.
                                    """,
                                    className="card-subtitle mb-2"
                                ),
                                dbc.Button(
                                    "Create group",
                                    href="https://app.globus.org/groups",
                                    target="_blank",
                                    className="m-2",
                                    color='primary'
                                )
                            ]
                        ),
                    ),
                ]),
            ], className='mb-1 mt-1'),
            dbc.Row([html.H2("Sharing your data")], className='mb-4 mt-4'),
            dbc.Row([
                html.H4("Select the folder", className='font-weight-bold pr-2'),
                html.H4("you wish to share.")
            ], className='mb-2 mt-2 px-3'),
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6(
                                    """
                                    Clicking this (external link) will take you to the Globus file manager page 
                                    containing the folders in your root directory. Navigate to the folder you wish to 
                                    share (ensure the Path points to the correct folder), and click "Submit" to go 
                                    back to CReD.
                                    """,
                                    className="card-subtitle mb-2"),
                                dbc.Button(
                                    "Select folder",
                                    href=share_url,
                                    className="m-2",
                                    color='primary'
                                ),
                                html.H6("You've selected: ", className="card-subtitle my-2"),
                                html.Div(
                                    [html.Ul(p) for p in path],
                                    className="font-weight-bold", id="selected-folder"
                                )
                            ]
                        ),
                    ),
                ]),
            ], className='mb-1 mt-1'),
            dbc.Row([
                html.H4("Select the group", className='font-weight-bold pr-2'),
                html.H4("you wish to share with.")
            ], className='mb-2 mt-2 px-3'),
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody([
                            html.H6(
                                """
                                Select the group that you want to share your files with.
                                """,
                                className="card-subtitle mb-2"),
                            html.Span(dbc.Button('Select Group', id="groups-btn", n_clicks=0, className="btn-primary")),
                            html.Div([
                                dbc.Modal(
                                    [
                                        dbc.ModalHeader("Select a group:"),
                                        dbc.ModalBody(groups_content),
                                        dbc.ModalFooter(
                                            dbc.Button(
                                                "Submit", id="group-modal-btn", className="ms-auto", n_clicks=0,
                                                href='/sharing/?group=',
                                                external_link=True,
                                            )
                                        ),

                                    ],
                                    id="groups-modal",
                                    is_open=False,
                                ),
                            ]),
                            html.Div(id='output_div'),
                            html.H6("You've selected: ", className="card-subtitle my-2"),
                            html.Div(group_name, className="font-weight-bold", id="selected-group")
                        ]),
                    ),
                ]),
            ], className='mb-1 mt-1'),
            dbc.Row(
                dbc.Button(
                    "Confirm and Share",
                    className='btn btn-lg btn-success btn btn-success',
                    id='confirm-btn',
                    disabled=True
                ),
                className='mb-2 mt-2 px-3',
            ),
            html.Div([
                dbc.Modal(
                    [
                        dbc.ModalHeader(html.Div("Confirm share?", className="h1 display-6")),
                        dbc.ModalBody([
                            html.Div([
                                html.H5("Sharing folder(s):"),
                                html.Ul([p for p in path])
                            ]),
                            html.Div([
                                html.H5("With group:"),
                                html.Ul(group_name),
                            ]),
                        ]),
                        dbc.ModalFooter(
                            dbc.Button(
                                "Submit", id="confirm-modal-btn", className="ms-auto", n_clicks=0,
                                href='/sharing/?confirm=yes',
                                external_link=True,
                                value='confirmed'
                            )
                        ),

                    ],
                    id="confirm-modal",
                    is_open=False,
                ),
            ]),
            dbc.Row([html.H2("Unshare Data")], className='mb-4 mt-4'),
            dbc.Row([
                html.H4("Reset permissions", className='font-weight-bold pr-2'),
                html.H4("for any shared folder to private.")
            ], className='mb-2 mt-2 px-3'),
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody([
                            html.Div([
                                html.Span(
                                    dbc.Button('Unshare a Folder', id="open", n_clicks=0, className="btn-danger")),
                                html.Div([
                                    dbc.Modal(
                                        [
                                            dbc.ModalHeader("Select a Folder to unshare:"),
                                            dbc.ModalBody(unshare_modal_content),
                                            dbc.ModalFooter(
                                                dbc.Button(
                                                    "Submit", id="submit", className="ms-auto", n_clicks=0,
                                                    href='/unsharing/',
                                                    external_link=True,
                                                )
                                            ),

                                        ],
                                        id="modal",
                                        is_open=False,
                                    ),
                                ]),
                                html.Div(id='output_div')
                            ]),
                        ]),
                    )
                ])
            ])
        ], className="container")
    ])


@share_app.callback(
    Output("unshare_select", "children"),
    [Input("unshare_select", "value")],
    [State("unshare_select", "options")]
)
def update_options(value):
    try:
        remove_share(value)
        return value
    except IndexError:
        pass


@share_app.callback(
    Output("modal", "is_open"),
    [Input("open", "n_clicks"), Input("submit", "n_clicks")],
    State("modal", "is_open")
)
def manage_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open

    return is_open


@share_app.callback(
    Output("confirm-modal", "is_open"),
    [Input("confirm-btn", "n_clicks"), Input("confirm-modal-btn", "n_clicks")],
    State("confirm-modal", "is_open")
)
def manage_confirm_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open

    return is_open


@share_app.callback(
    Output("groups-modal", "is_open"),
    [Input("groups-btn", "n_clicks"), Input("group-modal-btn", "n_clicks")],
    State("groups-modal", "is_open")
)
def manage_groups_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open

    return is_open


@share_app.callback(
    Output("group-modal-btn", "href"),
    Input("group_select", "value"),
)
def set_groups(selected_group):
    return f'/sharing/?group={selected_group}'


@share_app.callback(
    Output("confirm-btn", "disabled"),
    [Input("selected-group", "children"), Input("selected-folder", "children")],
)
def enable_confirm_button(group, folder):
    if group and folder:
        return False
    else:
        return True


def disable_folder_input(list_of_contents):
    """
    We want to prevent users from modifying the folder where files are to be uploaded, while files are uploading.
    We also want to prevent multiple uploads occurring (changing "folder" will trigger the upload callback after
    every state change!
    :param list_of_contents: list of file contents, will not be None if user selects files for uploading.
    :return: True
    """
    if list_of_contents is not None:
        return True


def validate_share(session):
    """
    Verify that the user has only attempted to share data they have access to

    :param session: a dictionary-like session object containing the information about the object being shared
    :return Boolean, string: regarding whether the share attempt is valid or not, and the message (None if success)
    """
    user = session.get('username', None)
    path = session.get('path', [])
    try:
        for p in path:
            path_user = p.split('/', 2)
            if str(user) != str(path_user[1]):
                logger.error(
                    f'user {str(user)} tried sharing a file owned by {str(path_user[1])}, but names do not match.'
                )
                return False, "You do not appear to have permission to share the selected file or folder."
        return True, None
    except Exception as e:
        logger.info(f'The sharing validation error for {path} is ', e)
        return False, f'Could not validate {path}.'


def confirm_share(session):
    """
    Create the share

    :param session: a dictionary-like session object containing the information about the object being shared
    :return Boolean, string: regarding whether the share attempt is successful or not, and the message (None if success)
    """
    endpoint_id = session.get('endpoint_id', None)
    path = session.get('path', [])
    uuid = session.get('uuid', None)
    for p in path:
        r_data = {
            "DATA_TYPE": "access",
            "principal_type": "group",
            "principal": uuid,
            "path": p,
            "permissions": "r",
        }
        cred_admin = get_admin_client()
        try:
            cred_admin.add_endpoint_acl_rule(endpoint_id, r_data)
        except Exception as e:
            logger.error('The sharing confirmation error is', e)
            return False
    return True, None


def remove_share(rule_id):
    """
   Remove a share
   :return None
    """
    endpoint_id = settings.GLOBUS_USS_EP_ID
    cred_admin = get_admin_client()
    try:
        cred_admin.delete_endpoint_acl_rule(endpoint_id, rule_id)
    except Exception as e:
        logger.error('The unsharing confirmation error is', e)  # todo: fix as this will always be triggered in dev.


def get_group_list(gc):
    try:
        return gc.get_my_groups()
    except AttributeError:
        return []


def get_group_acl(my_groups):
    """
    Remove a share
    :return a dictionary containing group record from the acl
    """
    endpoint_id = settings.GLOBUS_USS_EP_ID

    cred_admin = get_admin_client()
    acl_list = None
    try:
        acl_list = cred_admin.endpoint_acl_list(endpoint_id)
    except Exception as e:
        logger.error('The get group acl sharing confirmation error is', e)

    acl_dict = json.loads(str(acl_list))
    acl_list_dict = {}
    for record in list(acl_dict['DATA']):
        principle_type = record.get("principal_type", None)
        principle_id = record.get('id', None)
        if principle_id and principle_type == "group":
            for group in my_groups:
                if group['id'] == record['principal']:
                    acl_list_dict[record['id']] = {'path': record['path'], 'group_name': group['name']}
    return acl_list_dict


def get_user_acl(username, acl_list_dict):
    """
   Get only those ACL records for the user
   :params username: The user that owns these acl shares
   :params acl_dict: A dictionary containing all ACL records
   :return a dictionary containing group record from the acl
    """
    user_acl = {}
    pattern = rf'^\/{username}\/[0-9, a-z, A-Z, \/]*'
    for k, v in acl_list_dict.items():
        if re.match(pattern, acl_list_dict[k]['path']):
            user_acl[k] = v

    return user_acl
