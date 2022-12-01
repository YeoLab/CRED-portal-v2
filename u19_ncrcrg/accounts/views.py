import logging

import globus_sdk
import jsonpickle
# import omero.clients

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from globus_sdk import AuthClient, TransferClient, AccessTokenAuthorizer, GroupsClient

from .forms import EditProfileForm, ProfileForm
from .. import settings

logger = logging.getLogger(__name__)


@login_required
def view_profile(request, pk=None):
    if pk:
        user = User.objects.get(pk=pk)
    else:
        user = request.user
    args = {'user': user}
    return render(request, 'accounts/edit_profile.html', args)


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request,
                             'Your password was successfully updated!')
            return HttpResponseRedirect('/accounts/change-password/?pwchanged=True')  # noqa
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {
        'form': form
    })


def reset_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(data=request.POST, user=request.user)

        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return redirect(reverse('accounts:login'))
        else:
            return redirect(reverse('accounts:reset_password'))
    else:
        form = PasswordChangeForm(user=request.user)

        args = {'form': form}
        return render(request, 'accounts/reset_password.html', args)


def csrf_failure(request, reason=None):
    """
    If authentication time runs out, display this view.
    :param request:
    :param reason:
    :return:
    """
    ctx = \
        {'message': 'Authentication timeout, please login again to continue.'}
    return render(request, 'accounts/csrf_failure.html', ctx)


def logout(request):
    """
    - Revoke the tokens with Globus Auth.
    - Destroy the session state.
    - Redirect the user to the Globus Auth logout page.
    :params request: a Django Http request object
    :return redirect to the globus logout page
    """

    client = load_portal_client()

    # Deserialize and revoke the tokens with Globus Auth
    for key in request.session.keys():
        if key == 'tokens':
            tokens = jsonpickle.decode(request.session["tokens"])
            access_token = tokens['access_token']
    access_token = request.session.get('AUTH_TOKEN', None)

    if request.user.is_authenticated:
        try:
            client.oauth2_revoke_token(access_token)
            django_logout(request)
        except Exception as e:
            logger.info(e)

    request.session.clear()

    ga_logout_url = (
            'https://auth.globus.org/v2/web/logout' +
            '?client={}'.format(settings.SOCIAL_AUTH_GLOBUS_KEY) +
            '&redirect_uri={}'.format(settings.GLOBUS_LOGOUT_URI) +
            '&redirect_name=CReD Portal Logout')

    # Redirect the user to the Globus Auth logout page
    return redirect(ga_logout_url)


def load_portal_client():
    """Create an AuthClient for the portal"""
    return globus_sdk.ConfidentialAppAuthClient(
        settings.SOCIAL_AUTH_GLOBUS_KEY, settings.SOCIAL_AUTH_GLOBUS_SECRET)


@login_required
def edit_profile(request):
    user = User.objects.get(username=request.user.username)
    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=user.userprofile)
        try:
            if form.is_valid() and profile_form.is_valid():
                user_form = form.save()
                custom_form = profile_form.save(False)
                custom_form.user = user_form
                custom_form.save()
                return redirect('accounts:edit_profile')
        except ValueError:
            pass
    else:
        form = EditProfileForm(instance=user)
        profile_form = ProfileForm(instance=user.userprofile)
        args = {'form': form, 'profile_form': profile_form}
        return render(request, 'accounts/edit_profile.html', args)


