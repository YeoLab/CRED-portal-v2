import dash_bootstrap_components as dbc
from django_plotly_dash import DjangoDash

from .helpers import *
from .navbars import navbar_home, navbar_authenticated
from .. import settings

logger = logging.getLogger(__name__)


def return_help_layout(user):
    """
    Controls the look/feel of the about page interface.

    :param :
    :return:
    """
    nav = navbar_authenticated(user.username) if user.is_authenticated else navbar_home()
    return html.Div([
        nav,
        dbc.Container(
            [
                html.H1("Help & Documentation"),
                dbc.Row([
                    html.Hr(),
                ]),
                dbc.Container([
                    dbc.Row([
                        html.H2("Transferring Data with Globus")
                    ], className='my-4'),
                    dbc.Row([
                        html.P(
                            """
                            Below are some helpful images to follow to help you get accustomed to the Globus 
                            file transfer interface. Transferring your own data to CReD will follow a similar 
                            process, however we have pre-loaded some example data to help you get familiar. 
                            """
                        )
                    ], className='my-4'),
                    dbc.Container([
                        dbc.Row([
                            html.H3("Transferring Example Data to your CReD Portal Collection workspace:"),
                            html.P(
                                """
                                Click the "Upload" or "View/Transfer" buttons, which will bring you to the Globus 
                                file manager. The "View/Transfer" button will take you directly to a folder 
                                (source endpoint) containing example datasets*. 
                                (1) Select the folder corresponding to the tool of your choice.
                                Depending on your previous settings, you may see a single panel or double panel view. (2) 
                                Click the "double pane" view after your folder selection. 
                                """
                            ),
                            html.B(
                                """
                                *If you do not see the CReD Portal endpoint, try clicking the other panel view. 
                                Transfers can be done in either direction!
                                """
                            ),
                            html.Img(src='/static/images/tutorials/example_data_transfer_1.svg'),
                        ], className='my-4'),
                        dbc.Row([
                            html.P(
                                """
                                Within the "double panel" view in the second search box, search for 
                                and select the destination endpoint that you will be transferring files to. If you are 
                                transferring files into CReD, the destination endpoint will be called "CReD Portal Collection." 
                                """
                            ),
                            html.Img(src='/static/images/tutorials/example_data_transfer_2.svg'),
                        ], className='my-4'),
                        dbc.Row([
                            html.P(
                                """
                                Within the CReD Portal Collection, (1) type to navigate to the folder /USERNAME/raw_files/, where 
                                USERNAME will be replaced by the username you used to sign up with. Once selected, (2) 
                                click the "Start" button to initiate the transfer of files FROM the /share/ endpoint to your own. 
                                If the request is successful, there will be a popup display that you can use to monitor the status 
                                of your transfer request. 
                                """
                            ),
                            html.Img(src='/static/images/tutorials/example_data_transfer_3.svg'),
                        ], className='my-4'),
                        # Transfer data from personal laptop
                        dbc.Row([
                            html.H3(
                                "Transferring data from your local machine to your CReD Portal Collection workspace:"),
                            html.P(
                                """
                                Download, install, and configure Globus Connect Personal onto your local machine 
                                (eg. Your MacBook, or your Windows computer). This will establish a collection on your machine 
                                that will allow you to transfer data to and from other collections on Globus. 
                                """
                            ),
                            html.Ul([
                                html.Li(html.A("Instructions for Mac",
                                               href='https://docs.globus.org/how-to/globus-connect-personal-mac/', target="_blank")),
                                html.Li(html.A("Instructions for Windows",
                                               href='https://docs.globus.org/how-to/globus-connect-personal-windows', target="_blank")),
                                html.Li(html.A("Instructions for Linux",
                                               href='https://docs.globus.org/how-to/globus-connect-personal-linux', target="_blank")),
                            ], className="m-4"),
                            html.P(
                                """
                                Users whose universities do not have a institutional subscription to Globus may use 
                                Globus Connect Personal to establish a personal connection from their University's cluster. 
                                Globus provides CReD users with a reliable and secure method for transferring data, however 
                                users assume full responsibility for adhering to data transfer policies set by their university.
                                """
                            ),
                            html.P(
                                """
                                After you have successfully installed Globus Connect Personal, you will need to configure it. 
                                Please follow the application's instructions to login and review the permissions 
                                that Globus will need to manage files on your behalf. Please note the label that you 
                                will provide for your personal collection (1), as you will refer to this label 
                                when searching Globus for your personal connection below. 
                                """
                            ),
                            dbc.Col([
                                html.Img(
                                    src='/static/images/tutorials/example_globus_connect_personal_1.png',
                                    style={"width": "500px"}
                                ),
                            ], className='my-4'),
                            dbc.Col([
                                html.Img(
                                    src='/static/images/tutorials/example_globus_connect_personal_2.png',
                                    style={"width": "500px"}
                                ),
                            ], className='my-4'),
                        ]),
                        dbc.Row([
                            html.P(
                                """
                                Once Globus Connect Personal has been successfully configured, you should see an icon that 
                                shows the status of your connection. 
                                """
                            ),
                            dbc.Col([
                                html.Img(
                                    src='/static/images/tutorials/example_globus_connect_personal_3.png',
                                    style={"width": "200px"}
                                ),
                            ], className='my-4')


                        ], className='my-4'),
                        dbc.Row([
                            html.P([
                                "Navigate to the File Manager (",
                                html.A(
                                    "https://app.globus.org/file-manager",
                                    href="https://app.globus.org/file-manager",
                                    target="_blank"
                                ),
                                """
                                ) and search for (1) your personal collection that you defined above, 
                                as well as for (2) "CReD Portal Collection. (3) Navigate to the file you want to 
                                transfer, and (4) click "Start" to initiate the transfer.
                                """
                            ]),
                            html.Img(src='/static/images/tutorials/example_globus_connect_personal_4.svg'),
                        ], className='my-4'),
                    ])
                ])
            ], className="container m-4",
        ),
    ])


def help_page(user):
    help_app = DjangoDash('HelpApp', external_stylesheets=[settings.BOOTSTRAP_THEME])
    help_app.layout = return_help_layout(user=user)
    return help_app


def tooltip_collection(target="tooltip-collection"):
    return dbc.Tooltip(
        [
            "Collections are discoverable access points that allow data to be transferred through GridFTP " \
            "or HTTPS. For more information, click ",
            html.A(
                "here.",
                href="https://docs.globus.org/globus-connect-server/v5/reference/collection/",
                target="_blank"
            )
        ],
        target=target,
        # autohide=False,
    )


def tooltip_job(target="tooltip-job"):
    return dbc.Tooltip(
        [
            "A Job is a single script that runs a user-specified tool/pipeline using a set of parameters.",
        ],
        target=target,
        # autohide=False,
    )


def tooltip_trash(target="tooltip-trash"):
    return dbc.Tooltip(
        [
            "Trashed job scripts simply remove the job/queue files, but will NOT remove job files on Globus",
        ],
        target=target,
        # autohide=False,
    )


def tooltip_permanent(target="tooltip-permanent"):
    return dbc.Tooltip(
        [
            "Primary storage that persists across user sessions.",
        ],
        target=target,
        # autohide=False,
    )


def tooltip_scratch(target="tooltip-scratch"):
    return dbc.Tooltip(
        [
            "Ephemeral storage that will be deleted after a period of time.",
        ],
        target=target,
        # autohide=False,
    )