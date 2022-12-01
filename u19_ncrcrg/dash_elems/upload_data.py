import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input
from django_plotly_dash import DjangoDash

from .help_page import tooltip_collection
from .helpers import *
from .navbars import navbar_authenticated
from .. import settings

logger = logging.getLogger(__name__)

THEME = settings.BOOTSTRAP_THEME

upload_app = DjangoDash('UploadDataApp', external_stylesheets=[settings.BOOTSTRAP_THEME])


def upload_data(user):
    upload_app.layout = return_page_layout(user)
    return upload_app


def return_page_layout(user):
    """Layout for the File Upload page. This page is also the landing page once a user has
    authenticated via Globus
    :return: Dash page layout """
    fm_link = get_filemanager_url(user)
    example_link = get_example_data_url(user)
    return html.Div([
        navbar_authenticated(user),
        dbc.Container([
            html.H1("Process & Analyze Data"),
            return_breadcrumbs_row(current="Upload Data"),
            dbc.Row([html.H2("Upload Data")], className='mb-4 mt-4'),
            dbc.Row([
                html.H4("Transfer files to CReD")
            ], className='mb-2 mt-2 px-3'),
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Globus", className="card-title"),
                                html.H6([
                                    "Use Globus connect to establish a connection between your ",
                                    html.Span(
                                        "collection",
                                        id='tooltip-collection',
                                        style={"textDecoration": "underline", "cursor": "pointer"},
                                    ),
                                    """ 
                                    and CReD. For step-by-step instructions on how to upload or transfer files, 
                                    please visit our 
                                    """,
                                    html.A("help page", href="/help/", target="_blank"),
                                    "."
                                ], className="card-subtitle"),
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
            ], className='m-2'),
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("Request import from public repository", className="card-title"),
                                html.H6([
                                    """
                                    View publications and use the import data button to transfer selected files into 
                                    CReD.
                                    """
                                ], className="card-subtitle"),
                                html.A(
                                    "Transfer from the Sequence Read Archive (SRA)",
                                    href="/papers",
                                    className="btn btn-success m-2",
                                ),
                            ]
                        ),
                    ),
                ]),
            ], className='m-2'),


        ], className="container"),
        tooltip_collection(),
    ])


@upload_app.callback(
    Output('folder', 'disabled'),
    Input('upload-data', 'contents')
)
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


@upload_app.callback(
    Output('hidden-password', 'style'),
    [Input('toggle', 'value')]
)
def toggle_container(toggle_value):
    if toggle_value == 'Show':
        return {'display': 'block'}
    else:
        return {'display': 'none'}
