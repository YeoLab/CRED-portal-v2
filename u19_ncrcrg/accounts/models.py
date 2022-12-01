from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Extending our User model so we can store extra fields"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    institution = models.CharField(max_length=100, default='')
    lab = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.user.username


def create_profile(strategy, details, response, user, *args, **kwargs):
    """Using the new User object created when a new user registers, we store extra info as a UserProfile"""
    if UserProfile.objects.filter(user=user).exists():
        pass
    else:
        new_profile = UserProfile(user=user)
        new_profile.save()

    return kwargs
