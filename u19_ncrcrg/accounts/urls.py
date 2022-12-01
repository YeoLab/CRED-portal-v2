from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path

from . import views

app_name = 'accounts'

urlpatterns = [
    re_path(r'^login/globus/$', auth_views.LoginView
        .as_view(template_name='accounts/login.html'), name='login'),
    re_path(r'^logout/$', views.logout, name='logout'),
    re_path(r'^profile/edit/$', views.edit_profile, name='edit_profile'),
    re_path(r'^change-password/$', views.change_password, name='change_password'),
    re_path(r'^reset-password/$', auth_views.PasswordResetView.as_view(), {
        'template_name': 'accounts:reset_password.html',
        'post_reset_redirect': 'accounts:password_reset_done',
        'email_template_name': 'accounts:reset_password_email'
    }, name='reset_password'),

]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),

                  ] + urlpatterns
