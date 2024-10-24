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
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

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


class StudentSignupView(CreateView):
    model = User
    form_class = UserSignupForm
    template_name = 'user_signup.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('/')
    
class TeacherSignupView(CreateView):
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


@login_required
def student_dashboard(request):
    if request.method == "POST" and "request_help" in request.POST:
        # Create a help request for the logged-in student
        HelpRequest.objects.create(student=request.user)

        # Notify all connected tutor clients
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "tutors",  # Group name for tutors
            {
                "type": "notify_tutors",
                "message": f"New help request from {request.user.username}"
            }
        )

        return render(request, 'student_dashboard.html', {'message': "Help request sent!"})
    return render(request, 'student_dashboard.html')


@login_required
def tutor_dashboard(request):
    if request.user.user_type == 'tutor':
        help_requests = HelpRequest.objects.filter(resolved=False)
        return render(request, 'tutor_dashboard.html', {'help_requests': help_requests})
    return redirect('tutor_dashboard.html')

