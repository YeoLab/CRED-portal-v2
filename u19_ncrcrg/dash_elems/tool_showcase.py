from collections import defaultdict

import dash_bootstrap_components as dbc
from dash import dcc
from django_plotly_dash import DjangoDash

from u19_ncrcrg.tools import valid_pipelines
from .helpers import *
from .navbars import navbar_home, navbar_authenticated
from .. import settings

logger = logging.getLogger(__name__)

tool_showcase_app = DjangoDash('ToolShowcaseApp', external_stylesheets=[settings.BOOTSTRAP_THEME])
STATESDICT = defaultdict(list)




def return_card(tool):
    """
    Returns an html.Div containing the card and its associated modal.
    :param tool:
    :return:
    """
    container_disabled = True if tool['container'] == '' else False
    publication_disabled = True if tool['publication'] == '' else False
    workflow_disabled = True if tool['workflow'] == '' else False

    card = html.Div([
        dcc.Location(id=f"url-{tool['id']}", refresh=True),
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        html.H4(tool['title'], className="card-title"),
                        html.P(tool['description'], className="card-text"),
                        dbc.Row([
                            dbc.Col(
                                dbc.Button(
                                    "Container", color="info", id=f"container-{tool['id']}",
                                    href=f"{tool['container']}", target='_blank', disabled=container_disabled
                                ),
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "Publication", color="info", id=f"publication-{tool['id']}",
                                    href=f"{tool['publication']}", target='_blank', disabled=publication_disabled
                                ),
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "External Link", color="info", id=f"workflow-{tool['id']}",
                                    href=f"{tool['workflow']}", target='_blank', disabled=workflow_disabled
                                ),
                            ),
                        ], ),
                    ]
                ),
            ],
        ),
    ])
    return card


def return_cards_layout(tools, user):
    """
    Controls the look/feel of the card interface.

    :param tools:
    :param base_url: string
      GLOBUS base url
    :return:
    """
    cards = []
    for key in tools.keys():
        cards.append(dbc.Col(return_card(tools[key]), width=4, className='mb-4'))

    nav = navbar_authenticated(user.username) if user.is_authenticated else navbar_home()
    return html.Div([
        nav,
        dbc.Container(
            [
                html.H1("CReD Portal tools"),
                dbc.Row([
                    html.Div(
                        f"""
                        The following tools have been made available for users to download and use with minimal 
                        installation steps required. Each tool has been containerized using Docker and deployed as a 
                        Singularity image to encourage consistent deployment across multiple platforms. Users 
                        may submit/share their own software packages by emailing Brian Yee (bay001 [at] ucsd.edu).
                        """, className='my-2'
                    ),
                    html.Div(
                        """
                        Some of 
                        these workflow tools (ie. Cellranger) are integrated within the portal (no download necessary) 
                        and logged in users are encouraged to use this portal to run these tools directly. 
                        However, should there be a need to re-process separately outside the CReD portal ecosystem, you may 
                        safely download/use these images as they are identical to what is deployed on our cluster. Software 
                        packages (ie. Seurat) for more exploratory analysis are also available for download to minimize 
                        installation dependency conflicts across platforms. Many of these images have been deployed 
                        alongside Jupyter, which users may use to develop Jupyter notebooks containing analysis code. 
                        """, className='my-2'
                    ),
                    html.Div(
                        """
                        We 
                        encourage CReD portal users to use these images to analyze their data as this will make it much 
                        easier to reproduce analysis across groups. For more information on running these images, 
                        click here.
                        """, className='my-2'
                    ),
                ], className='my-4'),
                dbc.Row(cards),
            ],
        ),
    ])


def tool_showcase(base_url, request):
    tools = {}
    pipelines = valid_pipelines()
    for pipeline, obj in pipelines.items():
        pobj = obj(user=None)
        try:
            url = pobj.get_container(base_url)
        except TypeError:
            url = pobj.get_container()

        tools[pipeline] = dict(
            name=pobj.name,
            id=pobj.id,
            title=pobj.name,
            version=pobj.module_version,
            container=url,
            publication=pobj.get_publication(),
            workflow=pobj.get_workflow(),
            description=pobj.get_description(),
        )
    tool_showcase_app.layout = return_cards_layout(tools, request)
    return tool_showcase_app
