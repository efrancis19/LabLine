from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import *
from django.views.generic import CreateView
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .forms import *
from django.utils import timezone
from .models import User

def index(request):
    user = request.user
    if user.is_anonymous:  
        return render(request, 'index.html')
    elif user.user_type == 'student':
        return render(request, 'student_dashboard.html')
    elif user.user_type == 'tutor':
        return render(request, 'tutor_dashboard.html')
    else:
        return render(request, 'index.html')


class UserSignupView(CreateView):
    model = User
    form_class = UserSignupForm
    template_name = 'user_signup.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('/')
    

class UserLoginView(LoginView):
    template_name = 'login.html'


def logout_user(request):
    logout(request)
    return redirect("/")