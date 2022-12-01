import dash_bootstrap_components as dbc
from dash import dcc
from django_plotly_dash import DjangoDash

from .helpers import *
from .navbars import navbar_home
from .. import settings

logger = logging.getLogger(__name__)


def return_about_layout():
    """
    Controls the look/feel of the about page interface.

    :param :
    :return:
    """

    return html.Div([
        navbar_home(),
        dbc.Container(
            [
                html.H1("About the CReD Portal"),
                html.H2("Purpose"),
                html.Div(
                    """
                    The purpose of the National Cooperative Reprogrammed Cell Research Groups (NCRCRG) program is 
                    to create multidisciplinary research groups, in partnership with academia and industry, to use 
                    patient-derived reprogrammed cells to develop validated platforms for identifying novel targets 
                    and developing new therapeutics or diagnostic tools to reduce the burden of mental illness.
                    The collaborations will be pre-competitive, meaning that they lie at the interface between basic 
                    academic research and proprietary industrial research and involve cooperation between groups 
                    that might otherwise be competitors, with a focus on optimizing tools and measures needed for 
                    successful translational research. The Funding Opportunity Announcement (FOA) encourages 
                    applications to further develop promising cellular differentiation/characterization protocols 
                    and/or disease-relevant assays using patient-derived reprogrammed cells (e.g., induced 
                    pluripotent stem cells or iPSCs, induced neuronal cells or iNCs). Critical features of these 
                    applications should be (1) a strong emphasis on developing methodology that is robust and 
                    replicable across several performance sites, and (2) cross-paradigm validation to yield 
                    predictive value for pathophysiology.
                    """, className='my-2'
                ),
                html.Br(), html.Br(),
                html.H2("Consortia"),
                html.Div([
                    html.B("NCRCRG:"), """ Per PAR-13-225, these academic-industry partnerships use patient-derived reprogrammed 
                        cells to develop validated platforms for identifying novel targets and developing new therapeutics 
                        or diagnostic tools to reduce the burden of mental illness. The collaborations will be 
                        pre-competitive, meaning that they lie at the interface between basic academic research and 
                        proprietary industrial research and involve cooperation between groups that might otherwise be 
                        competitors, with a focus on optimizing tools and measures needed for successful translational 
                        research. The teams will further develop promising cellular differentiation/characterization 
                        protocols and/or disease-relevant assays using patient-derived reprogrammed cells (e.g., 
                        induced pluripotent stem cells or iPSCs, induced neuronal cells or iNCs). Critical features 
                        of these efforts are (1) a strong emphasis on developing methodology that is robust and 
                        replicable across several performance sites, and (2) cross-paradigm validation with a goal to 
                        yield predictive value for pathophysiology.""", html.Br(), html.Br(),

                    html.B("Convergent Neuroscience (CN):"), """ Per PAR-17-179, teams use multidisciplinary approaches to establish 
                        causal and/or probabilistic linkages across contiguous levels of analysis (e.g., gene, 
                        molecule, cell, circuit, system, behavior) in an explanatory model of psychopathology. The 
                        teams focus on how specific constituent biological processes at one level of analysis contribute 
                        to quantifiable properties at other levels, either directly or as emergent phenomena. 
                        The projects bring together inter/transdisciplinary teams from neuroscience and "orthogonal" 
                        fields (e.g., data/computational science, physics, engineering, mathematics, and environmental 
                        sciences). Teams will develop data-driven theoretical approaches and computational models that
                        connect contiguous levels of analysis, which will be tested experimentally to elucidate biological 
                        underpinnings of complex systems level outcomes in psychopathology.""", html.Br(), html.Br(),
                    ],
                    className='my-2'
                ),

                html.H2("Research Objective"),
                dcc.Markdown(
                    """
                    The CReD Portal will promote collaboration and coordination with any research entities that 
                    have similar goals and will potentiate biological discovery and therapeutics development for 
                    mental illnesses via:
                    - Harmonized data definitions and metadata formats
                    - Unified platform for systematically managing complex cellular phenotype data across teams in order to qualify and validate methods
                    - User-friendly portal for access and multi-modal analysis of the data within the NCRCRGs and across the broader research community.
                    """
                ),
            ], className="container m-4",
        ),
    ])


def about():
    about_app = DjangoDash('AboutApp', external_stylesheets=[settings.BOOTSTRAP_THEME])
    about_app.layout = return_about_layout()
    return about_app
