from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django import forms
from django.forms import ModelForm, ModelChoiceField

from .models import User
from django.db import transaction

class UserSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'user_type')

    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.is_admin = False  # Ensure this is intentional
        user.save()
        return user  # Return the saved user instance, not the class

    
class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Your username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder':'Your password'}))

