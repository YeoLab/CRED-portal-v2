from django_plotly_dash import DjangoDash

from .helpers import *
from .. import settings


logger = logging.getLogger(__name__)

THEME = settings.BOOTSTRAP_THEME

stop_share_app = DjangoDash('StopShareApp', external_stylesheets=[settings.BOOTSTRAP_THEME])