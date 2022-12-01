import json
import logging
import os
from collections import OrderedDict
from dash import dcc, html
from urllib.parse import urlparse, parse_qs
import dash_bootstrap_components as dbc
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group, AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from globus_sdk import GroupsAPIError
from rest_framework import permissions
from rest_framework import viewsets

from django_plotly_dash import DjangoDash
from . import settings
from .accounts.views import get_globus_client
from .dash_elems.about import about
from .dash_elems.faqs import faqs
from .dash_elems.help_page import help_page
from .dash_elems.home_dashboard import jobs_by_org
from .dash_elems.job_status import job_status
from .dash_elems.navbars import navbar_home, navbar_authenticated
from .dash_elems.search import metadata_search
from .dash_elems.sharing import share_data, validate_share, confirm_share, get_group_list
from .dash_elems.submit_job import submit_job_page
from .dash_elems.tool_showcase import tool_showcase
from .dash_elems.paper_showcase import paper_showcase_page, publications
from .dash_elems.upload_data import upload_data
from .forms import DynamicForm, PublicationForm
from .serializers import UserSerializer, GroupSerializer
from .settings import GLOBUS_HTTPS_SERVER_BASE_URL
from .tools import valid_pipelines, Job, FasterqdumpJob, DownloaderJob, OmeroDownloaderJob
from .util import create_job

logger = logging.getLogger(__name__)


def logout(request):
    """
    Simple view to log user out. All session variable for the
    user will be deleted.
    """
    for key in list(request.session.keys()):
        del request.session[key]
    context = {'new_user': False}
    if 'new_user' in request.GET.keys():
        context = {'new_user': True}
    return render(request, 'home.html', context)


graph_app = DjangoDash(name='mod_graph', suppress_callback_exceptions=True,
                       external_stylesheets=[settings.BOOTSTRAP_THEME])


def home(request):
    """
    home page view of the django app.
    """
    nav_app = DjangoDash(name='cp_navbar_intro', suppress_callback_exceptions=True,
                         external_stylesheets=[settings.BOOTSTRAP_THEME])

    if request.user and request.user.is_authenticated:
        user = User.objects.get(username=request.user.username)
        nav_app.layout = html.Div(navbar_authenticated(username=user.username))
    else:
        nav_app.layout = html.Div(navbar_home())
    graph_app.layout = dbc.Container([
        dcc.Graph(id="jobs_by_org", figure=jobs_by_org(), responsive=True),  # , style={'height': '45vh'}),
    ], fluid=True)  # fluid=True

    if 'new_user' in request.GET.keys():
        context = {'new_user': True}

    else:
        context = {'new_user': False,
                   'user': request.user,
                   "mod_graph": graph_app.layout,
                   }

    return render(request, 'home.html', context)


def help_view(request):
    # assign anon if user is not logged in
    if request.user:
        user = request.user
    else:
        user = 'AnonymousUser'

    help_app = help_page(user=user)
    context = {"help_app": help_app.layout}
    return render(request, 'help.html', context)


def about_view(request):
    about_app = about()
    context = {"about_app": about_app.layout}
    return render(request, "about.html", context)


def faqs_view(request):
    faqs_app = faqs()
    context = {"faqs": faqs_app.layout}
    return render(request, "FAQs.html", context)


def schedule_consultation(request):
    return render(request, "schedule_consultation.html")


def tool_showcase_view(request):
    try:
        user = User.objects.get(username=request.user.username)
    except ObjectDoesNotExist:
        user = AnonymousUser()
    base_url = settings.GLOBUS_HTTPS_SERVER_BASE_URL
    tv = tool_showcase(base_url, user)
    context = {"tool_showcase_app": tv.layout}
    return render(request, 'tools.html', context)


@login_required
def job_status_view(request):
    """
    This is a wrapper for the job status dash page. It will handle middleware requirements that support
    the job status page as a landing page after globus login.

    :param request: an https request object
           code: issues by the Globus ID Provider. Used to obtain tokens

    :return context: For use in the dash presentation layer
    """

    user = User.objects.get(username=request.user.username)
    js = job_status(user)
    context = {'new_user': False,
               "status_app": js.layout,
               }
    return render(request, 'job-status.html', context)


