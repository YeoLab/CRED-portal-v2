from django.contrib import admin
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User

from .models import UserProfile


class SettingsBackend(BaseBackend):
    """
    Authenticate against the settings ADMIN_LOGIN and ADMIN_PASSWORD.

    Use the login name and a hash of the password. For example:

    ADMIN_LOGIN = 'admin'
    ADMIN_PASSWORD = 'pbkdf2_sha256$30000$Vo0VlMnkR4Bk$qEvtdyZRWTcOsCnI/oQ7fVOu1XAURIZYoOZ3iq8Dr4M='
    """

    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Create a new user. There's no need to set a password
            # because only the password from settings.py is checked.
            user = User(username=username)
            user.is_staff = True
            user.is_superuser = True
            user.save()
        return user


    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'lab')

    def user_info(self, obj):
        return obj.description

    def get_queryset(self, request):
        queryset = super(UserProfileAdmin, self).get_queryset(request)
        queryset = queryset.order_by('-lab', 'user')
        return queryset

    user_info.short_description = 'Info'


admin.site.register(UserProfile, UserProfileAdmin)
