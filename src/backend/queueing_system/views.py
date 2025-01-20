from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, HelpRequestForm
from .models import HelpRequest, CustomUser
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from collections import deque

request_queue = deque() # Deque used to store requests sent by students
assigned_requests = deque()

def home(request):
    return render(request, 'index.html')


def register(request):
    if request.method == 'POST': 
        form = CustomUserCreationForm(request.POST) # Load the form for registering from forms.py
        if form.is_valid(): # If the user's login input is valid
            user = form.save()
            login(request, user)
            return redirect('student_dashboard' if user.user_type == 'student' else 'tutor_dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')  # Redirect to the login page after logout


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password) # Authenticate and login the user that matches the details entered in the login form
            if user is not None: # If the details entered match with an existing user
                login(request, user)  # Logs in the user
                if user.user_type == 'student':
                    return redirect('student_dashboard')  # Redirect to student dashboard if user is a student
                elif user.user_type == 'tutor':
                    return redirect('tutor_dashboard')  # Redirect to tutor dashboard if user is a tutor
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def student_dashboard(request):
    user = request.user
    help_requests = HelpRequest.objects.filter(student=user) # Lists the help requests in HelpRequest where the student field matches that of the logged in user
    return render(request, 'student_dashboard.html', {'help_requests': help_requests})


@login_required
def tutor_dashboard(request):
    #Displays a dashboard for tutors with a list of their assigned and pending requests.
    user = request.user
    assigned_requests = HelpRequest.objects.filter(tutor=user, status='in_progress')
    pending_requests = HelpRequest.objects.filter(status='pending')
    return render(request, 'tutor_dashboard.html', {
        'assigned_requests': assigned_requests,
        'pending_requests': pending_requests,
    })


def submit_request(request):
    if request.method == 'POST':
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.student = request.user # Associate the request with the logged-in student
            help_request.save()
            request_queue.append(help_request) # Add the request to the queue
            print(request_queue)

            # Notify tutors about the new request
            tutors = CustomUser.objects.filter(user_type='tutor')
            for tutor in tutors:
                notify_dashboard(
                    tutor.id,
                    f"New help request created by {request.user.username}: {help_request.description}",
                    event_type="new_request",
                    request_id=help_request.id,
                    description=help_request.description,
                    student=request.user.username,
                )
            return redirect('student_dashboard')  # Redirect after successful submission
    else:
        form = HelpRequestForm()  # Initialize an empty form for GET requests

    return render(request, 'submit_request.html', {'form': form})


def accept_request(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk, status='pending')
    help_request.tutor = request.user
    if help_request == request_queue[0]:
        help_request.status = 'in_progress' # Change the status of the request to 'in_progress' to reflect it being accepted by a tutor
        help_request.save()
        request_queue.popleft() # Pop the request from the queue since a tutor has accepted it
        assigned_requests.append(help_request)
        print(request_queue)
        print(assigned_requests)

        # Notify student and tutor
        notify_dashboard(
        help_request.student.id,
        f"Your request '{help_request.description}' has been accepted by {request.user.username}.",
        event_type="status_update",
        request_id=help_request.id,
        new_status="in_progress",
        student=help_request.student.username,
        description=help_request.description,
    )
        notify_dashboard(
        request.user.id,
        f"You have accepted the request '{help_request.description}'.",
        event_type="status_update",
        request_id=help_request.id,
        new_status="in_progress",
        student=help_request.student.username,
        description=help_request.description,
    )
    else:
        print("This request is not first in the queue!")
    
    return redirect('tutor_dashboard')


def mark_completed(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk, status='in_progress')
    help_request.status = 'completed'
    help_request.save()

    # Notify both student and tutor
    notify_dashboard(help_request.student.id, f"Request {help_request.description} has been completed.",
                     event_type="status_update", request_id=help_request.id, new_status="completed")
    notify_dashboard(request.user.id, f"You've marked the request {help_request.description} as completed.",
                     event_type="status_update", request_id=help_request.id, new_status="completed")

    return redirect('tutor_dashboard')



def cancel_request(request, pk):
    # Fetch the help request
    help_request = get_object_or_404(HelpRequest, pk=pk)

    # Check if the user is the student who created the request
    if request.user == help_request.student:
        help_request.status = 'canceled'
        help_request.save()
        if help_request in request_queue:
            request_queue.remove(help_request)  # Remove the request from the queue since it has been cancelled
            print(request_queue)
        elif help_request in assigned_requests:
            assigned_requests.remove(help_request)
            print(request_queue)

        # Notify the student (their own cancellation) and their assigned tutor about it.
        notify_dashboard(
            help_request.student.id,
            f"You have canceled the request '{help_request.description}'.",
            event_type="status_update",
            request_id=help_request.id,
            new_status="canceled",
            student=help_request.student.username,  # Added student username
            description=help_request.description,  # Added description
        )

        # Notify the tutor (if assigned)
        if help_request.tutor:
            notify_dashboard(
                help_request.tutor.id,
                f"The request '{help_request.description}' has been canceled by the student.",
                event_type="status_update",
                request_id=help_request.id,
                new_status="canceled",
                student=help_request.student.username,  # Added student username
                description=help_request.description,  # Added description
            )

    # Redirect back to the student dashboard after cancellation
    return redirect('student_dashboard')


@login_required
def request_history(request):
    user = request.user
    help_requests = HelpRequest.objects.filter(tutor=user)
    return render(request, 'request_history.html', {'help_requests': help_requests})


def about_us(request):
    return render(request, 'about_us.html')


def references(request):
    return render(request, 'references.html')


# Notify students and tutors on the dashboard about updates
def notify_dashboard(user_id, message, event_type=None, request_id=None, new_status=None, description=None, student=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        print("Channel layer is not configured. Cannot send notifications.")
        return
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "update_dashboard",  # Matches the method in the consumer
            "message": message,
            "event_type": event_type,  # Event type like 'new_request' or 'status_update'
            "request_id": request_id,  # ID of the request being updated
            "new_status": new_status,  # New status of the request
            "description": description,  # Description of the request (if applicable)
            "student": student,  # Student username (if applicable)
        }
    )