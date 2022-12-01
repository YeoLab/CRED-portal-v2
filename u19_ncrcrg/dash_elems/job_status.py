"""
Dash apps for the demonstration of functionality

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
import datetime
import logging
import math
import os
from urllib.parse import quote_plus

import boto3
import dash_bootstrap_components as dbc
import requests
from dash import dcc, html
from dash import dash_table, exceptions
import eutils
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Output, Input, State
from django_plotly_dash import DjangoDash

from .help_page import tooltip_permanent, tooltip_collection, tooltip_scratch, tooltip_trash
from .helpers import return_breadcrumbs_row, get_filemanager_url, get_jupyter_filemanager_url
from ..accounts.views import get_globus_https_server, get_https_token
from .navbars import navbar_authenticated
from .. import settings
from ..tools import connect_mongodb
from ..statuses import get_progress, get_message

logger = logging.getLogger(__name__)

THEME = settings.BOOTSTRAP_THEME

status_app = DjangoDash('JobStatusApp', external_stylesheets=[settings.BOOTSTRAP_THEME])
ec = eutils.Client()
df = None
job_status_columns = ['Name & Date', 'Name (Click to expand)', 'Date', 'Project tag', 'Trashed', 'removed']

#####


# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "24rem",
    "height": "100%",
    "z-index": 1,
    "overflow-x": "hidden",
    "transition": "all 0.5s",
    "padding": "0.5rem 1rem",
    "background-color": "#f8f9fa",
}

SIDEBAR_HIDDEN = {
    "position": "fixed",
    "top": 0,
    "left": "-24rem",
    "bottom": 0,
    "width": "24rem",
    "height": "100%",
    "z-index": 1,
    "overflow-x": "hidden",
    "transition": "all 0.5s",
    "padding": "0rem 0rem",
    "background-color": "#f8f9fa",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "transition": "margin-left .5s",
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

CONTENT_STYLE1 = {
    "transition": "margin-left .5s",
    "margin-left": "2rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

sidebar = html.Div(
    [
        html.H2("Job details", className="display-4"),
        html.Hr(),
        html.P(
            "Job details", className="lead", id="sidebar-jobid"
        ),
        dbc.InputGroup([
            dbc.InputGroup("Module"),
            dbc.Input(value="", disabled=True, id="sidebar-module")
        ], className="my-1"),
        dbc.InputGroup([
            dbc.InputGroup("Module version"),
            dbc.Input(value="", disabled=True, id="sidebar-version")
        ], className="my-1"),
        dbc.InputGroup([
            dbc.InputGroup("Processing Date"),
            dbc.Input(value="", disabled=True, id="sidebar-date")
        ], className="my-1"),
        dbc.InputGroup([
            dbc.InputGroup("Description"),
            dbc.Textarea(value="", disabled=True, id="sidebar-description")
        ], className="my-1"),
        dbc.InputGroup([
            dbc.InputGroup("Last updated"),
            dbc.Input(value="", disabled=True, id="sidebar-status-updated")
        ], className="my-1"),
        html.P(
            "Job status", className="lead"
        ),
        dbc.Progress(id="sidebar-progress", className="my-1", value=0),
        html.Div(id="sidebar-status"),

    ],
    id="sidebar",
    style=SIDEBAR_STYLE,
)

content = html.Div(

    id="page-content",
    style=CONTENT_STYLE)


@status_app.callback(
    [
        Output("sidebar", "style"),
        Output("page-content", "style"),
        Output("side_click", "data"),
        Output("jobid_click", "data"),
        Output("sidebar-jobid", "children"),
        Output("sidebar-description", "value"),
        Output("sidebar-module", "value"),
        Output("sidebar-version", "value"),
        Output("sidebar-date", "value"),
        Output("sidebar-status", "children"),
        Output("sidebar-status-updated", "value"),
        Output("table", "active_cell"),
        Output('job-status-loading', 'children'),
        Output('sidebar-progress', 'value'),
    ],

    [Input("table", "active_cell"), ],
    [
        State("side_click", "data"),
        State("jobid_click", "data"),
        State("username", "data"),
        State("table", "derived_viewport_data"),
    ],
)
def toggle_sidebar(active_cell, nclick, prev_select, user_name, data):
    endpoint_id = settings.GLOBUS_USS_EP_ID
    job_id = None

    default_status_layout = dbc.Input(value="", disabled=True, id="sidebar-status-text")
    defaults = SIDEBAR_HIDDEN, CONTENT_STYLE1, 'HIDDEN', prev_select, job_id, "", "", "", default_status_layout, "", "", active_cell, False, 0

    if active_cell is not None and data is not None:
        if active_cell["column_id"] == "Name (Click to expand)":
            job_id = data[active_cell["row"]]["job_id"]
            if nclick == "SHOW" and job_id == prev_select:
                sidebar_style = SIDEBAR_HIDDEN
                content_style = CONTENT_STYLE1
                cur_nclick = "HIDDEN"
            else:
                sidebar_style = SIDEBAR_STYLE
                content_style = CONTENT_STYLE
                cur_nclick = "SHOW"

            prev_select = job_id
            active_cell = {'row': -1, 'column': -1, 'column_id': "None selected"}

            job_metadata = get_job_metadata(job_id=job_id, user_name=user_name)

            job_status_msg, status_last_updated = get_current_job_status(experiment_name=job_id)
            if job_status_msg == get_message("COMPLETE"):
                progress = 100

                url = f"/results/{job_id}/"
                url = f"https://app.globus.org/file-manager?origin_id={endpoint_id}&origin_path={user_name}" + quote_plus(
                    url)

                job_status_layout = html.A(
                    "Results",
                    className="btn btn-primary mr-1",
                    href=url,
                    target="_blank",
                )
            elif job_status_msg == get_message("DOWNLOADCOMPLETE"):
                progress = 100

                url = f"/raw_files/{job_id}/"
                url = f"https://app.globus.org/file-manager?origin_id={endpoint_id}&origin_path={user_name}" + quote_plus(
                    url)

                job_status_layout = html.A(
                    "Results",
                    className="btn btn-primary mr-1",
                    href=url,
                    target="_blank",
                )
            elif job_status_msg.startswith('http'):
                progress = 50
                job_status_layout = html.A(
                    "URL",
                    className="btn btn-primary mr-1",
                    href=job_status_msg,
                    target="_blank",
                )
            else:
                progress = set_progress(job_status_msg)
                job_status_layout = dbc.Input(value=job_status_msg, disabled=True, id="sidebar-status-text")

            return sidebar_style, \
                   content_style, \
                   cur_nclick, \
                   prev_select, \
                   job_id, \
                   job_metadata['experiment_summary'], \
                   job_metadata['module'], \
                   job_metadata['module_version'], \
                   job_metadata['processing_date'], \
                   html.Div(job_status_layout), \
                   status_last_updated, \
                   active_cell, \
                   True, \
                   progress

    return defaults


def get_current_job_status(experiment_name, soft_limit=14, hard_limit=30):
    """
    Returns the last (only?) message from the expt_name queue.
    :param experiment_name: string
        full expt name (with checksum ie. 6mo_cortical_organoids_wt_cellranger3_feab5103e16ff600793fea28bb618f63558e6392.json) # noqa
    :param soft_limit: int
        Used only to communicate to the user that the last messsage was not found (likely deleted after 14 days).
        Doesn't really do anything otherwise
    :param hard_limit: int
        Max number of days that pass from the time of job submission. If a job is more than hard_limit days old,
        we don't even check SQS as 1) jobs should not take longer than this to finish, 2) SQS messages have a max
        lifespan of 14 days, meaning these jobs won't have messages in queue anyway.
    """
    dt = datetime.datetime.now() - datetime.datetime.strptime('-'.join(experiment_name.split('-')[-6:]),
                                                              "%Y-%m-%d-%H-%M-%S")
    hard_limit_dt = datetime.timedelta(days=hard_limit)
    if dt > hard_limit_dt:
        return f"Job finished.", f'More than {hard_limit} days ago.'
    session = boto3.session.Session(region_name='us-west-1')
    sqs = session.client(
        'sqs',
        aws_access_key_id=os.environ.get('SQS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('SQS_SECRET_ACCESS_KEY'),
        region_name='us-west-1'
    )

    try:
        url = sqs.get_queue_url(
            QueueName=str(experiment_name).replace('\"', '') + '.fifo')

    except Exception as e:
        logger.error(
            " Exception in experiment_viewer.services.get_current_job_status() : [{}], {}".format(
                e, experiment_name + '.fifo'
            )
        )  # noqa

        return "Error", ' '

    response = sqs.receive_message(
        QueueUrl=url['QueueUrl'],
        AttributeNames=[
            'SentTimestamp',
        ],
        MaxNumberOfMessages=10,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=12
    )
    message_to_return = None

    try:
        max_timestamp = 0

        for message in response['Messages']:
            if float(message['Attributes']['SentTimestamp']) > max_timestamp:
                max_timestamp = float(message['Attributes']['SentTimestamp'])
                message_to_return = message['Body']
        last_updated = pd.to_datetime(max_timestamp, unit='ms').to_pydatetime()

    except KeyError as e:
        logger.error("Exception in get_current_job_status for job {}: [{}]".format(experiment_name, e))  # noqa
        return "Job finished.", f'More than {soft_limit} days ago.'
    return message_to_return, last_updated.strftime('%m-%d-%y %H:%M:%S')


db = connect_mongodb(database='u19', user=bytes(os.environ.get("MONGODB_USER"), 'utf-8'),
                     password=bytes(os.environ.get("MONGODB_PASSWORD"), 'utf-8'))


def get_all_projects(user_name):
    """
    Queries the mongodb and returns all projects associated with user_name
    :param user_name: string
    :return: list
        list of dictionaries corresponding to project-level metadata.
    """
    project_collection = db['Projects']
    project_query = project_collection.find({"user": user_name})
    return [p['project_name'] for p in project_query]


def get_job_metadata(job_id, user_name):
    try:
        experiment_collection = db['Experiments']
        experiment_query = experiment_collection.find_one(
            {"aggr_nickname": job_id, "user": user_name},
        )
        if experiment_query is not None:
            return experiment_query
        else:
            logger.debug(f"Can't find {job_id}, {user_name} in collection.")
            return {'experiment_summary': "", 'module': "", 'module_version': "", 'processing_date': ""}

    except Exception as e:
        logger.error(e)
        return {'experiment_summary': "", 'module': "", 'module_version': "", 'processing_date': ""}


def reformat_date_string(date_string):
    """
    Every job's "aggr_nickname" should have a timestamp with an expected format:
    %Y-%m-%d
    This function returns a slightly nicer way of displaying the date
    on the page.

    :param date_string:
    :return:
    """
    dt = datetime.datetime.strptime(date_string, "%Y-%m-%d-%H-%M-%S")
    return dt.strftime("%Y-%m-%d")


def get_project_experiments(project_name, user_name):  # noqa

    experiment_metadata = dict()

    project_collection = db['Projects']

    # Get the project record matching the project name
    project_query = project_collection.find_one({"project_name": project_name, "user": user_name},
                                                {'_id': False})
    # Extract the experiment list from the project record
    try:  # edge case when transferring old jobs from V1
        experiment_list = project_query["experiments"]
    except KeyError:
        experiment_list = []
    for e in experiment_list:
        job_name_split = e['aggr_nickname'].split('-')
        job_name = '-'.join(job_name_split[:-6])  # dependent on timestamp being appended to the end of the job.
        job_date = reformat_date_string('-'.join(job_name_split[-6:]))
        trashed = e.get('trashed', 'no')  # due to old methods, 'trashed' can either be 'yes', 'no', or type(datetime)
        removed = e.get('removed', 0)  # unlike trashed, removed jobs no longer have associated queues or projects

        if trashed == 'yes':  # old trashed jobs need to be 're-trashed' to add the timestamp of trashed
            trashed = move_experiment_to_trash(e['aggr_nickname'], project_name, user_name)


        if removed == 0:
            experiment_metadata[e['aggr_nickname']] = {
                'Name & Date': "{} ({})".format(
                    job_name,
                    job_date,
                ),
                'Name (Click to expand)': job_name,
                'Project tag': project_name,
                'Date': job_date,
                'Share status': e['type'],
                'Trashed': trashed,
                'removed': removed
            }

    if len(experiment_metadata.keys()) == 0:  # no projects or experiments yet
        return pd.DataFrame(
            columns=['Name & Date', 'Name (Click to expand)', 'Project tag', 'Date', 'Share status', 'Trashed', 'removed'])
    return pd.DataFrame(experiment_metadata).T


def add_new_experiment_to_project(experiment_record, project, user_name):
    """
    Appends the experiment (job) to a user's project.
    @see views.create_job
    """
    try:
        db['Projects'].update_one(
            {'project_name': project, 'user': user_name},
            {
                '$push': {
                    'experiments': {
                        'aggr_nickname': experiment_record['aggr_nickname'],
                        'type': "personal",
                        'modality': experiment_record['modality']
                    }
                },
                '$inc': {
                    'num_experiments': 1
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Problem append new expt {experiment_record['aggr_nickname']} to project {project}", e)
        return False


def remove_experiment_from_project(aggr_nickname, project, user_name):
    try:
        db['Projects'].update_one(
            {'project_name': project, 'user': user_name},
            {
                '$pull': {
                    'experiments': {
                        'aggr_nickname': aggr_nickname,
                    }
                },
                '$inc': {
                    'num_experiments': -1
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Problem hiding an experiment {aggr_nickname}", e)
        return False


def move_experiment_to_trash(aggr_nickname, project, user_name):
    """
    Modifies 'trashed' tag in metadata database. Adds a timestamp that marks the datetime when user moves job over
    to trash. We'll need to check this timestamp against some period (see check_and_remove_expt()), and if the
    job has been sitting in trash for longer than this time, remove from projects and delete the associated sqs queue.
    """
    try:
        trashed_datetime = datetime.datetime.now()
        db['Projects'].find_and_modify(
            query={
                'project_name': project,
                'user': user_name,
                'experiments.aggr_nickname': aggr_nickname,
            },
            update={
                '$set': {
                    'experiments.$.trashed': trashed_datetime
                },
            }
        )
        logger.debug(f"Moved {aggr_nickname} to trash.")
        return trashed_datetime
    except Exception as e:
        logger.error(f"Problem hiding an experiment {aggr_nickname}", e)
        return 'no'


def restore_trashed_experiment(aggr_nickname, project, user_name):
    """
    Modifies the 'trashed' tag for the experiment in project space. This now effectively 'resets' the clock by which
    items stay in trash before ultimately getting removed after some period of time.

    Returns True if successfully changes the trashed tag, False otherwise.
    """
    try:
        db['Projects'].find_and_modify(
            query={
                'project_name': project,
                'user': user_name,
                'experiments.aggr_nickname': aggr_nickname,
            },
            update={
                '$set': {
                    'experiments.$.trashed': 'no'
                },
            }
        )
        return True
    except Exception as e:
        logger.error(f"Problem hiding an experiment {aggr_nickname}", e)
        return False


def return_esearch_layout():
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H4("NCBI"),
                dbc.Input(id='esearch', value="", placeholder="Search pubmed for terms...", debounce=True),
            ]),
            dbc.CardBody([
                html.Details([
                    html.Summary('Details of search will become available here (Click to expand).'),
                    dbc.CardBody("...")
                ])
            ], id='esearch_results')
        ], className='mb-4')
    ])


def return_massive_search_layout():
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H4("MASSIVE"),
                dbc.Input(id='massive_search_author', value="", placeholder="Search MASSIVE by author...",
                          debounce=True, className='mb-4'),
                dbc.Input(id='massive_search_keyword', value="", placeholder="Search MASSIVE for terms...",
                          debounce=True, className='mb-4'),
            ]),
            dbc.CardBody([
                html.Details([
                    html.Summary('Details of search will become available here (Click to expand).'),
                    dbc.CardBody("...")
                ])
            ], id='massive_search_results')
        ], className='mb-4')
    ])


def return_pie_chart_layout(df, dx):
    options = None
    try:
        options = [{'value': x, 'label': x}
                   for x in set(df['Project tag'])] + [{'value': "All", 'label': "All"}]  # noqa
    except TypeError as e:
        logger.error(e)
        pass

    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H4("Projects:"),
                dcc.Dropdown(
                    value="All",
                    id='project',
                    options=options,
                    clearable=False
                ),
                dcc.Graph(id="pie-chart",
                          figure=go.Figure(data=[go.Pie(labels=dx.index, values=dx['Project tag'], hole=.5)])),
            ]),
        ], className='mb-4')
    ])


def return_jupyterhub_panel_layout(user_name):
    jupyterhub_fm_link = get_jupyter_filemanager_url(username=user_name)
    jupyterhub_server_link = "https://hub.stratus.jupyter-security.info/jhub/hub/"
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H4("Jupyterhub"),
                dbc.Row([
                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                html.A(
                                    "File manager",
                                    className="btn btn-info m-1",
                                    href=jupyterhub_fm_link,
                                    target="_blank"
                                ),
                            ], className="col align-self-center", width=3),
                            dbc.Col([
                                html.Img(
                                    src="/static/images/logos/transfer_cred-jupyter_logo.svg",
                                    style={'height': '80px'},
                                ),
                            ], width=9)
                        ], className="align-middle"),
                        html.Div([
                            "Transfer data between CReD ",
                            "& Jupyterhub ",
                            html.Span(
                                "(scratch)",
                                id="tooltip-scratch",
                                style={"textDecoration": "underline", "cursor": "pointer"},
                            ),
                            " collections.",
                            tooltip_scratch(),
                        ])
                    ]),
                ], className='ml-2 my-4'),
                dbc.Row([
                    html.Div([
                        html.A(
                            "Launch Jupyterhub",
                            className="btn btn-success m-1",
                            href=jupyterhub_server_link,
                            target="_blank"
                        ),
                        html.Div(
                            "Takes you to the Jupyterhub control panel, where you may select an image and spawn a server."
                        )
                    ]),
                ], className='ml-2 my-4'),
            ])
        ], className='mb-4')
    ], className='mb-4')


def return_scratch_pad_layout():
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H4("Scratchpad"),
                dcc.Textarea(
                    id='textarea-state-example',
                    value='Scratch pad',
                    style={'width': '100%', 'height': 200},
                ),
                html.Button('Save', id='textarea-state-example-button', n_clicks=0),
                html.Div(id='textarea-state-example-output', style={'whiteSpace': 'pre-line'})
            ])
        ], className='mb-4')
    ])


def check_and_remove_expt(row, user_name, max_days=14):
    """
    Checks how long a row (expt) has been sitting in trash. If it's been more than max_days:
    - delete associated sqs queue
    - remove the job from associated project

    Note: This does NOT remove the job from the databases' "experiments" collection. We might want to keep all records
    stored just in case. However since we use the "projects" collection to display all of the users' associated jobs/
    experiments, removed jobs should never show back up in the dashboard.

    Note: This also does NOT remove any files generated by the job. Only removes the SQS queue and job record from its
    project.
    """
    # Dataframe shouldn't have any removed=1 columns, @see get_project_experiments()
    # So we shouldn't hit this unless there's an edge case I'm not thinking of?
    if row['removed'] == 1:
        return 1
    elif datetime.datetime.now() - row['Trashed'] > datetime.timedelta(days=max_days):
        try:
            logger.info(
                f"Removing fifo name: {row['job_id']}.fifo from SQS {row['Project tag']} and user = {user_name}"
            )
            delete_sqs_queue(row['job_id'])
        except Exception as e:
            logger.error(
                f"{e}: Problem removing fifo name: {row['job_id']}.fifo from SQS {row['Project tag']} and user = {user_name}"
            )
        return 1
    return 0


def return_trashed_job_layout(df, user_name, max_page_size=10):
    """
    Returns layout for displaying trashed jobs

    Also checks 'old' trashed jobs by applying remove_expt() to every job in the 'trashed' dataframe.
    Sets the 'removed' column to 1 if the trashed job has been trashed for longer than 14 days.
    Removed jobs should also have their SQS queue removed, as well as their projects disassociated (remove from project)
    """
    _df = df[df['Trashed'] != 'no']  # either trashed = 'yes' or type(datetime)

    _df['job_id'] = _df.index
    try:
        _df['removed'] = _df.apply(check_and_remove_expt, args=(user_name, ), axis=1)
        _df = _df[_df['removed']==0]
    except ValueError as e:  # empty dataframe
        pass

    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H4([
                    "Trash ",
                    html.Span(
                        "(Cleared after two weeks)",
                        id="tooltip-trash",
                        style={"textDecoration": "underline", "cursor": "pointer"},
                    ),
                    tooltip_trash(),
                ]),
                dash_table.DataTable(
                    data=_df.to_dict('records'),
                    columns=[{"name": i, "id": i, "presentation": 'markdown', } for i in ['Name & Date']],
                    page_current=0,
                    page_size=max_page_size,
                    page_action='native',
                    sort_action="native",
                    sort_mode="multi",
                    filter_action="native",
                    is_focused=True,
                    id="trash",
                    row_deletable=True,
                    style_as_list_view=True,
                ),
                html.Div(),
                html.Div(id='trash_output'),
            ])
        ], className='mb-4')
    ])


def return_job_status_layout(df, max_page_size=5):
    _df = df[df['Trashed'] == 'no']
    _df['job_id'] = _df.index

    return [
        dbc.Card([
            dbc.CardBody([
                html.H4("Current Jobs"),
                dash_table.DataTable(
                    data=_df.to_dict('records'),
                    columns=[{"name": i, "id": i, "presentation": 'markdown', } for i in _df.columns[1:-3]],
                    # hide "index", "Trashed", "job_id" columns
                    page_current=0,
                    page_size=max_page_size,
                    page_action='native',
                    sort_action="native",
                    sort_mode="multi",
                    filter_action="native",
                    is_focused=True,
                    id="table",
                    style_header={
                        'font-family': '\"Open Sans\", -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif, \"Apple Color Emoji\", \"Segoe UI Emoji\", \"Segoe UI Symbol\"'
                    },
                    style_cell={
                        'font-family': '\"Open Sans\", -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif, \"Apple Color Emoji\", \"Segoe UI Emoji\", \"Segoe UI Symbol\"'
                    },
                    style_data_conditional=[
                        {
                            'if': {
                                'state': 'active'  # 'active' | 'selected'
                            },
                            'backgroundColor': 'rgba(0, 116, 217, 0.3)'
                        },
                        {
                            'if': {
                                'state': 'selected'  # 'active' | 'selected'
                            },
                            'backgroundColor': 'rgba(0, 116, 217, 0.3)'
                        },
                    ],
                    row_deletable=True,
                    style_as_list_view=True,
                ),
                html.Div(),
                html.Div(id='output'),
                dcc.Loading(
                    id="loading-2",
                    children=[html.Div([html.Div(id="job-status-loading")])],
                    type="circle",
                ),
                dcc.Location(id='location'),
                dbc.Button(
                    "New Job",
                    id='newJob',
                    color="primary",
                    className="m-2",
                    href="/submit-job/",
                    external_link=True,
                ),
            ], className="text-dark")
        ])
    ]


def return_globus_card_layout(user_name, max_alloc_gb=100):
    fm_link = get_filemanager_url(user_name)
    return dbc.Card([
        dbc.CardBody([
            html.H4(f"Manage files/groups"),
            html.Div(html.H6(f"Used {get_usage(user_name)} / {max_alloc_gb} GB (Updates daily)")),
            dbc.Row([
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.A(
                                "File manager",
                                className="btn btn-info m-1",
                                href=fm_link,
                                target="_blank"
                            ),
                        ], className="col align-self-center", width=3),
                        dbc.Col([
                            html.Img(
                                src="/static/images/logos/transfer_local-cred_logo.svg",
                                style={'height': '80px'},
                            ),
                        ], width=9)
                    ], className="align-middle"),
                    html.Div([
                        "Transfer files between your source and the CReD Portal ",
                        html.Span("collection.", id="tooltip-collection",
                                  style={"textDecoration": "underline", "cursor": "pointer"}, ),
                        tooltip_collection(),
                    ])
                ]),
            ], className='ml-2 my-4'),
            dbc.Row([
                html.Div([
                    html.A(
                        "Group manager",
                        className="btn btn-info m-1",
                        href="https://app.globus.org/groups",
                        target="_blank"
                    ),
                    html.Div(
                        "Manage your Globus groups."
                    )
                ]),
            ], className='ml-2 my-4'),
            dbc.Row([
                html.Div([
                    dbc.Button(
                        "Sharing",
                        color="primary",
                        className="m-1",
                        href="/sharing/",
                        external_link=True,
                    ),
                    html.Div(
                        "Share files."
                    )
                ]),
            ], className='ml-2 my-4'),
        ])
    ])


def convert_size(size_kilobytes):
    """
    Converts file size (in kilobytes, that's default for du) to GB+
    """
    size_bytes = size_kilobytes * 1024
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def get_usage(user_name):
    """
    Reads today's du file, returns the usage for a user_name.

    du file should look like:

    37534740	/projects/ps-yeolab5/cred/awooten
    24	/projects/ps-yeolab5/cred/awooten03c794eb071b4464
    521761416	/projects/ps-yeolab5/cred/bay001
    52	/projects/ps-yeolab5/cred/brianfbb
    24	/projects/ps-yeolab5/cred/brucearonow
    ...
    """
    endpoint_id = settings.GLOBUS_USS_EP_ID
    https_server = get_globus_https_server(endpoint_id)
    # open file to stream out
    transfer_url = f'{https_server}/usage/{datetime.datetime.today().strftime("%Y%m%d")}.txt'
    https_token = None
    try:
        https_token = get_https_token(endpoint_id)
    except Exception as e:
        logger.debug(f'\n\nThe exception is {e}\n\n')

    header = {"Authorization": f"Bearer {https_token}"}
    response = requests.get(transfer_url, headers=header, allow_redirects=False)
    for entry in response.content.decode('utf-8').split('\n'):
        entry = entry.split('\t')
        if entry[-1].split('/')[-1] == user_name:
            return convert_size(int(entry[0]))
    return '0 GB'


def return_page_layout(df, user_name):
    """
    Controls the look/feel of the job status interface.

    :param: df - dataframe with date required in layout
    :return: dash layout object
    """
    return html.Div(
        [
            navbar_authenticated(user_name),
            dbc.Container([
                html.H1("Dashboard", id='title'),
                return_breadcrumbs_row(current="Dashboard"),
                dbc.Row([
                    dbc.Col(
                        return_job_status_layout(df=df),
                        className='mb-4',
                        id='job-status-layout'
                    ),
                    dbc.Col(
                        return_globus_card_layout(user_name=user_name),
                    )
                ]),
                dbc.Row([
                    dbc.Col(
                        [
                            return_jupyterhub_panel_layout(user_name=user_name),
                        ], className='my-4'
                    ),
                    dbc.Col(
                        [
                            return_trashed_job_layout(df=df, user_name=user_name),
                        ], className='my-4'
                    ),
                ]),
            ]),
            html.Div(
                [
                    dcc.Store(id='side_click'),
                    dcc.Store(id='jobid_click'),
                    dcc.Store(id='username', data=user_name),
                    dcc.Location(id="url"),
                    sidebar,
                    content,
                ],
            )
        ],
    )


def job_status(user):
    df = pd.DataFrame(columns=job_status_columns)  # noqa
    projects = get_all_projects(user.username)
    for project in projects:
        df = pd.concat([df, get_project_experiments(project, user.username)])
    df = df[df['removed'] != 1]
    df.sort_values(['Date', 'Name (Click to expand)'], ascending=False, inplace=True)

    status_app.layout = return_page_layout(df=df[job_status_columns], user_name=user.username)

    return status_app


@status_app.callback(
    Output("pie-chart", "figure"),
    [Input("project", "value"), Input("table", "data")],
)
def generate_chart(name, job_data):
    df = pd.DataFrame(job_data)

    try:
        if name != "All":
            dx = pd.DataFrame(df[df['Project tag'] == name]['Project tag'].value_counts())
        else:
            dx = pd.DataFrame(df['Project tag'].value_counts())
        fig = go.Figure(data=[go.Pie(labels=dx.index, values=dx['Project tag'], hole=0.5)])
    except TypeError:
        fig = go.Figure(data=[go.Pie(labels=['No jobs'], values=[1], hole=0.5)])
    except KeyError:
        fig = go.Figure(data=[go.Pie(labels=['No jobs'], values=[1], hole=0.5)])
    return fig


@status_app.callback(
    Output('textarea-state-example-output', 'children'),
    Input('textarea-state-example-button', 'n_clicks'),
    State('textarea-state-example', 'value'),
    State("username", "data"),
    prevent_initial_call=True
)
def save_scratchpad(n_clicks, value, user_name):
    now = datetime.datetime.now()
    dt = now.strftime("%b-%d-%Y_%H-%M-%S") + ".txt"

    bvalue = base64.b64encode(bytes(value, 'utf-8'))
    decoded = base64.b64decode(bvalue)

    endpoint_id = settings.GLOBUS_USS_EP_ID
    https_server = get_globus_https_server(endpoint_id)
    transfer_url = f'{https_server}/{user_name}/notes/{dt}'
    https_token = None
    try:
        https_token = get_https_token(endpoint_id)
    except Exception as e:
        logger.debug(f'\n\nThe exception is {e}\n\n')

    header = {"Authorization": f"Bearer {https_token}"}
    response = requests.put(transfer_url, data=decoded, headers=header, allow_redirects=False)

    logger.info(f'RESPONSE: \n\n{response.text} -- {header}\n\n')
    # If you want to display the text on page.
    if n_clicks > 0:
        return f'Saved! File at notes/{dt}'


@status_app.callback(
    Output('esearch_results', 'children'),
    Input('esearch', 'value'),
    prevent_initial_call=True
)
def esearch(term):
    esr = ec.esearch(db='pubmed', term=term, )
    paset = ec.efetch(db='pubmed', id=esr.ids, )
    pubs = []
    for doc in paset:
        author_string = ", ".join(doc.authors[:2]) + f"...{doc.authors[-1]}" if len(doc.authors) > 2 else doc.authors
        pubs.append(html.Details([
            html.Summary(doc.title),
            dbc.CardBody([
                html.Div([html.B("Pubmed: "),
                          html.A(doc.pmid, href=f"https://pubmed.ncbi.nlm.nih.gov/{doc.pmid}/", target="_blank")]),
                html.Div([html.B("Authors: "), html.A(author_string)]),
                html.Div([html.B("Abstract: "), html.A(doc.abstract)]),
            ])
        ]))
    return pubs


@status_app.callback(
    Output('massive_search_results', 'children'),
    Input('massive_search_author', 'value'),
    Input('massive_search_keyword', 'value'),
    prevent_initial_call=True
)
def massive_search(author_search, keyword_search):
    for keyword, query in zip([author_search, keyword_search], ['user_input', 'title_input']):
        if keyword != "":
            url = "https://massive.ucsd.edu/ProteoSAFe/QueryDatasets?pageSize=30&offset=0&query={%22" + \
                  "{}".format(query) + "%22:%22" + \
                  "{}".format(keyword) + "%22}"
            response = requests.get(url=url)

            datasets = []
            for dataset in response.json()['row_data']:
                datasets.append(html.Details([
                    html.Summary(dataset['title']),
                    dbc.CardBody([
                        html.Div([
                            html.B("Dataset: "),
                            html.A(
                                dataset['dataset'],
                                target="_blank",
                                href="https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?accession={}".format(
                                    dataset['dataset'])
                            )
                        ]),
                        html.Div([
                            html.B("Contact: "),
                            html.A(dataset['realname'], href="mailto:{}".format(dataset['notification'])),
                            html.A(
                                " (" + dataset['user_id'] + ")",
                                target="_blank",
                                href="https://massive.ucsd.edu/ProteoSAFe/user/summary.jsp?user={}".format(
                                    dataset['user_id'])
                            ),
                        ]),
                        html.Div([html.B("Description: "), html.A(dataset['description'])]),
                        html.Div([html.B("Species: "), html.A(dataset['species_resolved'])]),
                    ])
                ]))
    return datasets


@status_app.callback(Output('output', 'children'),
                     [Input('table', 'data_previous')],
                     [State('table', 'data'), State("username", "data"), ])
def show_removed_rows(previous, current, user_name):
    if previous is None:
        exceptions.PreventUpdate()
    else:
        for row in previous:
            if row not in current:
                move_experiment_to_trash(aggr_nickname=row['job_id'], project=row['Project tag'], user_name=user_name)
        return [f'Moved {row["Name (Click to expand)"]} to trash' for row in previous if row not in current]


@status_app.callback(Output('trash_output', 'children'),
                     [Input('trash', 'data_previous')],
                     [State('trash', 'data'), State("username", "data"), ])
def restore_from_trash(previous, current, user_name):
    if previous is None:
        exceptions.PreventUpdate()
    else:
        for row in previous:
            if row not in current:
                restore_trashed_experiment(aggr_nickname=row['job_id'], project=row['Project tag'], user_name=user_name)
        return [f'Restored {row["Name (Click to expand)"]}' for row in previous if row not in current]


def set_progress(message):
    try:
        return get_progress(message)
    except Exception as e:
        return -1


def delete_sqs_queue(experiment_name):
    session = boto3.session.Session(region_name='us-west-1')
    sqs = session.client(
        'sqs',
        aws_access_key_id=os.environ.get('SQS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('SQS_SECRET_ACCESS_KEY'),
        region_name='us-west-1'
    )

    try:
        queue_url = sqs.get_queue_url(
            QueueName=str(experiment_name).replace('\"', '') + '.fifo'
        )['QueueUrl']
        logger.debug(f'deleting queue url: {queue_url}')
        sqs.delete_queue(QueueUrl=(queue_url))
    except Exception as e:
        logger.error(f"{e}. Problem deleting queue for experiment {experiment_name}")