import dash_bootstrap_components as dbc
from dash import html

from u19_ncrcrg import settings

CRED_LOGO = '/static/images/logos/brain_logo_trans.png'


def navbar_home():
    navbar = \
        dbc.Navbar(
            [
                html.A([html.Img(src=CRED_LOGO, height="65px")], href="/home/", className='text-light', id='home'),
                dbc.NavLink("About", href="/about/", external_link=True, className="text-light", id="about"),
                dbc.NavLink("Upload data", href="/upload-data/", external_link=True, className="text-light",
                            id='upload'),
                dbc.NavLink("Submit a job", href="/submit-job/", external_link=True, className="text-light",
                            id='submit_job'),
                dbc.NavLink("Dashboard", href="/job-status/", external_link=True, className="text-light",
                            id='dashboard'),
                dbc.NavLink("Manage Sharing", href="/sharing/", external_link=True, className="text-light",
                            id='manage_share'),
                dbc.NavLink("Papers", href="/papers/", external_link=True, className="text-light",
                            id='papers'),
                # dbc.NavLink("Search Public Metadata", href="/metadata-search/", external_link=True,
                #             className="text-light", id="meta_data"),
                dbc.NavLink("CReD Portal toolkit", href="/tools/", external_link=True, className="text-light",
                            id="toolkit"),
                dbc.NavLink("FAQs", href="/faqs/", external_link=True, className="text-light", id="faqs"),
                dbc.NavLink("Login", href=settings.LOGIN_URL, external_link=True, id="login",
                            className="ml-auto flex-nowrap mt-3 mt-md-0 text-light", style={"text-color": "right"}),
            ],
            className="navbar navbar-expand-lg navbar-dark bg-dark mb-4",
        )

    return navbar


def navbar_authenticated(username):
    navbar = \
        dbc.Navbar(
            [
                html.A([html.Img(src=CRED_LOGO, height="65px")], href="/home/", className='text-light', id='home'),
                dbc.NavLink("About", href="/about/", external_link=True, className="text-light", id="about"),
                dbc.NavLink("Upload data", href="/upload-data/", external_link=True, className="text-light",
                            id='upload'),
                dbc.NavLink("Submit a job", href="/submit-job/", external_link=True, className="text-light",
                            id='submit_job'),
                dbc.NavLink("Dashboard", href="/job-status/", external_link=True, className="text-light",
                            id='dashboard'),
                dbc.NavLink("Manage Sharing", href="/sharing/", external_link=True, className="text-light",
                            id='manage_share'),
                # dbc.NavLink("Search Public Metadata", href="/metadata-search/", external_link=True,
                #             className="text-light", id="meta_data"),
                dbc.NavLink("Papers", href="/papers/", external_link=True,
                            className="text-light", id='papers'),
                dbc.NavLink("CReD Portal toolkit", href="/tools/", external_link=True, className="text-light",
                            id="toolkit"),
                dbc.NavLink("FAQs", href="/faqs/", external_link=True, className="text-light", id="faqs"),
                html.Div(f"Welcome {username}!", className="ml-auto flex-nowrap mt-3 mt-md-0 text-light", id='user'),
                dbc.NavLink("Logout", href='/accounts/logout/', external_link=True, id="logout",
                            className="auto flex-nowrap mt-3 mt-md-0 text-light", style={"text-color": "right"}),
                dbc.NavLink("Profile", href="/accounts/profile/edit/", external_link=True, id='profile',
                            className="auto flex-nowrap mt-3 mt-md-0 text-light", style={"text-color": "right"}),
            ],
            className="navbar navbar-expand-lg navbar-dark bg-dark mb-4",
        )

    return navbar