def metadata_search_view(request):
    try:
        user = User.objects.get(username=request.user.username)
    except ObjectDoesNotExist:
        user = AnonymousUser()
    ms = metadata_search(user)
    context = {"metadata_search_app": ms.layout}
    return render(request, 'metadata-search.html', context)


def set_my_files(request, cred_user, session_key, replace=True, include_root_dir=False, clear=False):
    """
    Parses a GET reponse from the Globus helper page to get a list of user-selected files and folders.

    SET a session variable (file_list) to contain a list of paths relative to a username, sans username

    ie:

    cred_user 'myuser' selects 'raw_files' and 'raw_files/my_file.txt', this function will set a session variable:

    request.session['file_list'] = ['raw_files', 'raw_files/my_file.txt']

    Returns a list of strings corresponding to the path "relative to username"

    :param replace: boolean
        if True, REPLACES the current request.session[session_key] contents with GET request. If False,
        the GET request will be APPENDED to the current contents of request.session[session_key].
    """
    all_files = []
    if clear:
        request.session[session_key] = []
        return all_files

    if session_key not in request.session.keys():
        request.session[session_key] = []
    res = urlparse(request.build_absolute_uri())
    files_dict = parse_qs(res.query)
    try:
        if include_root_dir:
            rel_path = files_dict['path'][0]
        else:
            rel_path = files_dict['path'][0][files_dict['path'][0].find(cred_user) + len(cred_user) + 1:]

        for key, value in files_dict.items():
            if key.split('[')[0] == 'file':
                all_files.append(os.path.join(rel_path, files_dict[key][0]))
            elif key.split('[')[0] == 'folder':
                all_files.append(os.path.join(rel_path, files_dict[key][0] + "/"))
        if replace:
            request.session[session_key] = list(set(all_files))
        else:
            request.session[session_key] = list(set(all_files).union(set(request.session[session_key])))
    except KeyError:
        pass
    return all_files


def paper_showcase_view(request):
    try:
        user = User.objects.get(username=request.user.username)
    except ObjectDoesNotExist:
        user = AnonymousUser()

    if request.method == 'POST':
        geo_accessions = request.POST.getlist('geo_accessions')
        pride_accessions = request.POST.getlist('pride_accessions')
        omero_accessions = request.POST.getlist('omero_accessions')
        logger.debug(request.POST)
        logger.debug('Submitting these accession ids:', geo_accessions)
        if len(geo_accessions) > 0:

            for accession in geo_accessions:
                tool = FasterqdumpJob(user=request.user.username)
                job_metadata = tool.generate_job_submission_document(srr=accession)
                exit_code = create_job(job_metadata=job_metadata, request=request)
                logger.debug(f"exit code for {accession}: {exit_code}")
        if len(pride_accessions) > 0:
            for accession in pride_accessions:
                tool = DownloaderJob(user=request.user.username)
                job_metadata = tool.generate_job_submission_document(url=accession)
                exit_code = create_job(job_metadata=job_metadata, request=request)
                logger.debug(f"exit code for {accession}: {exit_code}")
        if len(omero_accessions) > 0:
            for accession in omero_accessions:
                tool = OmeroDownloaderJob(user=request.user.username)
                job_metadata = tool.generate_job_submission_document(project_id=accession)
                exit_code = create_job(job_metadata=job_metadata, request=request)
                logger.debug(f"exit code for {accession}: {exit_code}")

        return HttpResponseRedirect('/job-status/')
    elif request.method == 'GET':
        forms = OrderedDict()
        paper_app = paper_showcase_page(user)
        logger.debug(request.GET)

        if request.GET.get('reset', '') == 'reset':
            title_term = ''
            author_term = ''
            mesh_keywords = ''
        else:
            title_term = request.GET.get('title_term',
                                         '')  # want to use None here, but if key exists, it defaults to ""
            author_term = request.GET.get('author_term', '')
            mesh_keywords = request.GET.get('mesh_keywords', '')

        for doi, metadata in publications.items():

            d = {
                'name': metadata['title'],
                'authors': metadata['authors'],
                'abstract': metadata['abstract'],
                'full_authors': metadata['full_authors'],
                'doi_link': metadata['doi_link'],
                'pmid_link': metadata['pmid_link'],
                'total_citations': metadata['total_citations'],
                'pub_year': metadata['pub_year'],
                'other_accessions': metadata['other_accessions'],
                'form': PublicationForm(
                    title=metadata['title'],
                    authors=metadata['authors'],
                    full_authors=metadata['full_authors'],
                    abstract=metadata['abstract'],
                    geo_accessions=metadata['geo_accessions'],
                    pride_accessions=metadata['pride_accessions'],
                    omero_accessions=metadata['omero_accessions'],
                    total_citations=metadata['total_citations'],
                    pub_year=metadata['pub_year'],
                )
            }
            if title_term == '' and author_term == '' and mesh_keywords == '':  # show all pubs
                forms[doi] = d
            else:
                if title_term != '' and title_term.upper() in metadata['title'].upper():
                    forms[doi] = d
                if author_term != '' and author_term.upper() in metadata['authors'].upper():
                    forms[doi] = d
                if mesh_keywords != '' and mesh_keywords.upper() in [m.upper() for m in metadata['mesh_keywords']]:
                    forms[doi] = d
    context = {
        "paper_app": paper_app.layout,
        "forms": forms,
        "author_term": author_term,
        "title_term": title_term,
        "mesh_keywords": mesh_keywords
    }

    return render(request, 'papers.html', context)