def setup_uss_env(user):
    """
    if a user is new to CReD set up the directory structure for them n the USS and
    add them to the acl list for that endpoint with rw permissions
    :param user: New user object
    :return: Nothing
    """

    endpoint_id = settings.GLOBUS_USS_EP_ID

    # jupyterhub_endpoint_id = settings.GLOBUS_JUPYTER_EP_ID
    user = User.objects.get(username=user)
    social_state = user.social_auth.filter(provider="globus")
    ac = get_globus_client(user_social_state=social_state)['auth']

    try:
        user_info = ac.oauth2_userinfo()
    except AttributeError as ae:
        return HttpResponseRedirect('/accounts/logout/')
    cred_admin = None
    cred_jupyter_admin = None

    try:
        cred_admin = get_admin_client()
        # cred_jupyter_admin = get_admin_client(endpoint_id=jupyterhub_endpoint_id)

    except Exception as e:
        logger.debug(f"Couldn't authorize using tokens {cred_admin}\n\n")

    path = f'/'
    dir_list = []
    try:
        dir_list = cred_admin.operation_ls(endpoint_id, path=path)
    except Exception as e:
        logger.error('\n\n The dir list error is ', e)

    dir_flag = False
    for uss_dir in dir_list:
        if user.username == uss_dir["name"]:
            dir_flag = True

    # TODO: re-factor once CReD starts managing the Jupyterhub collection.
    # try:
    #     path = f'/{user.username}/'
    #     cred_jupyter_admin.operation_mkdir(jupyterhub_endpoint_id, path=path)
    #     rw_data = {
    #         "DATA_TYPE": "access",
    #         "principal_type": "identity",
    #         "principal": user_info["sub"],
    #         "path": path,
    #         "permissions": "rw",
    #     }
    #     cred_jupyter_admin.add_endpoint_acl_rule(endpoint_id, rw_data)

    # except Exception as e:
    #     logger.error(f'Root dir exception (Jupyterhub collection) {e}')
    #     pass

    if not dir_flag:
        try:
            path = f'/{user.username}/'
            cred_admin.operation_mkdir(endpoint_id, path=path)
        except Exception as e:
            logger.debug(f'Root dir exception {e}')

        try:
            path = f'/{user.username}/raw_files/'
            cred_admin.operation_mkdir(endpoint_id, path=path)
            rw_data = {
                "DATA_TYPE": "access",
                "principal_type": "identity",
                "principal": user_info["sub"],
                "path": path,
                "permissions": "rw",
            }
            cred_admin.add_endpoint_acl_rule(endpoint_id, rw_data)
        except Exception as e:
            logger.debug(f'Raw data dir exception {e}')
            pass
        try:
            cred_admin.operation_mkdir(endpoint_id, path=f'/{user.username}/json_files/')
        except Exception as e:
            logger.debug(f'JSON Files dir exception {e}')
            pass
        try:
            path = f'/{user.username}/results/'
            cred_admin.operation_mkdir(endpoint_id, path=path)
            r_data = {
                "DATA_TYPE": "access",
                "principal_type": "identity",
                "principal": user_info["sub"],
                "path": path,
                "permissions": "r",
            }
            cred_admin.add_endpoint_acl_rule(endpoint_id, r_data)
        except Exception as e:
            logger.debug(f'Results dir exception {e}')
            pass
        try:
            path = f'/{user.username}/notes/'
            cred_admin.operation_mkdir(endpoint_id, path=path)
            rw_data = {
                "DATA_TYPE": "access",
                "principal_type": "identity",
                "principal": user_info["sub"],
                "path": path,
                "permissions": "rw",
            }
            cred_admin.add_endpoint_acl_rule(endpoint_id, rw_data)
        except Exception as e:
            logger.debug(f'Notes dir exception {e}')
            pass


def get_globus_tokens(scopes):
    """
    Method for returning tokens given a list of scopes.
    If there is more than one scope

    :param scopes: list
        list of scopes (eg.
            scopes = [
                f'https://auth.globus.org/scopes/{endpoint_id}/https',
            ]
        )
    """
    portal_client = load_portal_client()
    # get OAuth tokens for scopes
    tokens = portal_client.oauth2_client_credentials_tokens(
        requested_scopes=scopes
    )
    return tokens


