from django import forms
# from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.forms import ModelForm


from .models import UserProfile
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    lab = forms.CharField(required=True)
    institution = forms.CharField(required=True)

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'lab',
            'institution',
            'password1',
            'password2'
        )

    # def __str__(self):
    #     return self.email

    def save(self, commit=True):
        user = super(RegistrationForm, self).save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.lab = self.cleaned_data['lab']
        user.institution = self.cleaned_data['institution']
        user.is_active = False

        if commit:
            user.save()

        return user

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data['username']
        email = cleaned_data['email']
        user_model = get_user_model()  # your way of getting the User
        try:
            user_model.objects.get(username__iexact=username)
            self.add_error("username", "Username already exists!")
        except user_model.DoesNotExist:
            pass
        try:
            user_model.objects.get(email__iexact=email)
            self.add_error("email", "Email already exists!")
        except user_model.DoesNotExist:
            pass
        try:
            assert username.lower() == username
        except AssertionError:
            self.add_error("username", "Use only lower case values.")


class EditProfileForm(ModelForm):

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
        )


class ProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ('lab', 'institution')  # Note that we didn't mention user field here.