@login_required
def submit_job_view(request):
    user = User.objects.get(username=request.user.username)
    base_url = GLOBUS_HTTPS_SERVER_BASE_URL

    forms = {}
    form_options = {}
    pipelines = valid_pipelines()
    if request.GET.get('clear_file_list', 'false') == 'true':
        set_my_files(request, user.username, session_key='files_to_use', replace=False, clear=True)
    else:
        set_my_files(request, user.username, session_key='files_to_use', replace=False, clear=False)
    try:
        my_files = request.session['files_to_use']
    except Exception as e:
        logger.error(f"error in returning file list: {e}")
        my_files = []
    submit_app = submit_job_page(user, my_files)

    for pipeline, obj in pipelines.items():
        pobj = obj(user=user)
        if issubclass(type(pobj), Job):

            try:  # if request comes from job-status, it is likely a re-submission.
                json_payload = request.POST['json_payload']
            except KeyError:
                json_payload = None
            form_options[pobj.id] = pobj.get_form_options(json_payload)
            forms[pobj.id] = {
                'name': pobj.name,
                'title': pobj.name,
                'version': pobj.module_version,
                'container': pobj.get_container(base_url),
                'workflow': pobj.get_workflow(),
                'description': pobj.get_description(),

                'form': DynamicForm(
                    dynamic_fields=form_options[pobj.id],
                    user=user.username,
                    my_files=my_files,
                ),
                'obj': pobj
            }
    context = {"submit_app": submit_app.layout, "forms": forms}
    if request.method == 'POST':
        logger.debug(request.POST)
        try:
            tool_id = request.POST['tool_id']
        except KeyError:
            tool_id = json.loads(request.POST['json_payload'])['tool_id']
        form = DynamicForm(
            request.POST,
            dynamic_fields=form_options[tool_id],
            user=user.username,
            my_files=my_files
        )
        if form.is_valid():
            logger.info("FORM DATA: {}".format(form.data))
            job_metadata = forms[tool_id]['obj'].generate_job_submission_document(form.data)
            # TODO: refactor. This needs to be here because SRX metadata may include more than one SRR
            #  (and may potentially require multiple submissions). We might want to make all of these lists to
            #  be consistent, but for now only a few tools return job_metadata as lists.
            if type(job_metadata) == list:
                exit_code = []
                for metadata in job_metadata:
                    logger.info(f"METADATA IS A LIST: {metadata}")
                    exit_code.append(create_job(job_metadata=metadata, request=request))
            else:
                exit_code = create_job(job_metadata=job_metadata, request=request)
            logger.info("EXIT CODE: {}".format(exit_code))
            return HttpResponseRedirect('/job-status/')
    return render(request, 'submit-job.html', context)


