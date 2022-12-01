import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input
from django_plotly_dash import DjangoDash
import dash_bootstrap_components as dbc
from .navbars import navbar_home, navbar_authenticated
from .helpers import *

from .. import settings
from ..tools import connect_mongodb

logger = logging.getLogger(__name__)

search_app = DjangoDash('MetadataSearchApp', external_stylesheets=[settings.BOOTSTRAP_THEME])


db = connect_mongodb(database='u19', user=bytes(os.environ.get("MONGODB_USER"), 'utf-8'),
                     password=bytes(os.environ.get("MONGODB_PASSWORD"), 'utf-8'))


def mongodb_search(experiment_nickname, experiment_summary, email_search, tool, db=db):
    results = []
    if experiment_nickname != "":
        experiment_nickname = experiment_nickname.split(' ')
        for term in experiment_nickname:
            for x in (
                    db['Experiments'].find(
                        {"experiment_nickname": {'$regex': "({})".format(term)}, "user": "public"})):  # noqa
                results.append(x)
    if experiment_summary != "":
        for x in (db['Experiments'].find({"$text": {"$search": experiment_summary}, "user": "public"},
                                         {'_txtscr': {'$meta': 'textScore'}}).sort(
            [('_txtscr', {'$meta': 'textScore'})])):  # noqa
            results.append(x)
    if email_search != "":
        for x in db['Experiments'].find({"email": email_search, "user": "public"}):  # noqa
            results.append(x)
        for x in db['Experiments'].find({"contact_email": email_search, "user": "public"}):  # noqa
            results.append(x)
    if tool != "":
        for x in db['Experiments'].find({"module": tool, "user": "public"}):  # noqa
            results.append(x)
    return results


def return_search_layout(user):
    """
    Controls the look/feel of the about metadata search interface.

    :param :
    :return:
    """
    nav = navbar_authenticated(user.username) if user.is_authenticated else navbar_home()
    return html.Div([
        nav,
        dbc.Container([
            dbc.Form([
                html.H2("Search Analyses", className="display-4"),
                html.Hr(),
                dbc.InputGroup([
                    dbc.InputGroupText("Search by job name"),
                    dbc.Input(disabled=False, id="search-name", debounce=True, value="")
                ], className="my-1"),
                dbc.InputGroup([
                    dbc.InputGroupText("Search by email"),
                    dbc.Input(disabled=False, id="search-email", debounce=True, value="")
                ], className="my-1"),
                dbc.InputGroup([
                    dbc.InputGroupText("Search by summary"),
                    dbc.Input(disabled=False, id="search-summary", debounce=True, value="")
                ], className="my-1"),
                dbc.InputGroup([
                    dbc.InputGroupText("Search by tool"),
                    dbc.Input(disabled=False, id="search-tool", debounce=True, value="")
                ], className="my-1"),
                dbc.Button("Primary", color="primary", className="mr-1", id='search', n_clicks=0),
            ]),
            dbc.Container(id='search-results', className="my-2")
        ]),
    ])

@search_app.callback(
    Output("search-results", "children"),
    [
        Input("search", "n_clicks"),
        Input("search-name", "value"),
        Input("search-email", "value"),
        Input("search-summary", "value"),
        Input("search-tool", "value"),
    ]
)
def search_callback(search_btn_nclicks, search_name, search_email, search_summary, search_tool):
    # mongodb_search()
    if search_btn_nclicks > 0:
        results = mongodb_search(
            experiment_nickname=search_name,
            experiment_summary=search_summary,
            email_search=search_email,
            tool=search_tool,
        )
        results_layout = []

        for result in results:
            try:
                experiment_nickname = result['experiment_nickname']
            except KeyError:
                logger.error(f"Search result {result} has no nickname", result)
                experiment_nickname = ''
            try:
                experiment_summary = result['experiment_summary']
            except KeyError:
                logger.error(f"Search result {result} has no summary", result)
                experiment_summary = ''
            try:
                experiment_email = result['email']
            except KeyError:
                logger.error(f"Search result {result} has no email", result)
                experiment_email = ''
            results_layout.append(
                html.Tr(
                    [
                        html.Td(html.Div(experiment_nickname)),
                        html.Td(html.Div(experiment_summary[:200] + '...')),
                        html.Td(html.Div(experiment_email)),
                    ]
                ),
            )
        table_header = [html.Thead(html.Tr([html.Th("Name"), html.Th("Summary"), html.Th("Email")]))]
        results_layout = dbc.Table(
            table_header + results_layout,
            hover=True, responsive=True, striped=True, bordered=True
        )
        return results_layout


def metadata_search(user):
    search_app.layout = return_search_layout(user)
    return search_app
