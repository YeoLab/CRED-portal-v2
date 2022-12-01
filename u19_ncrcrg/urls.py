from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from rest_framework import routers

from . import views

router = routers.SimpleRouter()

urlpatterns = [
    re_path(r'^$', views.home, name='home'),

    path('home/', views.home, name='home'),
    path('accounts/', include('u19_ncrcrg.accounts.urls')),
    re_path(r'^sharing/$', views.start_sharing_view, name="sharing"),
    re_path(r'^unsharing/(?P<path>.*)$', views.stop_sharing_view, name="unsharing"),
    re_path(r'^job-status/$', views.job_status_view, name="job-status"),
    re_path(r'^submit-job/$', views.submit_job_view, name="submit-job"),
    re_path(r'^upload-data/(?P<code>.*)$', views.upload_data_view, name="upload-data"),
    re_path(r'^metadata-search/$', views.metadata_search_view, name="metadata-search"),
    re_path(r'^about/$', views.about_view, name="about"),
    re_path(r'^faqs/$', views.faqs_view, name="faqs"),
    re_path(r'^tools/$', views.tool_showcase_view, name="tools"),
    re_path(r'^papers/$', views.paper_showcase_view, name="papers"),
    path('schedule_consultation/', views.schedule_consultation,
         name='schedule_consultation'),
    path('mendel/', admin.site.urls),
    path('help/', views.help_view, name='help'),
    re_path(r'^static/(?P<path>.*)$', serve,
        {'document_root': settings.STATIC_ROOT}),
    path('', include('django.contrib.auth.urls')),
    path('', include('social_django.urls', namespace='social')),
    re_path('^django_plotly_dash/', include('django_plotly_dash.urls')),
    re_path(r'^accounts/profile/$', views.job_status_view, name='job-status'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),

                  ] + urlpatterns


CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379),],
        },
    },
}