@login_required
def upload_data_view(request, code=None):
    """
    This is a wrapper for the upload data dash page. It will handle middleware requirements that support
    the upload data page as a landing page after globus login.

    :param request: an https request object
           code: issues by the Globus ID Provider. Used to obtain tokens

    :return context: For use in the dash presention layer
    """
    user = User.objects.get(username=request.user.username)
    # ome_client = access_omero_server(user=user.username)
    ud = upload_data(user)
    context = {
        'upload_app': ud.layout,
        'user': user,
    }

    return render(request, 'upload-data.html', context)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


def sharing_url(request):
    redirect_url = 'https://app.globus.org/groups'
    return redirect(redirect_url)


@csrf_exempt
def start_sharing_view(request):
    """
    Sharing files and directories start  workflowpage

    :param request: an https request object
           code: issues by the Globus ID Provider. Used to obtain tokens

    :return context: For use in the dash presentation layer
    """
    try:
        user = User.objects.get(username=request.user.username)
    except ObjectDoesNotExist:
        user = AnonymousUser()
    if not user.is_authenticated or user.is_authenticated is None:
        return HttpResponseRedirect('/')
    else:
        try:
            gc = get_globus_client(request=request)['groups']
            my_groups = get_group_list(gc)
        except GroupsAPIError:  # Weird edge case where user is logged in/authenticated, but token expired.
            return HttpResponseRedirect('/accounts/logout/')

        group_guuid, group_name, endpoint_id, path = None, None, None, None
        set_my_files(request, user.username, session_key='files_to_share', include_root_dir=True)

        if request.method == 'GET':
            if 'endpoint' in request.GET:  # sets folder to share

                try:
                    endpoint_id = request.GET.get('endpoint_id', None)
                    request.session['endpoint_id'] = endpoint_id
                    request.session['path'] = request.session['files_to_share']
                    request.session['username'] = user.username
                except Exception as e:
                    logger.error(e)
                    pass
            if 'group' in request.GET:  # sets group to share with
                my_groups = gc.get_my_groups()
                try:
                    group_uuid = request.GET.get('group', None)
                    for group in my_groups:
                        if group['id'] == group_uuid:
                            group_name = group['name']
                    request.session['uuid'] = group_uuid
                    request.session['group_name'] = group_name
                except Exception as e:
                    logger.info('\n\n The error is ', e)
        if request.GET.get('confirm', 'no') == 'yes':
            try:
                confirmed = False
                confirmed_message = None
                validated, validated_message = validate_share(request.session)
                if validated:
                    confirmed, confirmed_message = confirm_share(request.session)

                if validated and confirmed:
                    messages.success(request, "The share has been validated and confirmed.")
                    request.session['uuid'] = None
                    request.session['group_name'] = None
                    request.session['endpoint_id'] = None
                    request.session['path'] = []
                else:
                    for error_message in [validated_message, confirmed_message]:
                        if error_message is not None:
                            messages.error(
                                request,
                                f'The sharing process has an error ({error_message}). '
                                'Please review your selections and try again.'
                            )

            except Exception as e:
                logger.info('The validation/confirmation error is', e)

        sd = share_data(
            user,
            request.session.get('path', []),
            request.session.get('group_name', None),
            my_groups
        )

        context = {
            'user': user,
            'share_app': sd.layout,
        }

        return render(request, 'share-data.html', context)


@login_required
def stop_sharing_view(request, path=None):
    if path is None:
        path = []
    user = User.objects.get(username=request.user.username)
    request.session['username'] = user.username
    client = get_globus_client(request)
    gc = client['groups']
    my_groups = gc.get_my_groups()

    sd = share_data(user, path=path, group_name=None, my_groups=my_groups)

    context = {
        'user': user,
        'share_app': sd.layout,
    }
    return render(request, 'share-data.html', context)