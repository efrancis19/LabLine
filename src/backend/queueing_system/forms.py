from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django import forms
from .models import HelpRequest

class CustomUserCreationForm(UserCreationForm): # Form for registering as a new user
    user_type = forms.ChoiceField(choices=CustomUser.USER_TYPE_CHOICES) # User indicates their user type. The user types 'student' and 'tutor' are from the choices in the User model

    class Meta:
        model = CustomUser
        fields = ['user_type', 'username', 'password1', 'password2']   # Fields are inherited from the User model

class HelpRequestForm(forms.ModelForm): # Form for submitting a help request to a tutor as a student
    class Meta:
        model = HelpRequest
        fields = ['description']   # Fields are inherited from the HelpRequest model

class PCNumberForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['pc_number', 'lab_id']