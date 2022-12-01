import dash_bootstrap_components as dbc
from django_plotly_dash import DjangoDash

from .helpers import *
from .navbars import navbar_home
from .. import settings

logger = logging.getLogger(__name__)


def return_faqs_layout():
    """
    Controls the look/feel of the about page interface.

    :param :
    :return:
    """

    return html.Div([
        navbar_home(),
        dbc.Container(
            [
                html.H1("CReD Portal FAQs"),
                html.Ul([
                    html.Li(html.A('What is the CReD Portal?', href="#what_is_cred", target="_self")),
                    html.Li(html.A('Do you need to subscribe to CReD?', href="#subscribe", target="_self")),
                    html.Li(html.A('What is Globus?', href="#globus", target="_self")),
                    html.Li(html.A('What is ORCID?', href="#orcid", target="_self")),
                    html.Li(html.A('What resources does CReD provide?', href="#resources", target="_self")),
                    html.Li(html.A('What analysis tools does CReD provide?', href="#tools", target="_self")),
                    html.Li(html.A('Will I be notified when my job is complete?', href="#notify", target="_self")),
                    html.Li(html.A('How do you upload files in CReD?', href="#upload1", target="_self")),
                    html.Li(html.A('How do you share files in CReD?', href="#share", target="_self")),
                    html.Li(html.A('Is Jupyter Notebook available in CReD?', href="#jupyter", target="_self")),
                ]
                ),
                html.H3("What is the CReD Portal?", style={"color": "Teal"}, id="what_is_cred"),
                html.P("The Cell Reprogramming Database or CReD Portal is a workspace for conducting research into "
                       "the genetic composition of neuronal cells that may be related to disorders affecting the "
                       "brain."
                       ),
                html.Hr(),
                html.H3("Do you need to subscribe to CReD?", style={"color": "Teal"}, id="subscribe"),
                html.P("You do need to register in the CReD Portal and to log into use most of the features in the "
                       "portal. Fortunately, the subscription process is fairly simple. You will be asked to log "
                       "in using one of three methods, using your Globus, Google or ORCID login"
                       ),
                html.Hr(),
                html.H3("What is Globus?", style={"color": "Teal"}, id="globus"),
                html.P("Globus is a service utilized by CReD to perform a number of functions including "
                       "authentication, file streaming and sharing. In the context of registration, Globus provides "
                       "an interface between the portal and thousands of authenticating providers. These providers "
                       "represent most of the academic and research institutions worldwide. You likely belong to one "
                       "of these institutions. Try logging in using the globus option first. If you cannot find and "
                       "institution you are associated with you can use Google or ORCID as an authenticator"

                       ),
                html.Hr(),
                html.H3("What is ORCID?", style={"color": "Teal"}, id="orcid"),
                html.P(["ORCID or Open Researcher and Contributor ID is a non-proprietary alphanumeric code to uniquely "
                       "identify authors and contributors of scholarly communication as well as ORCID's website and "
                       "services to look up authors and their bibliographic output (and other user-supplied "
                       "pieces of information). "

                       "This addresses the problem that a particular author's contributions to the scientific "
                       "literature or publications can be hard to recognize as most personal names are not unique, "
                       "they can change (such as with marriage), have cultural differences in name order, contain "
                       "inconsistent use of first-name abbreviations and employ different writing systems. It provides "
                       "a persistent identity for humans, similar to tax ID numbers, that are created for "
                       "content-related entities on digital networks by digital object identifiers (DOIs). You can "
                       "obtain an ORCID ", html.A('here', href='https://orcid.org/register')]
                       ),
                html.Hr(),
                html.H3("What resources does CReD provide?", style={"color": "Teal"}, id="resources"),
                html.P("CReD provides a number of underlying, integrated resources. These include compute resources in "
                       "the form of multiple multiprocessing capable nodes in the TSCC cluster. Storage resources from "
                       "the Universal Storage Services (USS) hosted at the San Diego Supercomputer Center at UCSD and "
                       "the S3 services hosted by Amazon Web Services (AWS) fr document storage, database resources "
                       "using MongoDB for storing job related meta-data, authentication, file sharing and file "
                       "streaming provided by Globus, plus a variety of job control related resources related to "
                       "queuing, scheduling, containerizing and reporting"),
                html.Hr(),
                html.H3("What analysis tools does CReD provide?", style={"color": "Teal"}, id="tools"),
                html.P("CReD currently provides 15 tools to use with datasets to create jobs and growing. These tools "
                       "covers four modalities, genomics, proteomics, electron physiology and imaging the graphic "
                       "below shows the current stock of tools:"),
                html.Img(src="/static/images/analysis_tools.png", alt="Tools at CReD"),
                html.P("More tools are being added all the time. If you have a tool you wish to add to the  portal "
                       "please contact wcwest@health.ucsd.edu or brian.alan.yee@gmail.com"),
                html.Hr(),
                html.H3("Will I be notified when my job is complete?", style={"color": "Teal"},
                        id="notify"),
                html.P("Yes. You will receive an email informing you if your job completed successfully or failed."),
                html.Hr(),
                html.H3("How do you upload files in CReD?", style={"color": "Teal"}, id="upload1"),
                html.P("CReD uses a micoservice of Globus to upload files. It does so by moving files between valid"
                       "Globus access points. To upload files from your local machine, you will need to download"
                       "a piece of software called Globus Personal Server from here: "
                       "https://www.globus.org/globus-connect-personal . This software has a port for Macintosh, "
                       "Linux and Windows. "),
                html.P([f"Please log in to get complete instructions on installing Globus Personal "
                       f"and File Uploading ", html.A('here', href=f'{settings.CRED_BASE_URL}/upload-data/')]),
                html.Hr(),
                html.H3("How do you share files in CReD?", style={"color": "Teal"}, id="share"),
                html.P("CReD uses a micoservice of Globus to share files. There are a series of steps requred to "
                       "set up shared files. "),
                html.P("    1. Create a group  - A group is a collection of 1 or more users you wish to share files."),
                html.P("    2. Share a folder - designate a folder that contains the files you wish to share and the"),
                html.P("       share type - read or read/write"),
                html.P("    3. Assign a group to the shared folders - combine step 1 and 2"),
                html.Nobr(),
                html.P("You can also remove a share. "),
                html.P([f"Please log in to get complete instructions on File Sharing ", html.A('here', href=f'{settings.CRED_BASE_URL}/sharing/')]), # noqa
                html.Hr(),
                html.H3("Is Jupyter Notebook available in CReD?", style={"color": "Teal"}, id="jupyter"),
                html.P(["Yes. You can create a Jupyter Notebook ", html.A('here', href=f'{settings.CRED_BASE_URL}/job-status/')]), # noqa
                html.Hr(),

            ])])


def faqs():
    faqs_app = DjangoDash('FAQs', external_stylesheets=[settings.BOOTSTRAP_THEME])
    faqs_app.layout = return_faqs_layout()
    return faqs_app