def get_admin_client(endpoint_id=settings.GLOBUS_USS_EP_ID):
    """This function is to produce admin credentials for use in file and endpoint related operations
    :return: an site transfer client object
    """
    portal_client = load_portal_client()
    scopes = [f'https://auth.globus.org/scopes/{endpoint_id}/https',
              'urn:globus:auth:scope:transfer.api.globus.org:all']
    tokens = portal_client.oauth2_client_credentials_tokens(
        requested_scopes=scopes)

    # transfer token
    transfer_token_info = (
        tokens.by_resource_server["transfer.api.globus.org"])
    transfer_token = transfer_token_info["access_token"]

    # get a TransferClient to find the base URL
    transfer_client = globus_sdk.TransferClient(
        authorizer=globus_sdk.AccessTokenAuthorizer(transfer_token))

    return transfer_client


def get_globus_https_server(endpoint_id):
    """
    Returns https server url for a given collection endpoint id
    """
    tokens = get_globus_tokens(
        scopes=['urn:globus:auth:scope:transfer.api.globus.org:all']
    )
    transfer_token_info = (
        tokens.by_resource_server["transfer.api.globus.org"]
    )
    transfer_token = transfer_token_info["access_token"]

    # get a TransferClient to find the base URL
    transfer_client = globus_sdk.TransferClient(
        authorizer=globus_sdk.AccessTokenAuthorizer(transfer_token)
    )

    # get the endpoint (collection info)
    endpoint = transfer_client.get_endpoint(endpoint_id)

    # HTTPS server base URL, no trailing slash
    # example: https://g-96b3c4.0ed28.75bc.data.globus.org
    https_server = endpoint['https_server']
    return https_server


def get_https_token(endpoint_id):
    """
    Helper function that obtains a token to authorize https puts,
    returns response
    """
    # OAuth2 scopes, transfer and HTTPS access
    https_token = None
    try:
        tokens = get_globus_tokens(
            scopes=[f'https://auth.globus.org/scopes/{endpoint_id}/https', ]
        )

        # https access token
        https_token_info = (
            tokens.by_resource_server[endpoint_id]
        )
        https_token = https_token_info["access_token"]
    except Exception as e:
        logger.debug(f'\n\nError getting tokens {e}\n\n')

    return https_token


def get_globus_tokens_by_state(user_social_state):
    extra_data = user_social_state.get().extra_data
    tokens = {}
    tokens['auth.globus.org'] = {'access_token': extra_data['access_token'],
                                 'refresh_token': extra_data['refresh_token']}
    if 'other_tokens' in extra_data:
        for t in extra_data['other_tokens']:
            tokens[t['resource_server']] = {'access_token': t['access_token'],
                                            'refresh_token': t['refresh_token']}

    logger.debug('\n\n The tokens are', tokens)
    return tokens


def get_globus_client(request=None, user_social_state=None):
    """Get a client based on the requesting user's social_auth
    :param:request HTTP Request Object
    :return: a dictionary of clients based on tokens
    """
    clients = {}
    tokens = {}
    if request:
        user_social_state = request.user.social_auth

    try:
        tokens = get_globus_tokens_by_state(user_social_state)
    except Exception as e:
        logger.debug('\n\n the globus client error is ', e)

    resource_servers = ['auth.globus.org', 'transfer.api.globus.org', 'groups.api.globus.org']

    for resource in resource_servers:
        access_token = tokens[resource]['access_token']
        authorizer = AccessTokenAuthorizer(access_token)
        if resource == 'auth.globus.org':
            clients['auth'] = AuthClient(authorizer=authorizer)
        elif resource == 'transfer.api.globus.org':
            clients['transfer'] = TransferClient(authorizer=authorizer)
        elif resource == 'groups.api.globus.org':
            clients['groups'] = GroupsClient(authorizer=authorizer)

    return clients


def access_omero_server(**kwargs):
    OMERO_USER = kwargs.get('user')
    OMERO_PASSWORD = settings.OMERO_PASSWORD
    HOST = 'cred-portal-vm.ucsd.edu'
    PORT = 4064
    conn_list = [OMERO_USER, OMERO_PASSWORD, HOST, PORT]

    return conn_list


