from collections import defaultdict
from urllib.parse import quote_plus

import dash_bootstrap_components as dbc
from dash import dcc
from django_plotly_dash import DjangoDash

from .help_page import tooltip_collection, tooltip_job
from .navbars import navbar_authenticated
from .helpers import *
from .. import settings

logger = logging.getLogger(__name__)

submit_app = DjangoDash('SubmitJobApp', external_stylesheets=[settings.BOOTSTRAP_THEME])
STATESDICT = defaultdict(list)


def list_files(my_files, user_name):
    endpoint_id = settings.GLOBUS_USS_EP_ID
    base_url = settings.GLOBUS_HTTPS_SERVER_BASE_URL

    selected_files = []
    if len(my_files) > 0:
        for f in my_files:
            if f.endswith('/'):  # all folders must end with "/" see: views.set_my_files()
                selected_files.append(
                    dbc.ListGroupItem(
                        html.A(
                            f,
                            href=f"https://app.globus.org/file-manager?origin_id={endpoint_id}&origin_path={user_name}%2F" + quote_plus(
                                f),
                            target="_blank"
                        )
                    )
                )
            else:
                selected_files.append(dbc.ListGroupItem(html.A(f, href=f"{base_url[:-1]}/{user_name}/{f}", target="_blank")))
        return html.Div([
            html.H5("You've selected:"),
            dbc.ListGroup(selected_files),
            dcc.Link(
                dbc.Button("Clear selection", color="secondary", className="my-2", ),
                href='/submit-job/?clear_file_list=true',
                refresh=True
            )
        ])
    else:
        return html.Div()


def submit_job_page(cred_user, my_files):
    base_url = "https://app.globus.org/file-manager"
    platform_url = get_platform_url()
    callback_url = f'{platform_url}/submit-job/' if settings.DEBUG == True else 'https://cred-portal.com/submit-job/'
    query_string = f'?method=GET&origin_id={settings.GLOBUS_USS_EP_ID}&origin_path=%2F{cred_user}%2F&action={callback_url}'
    url = base_url + query_string
    submit_app.layout = html.Div([
        navbar_authenticated(cred_user),
        dbc.Container([
            html.H1("Process & Analyze Data", id="submitJobTitle"),
            return_breadcrumbs_row(current="Submit Job"),
            dbc.Row([html.H2("Select files from Globus")], className='mb-4 mt-4'),
            dbc.Container([
                html.Div([
                    "Use the button below to navigate to the CReD Portal ",
                    html.Span("collection", id="tooltip-collection", style={"textDecoration": "underline", "cursor": "pointer"},),
                    " on Globus, where you can select one or more files to use in your ",
                    html.Span("job.", id="tooltip-job", style={"textDecoration": "underline", "cursor": "pointer"},),
                    tooltip_collection(),
                    tooltip_job(),
                ]),
                html.Div([
                    dbc.Button(
                        "Select files",
                        id="selectFiles",
                        href=url,
                        external_link=True,
                        color="primary",
                        className="my-1"
                    ),
                ],
                    className="d-grid gap-2"
                ),
                list_files(my_files, cred_user),

            ]),
            dbc.Row([html.H2("Select tool and submit job")], className='mb-4 mt-4'),
            dbc.Container([
                html.Div(
                    "After you have chosen your files/folders, select a tool, choose the appropriate parameters, and click \"Submit\" to queue up your job.")
            ])
        ], className="container"),
    ])

    return submit_app