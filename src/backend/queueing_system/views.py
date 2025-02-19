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
import json


request_queue = deque() # Deque used to store requests sent by students
assigned_requests = deque()

def home(request):
    return render(request, 'index.html')


def register(request):
    if request.method == 'POST': 
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            # Redirect users based on user type
            if user.user_type == 'student':
                return redirect('student_dashboard')
            elif user.user_type == 'tutor':
                return redirect('tutor_dashboard')
            elif user.user_type == 'lecturer':
                return redirect('lecturer_dashboard')  # New dashboard for lecturers
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
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                if user.user_type == 'student':
                    return redirect('student_dashboard')
                elif user.user_type == 'tutor':
                    return redirect('tutor_dashboard')
                elif user.user_type == 'lecturer':
                    return redirect('lecturer_dashboard')  # New dashboard
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


@login_required
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

@login_required
def lecturer_dashboard(request):
    # Get all logged-in tutors and students
    tutors = CustomUser.objects.filter(user_type="tutor", is_active=True)
    students = CustomUser.objects.filter(user_type="student", is_active=True)
    
    # Get active requests count
    active_requests = HelpRequest.objects.filter(status="in_progress").count()

    # Get request history
    past_requests = HelpRequest.objects.filter(status="completed")

    return render(request, 'lecturer_dashboard.html', {
        'tutors': tutors,
        'students': students,
        'active_requests': active_requests,
        'past_requests': past_requests,
    })



def submit_request(request):
    if request.method == 'POST':
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.student = request.user
            help_request.save()
            request_queue.append(help_request)

            # Notify all tutors
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "tutors_group",
                {
                    "type": "update_dashboard",
                    "message": f"New help request from {request.user.username}: {help_request.description}",
                    "event_type": "new_request",
                    "request_id": help_request.id,
                    "description": help_request.description,
                    "student": request.user.username,
                }
            )

            #notify lecturer
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "lecturers_group",
                {
                    "type": "update_dashboard",
                    "message": "A new help request has been submitted.",
                    "event_type": "new_request",
                }
            )

            return redirect('student_dashboard')
    else:
        form = HelpRequestForm()
    return render(request, 'submit_request.html', {'form': form})


def accept_request(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk, status='pending')
    help_request.tutor = request.user

    if help_request == request_queue[0]:
        help_request.status = 'in_progress'
        help_request.save()
        request_queue.popleft()
        assigned_requests.append(help_request)

        # Notify the student
        notify_dashboard(
            help_request.student.id,
            f"Your request '{help_request.description}' has been accepted by {request.user.username}.",
            event_type="status_update",
            request_id=help_request.id,
            new_status="in_progress",
            student=help_request.student.username,
            description=help_request.description,
            pc_number=help_request.pc_number
        )

        # Notify the tutor
        notify_dashboard(
            request.user.id,
            f"You have accepted the request '{help_request.description}'.",
            event_type="status_update",
            request_id=help_request.id,
            new_status="in_progress",
            student=help_request.student.username,
            description=help_request.description,
            pc_number=help_request.pc_number
        )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tutors_group",
        {
            "type": "update_dashboard",
            "message": f"The request '{help_request.description}' was accepted by tutor.",
            "event_type": "status_update",
            "request_id": help_request.id,
            "new_status": "in_progress",
            "student": help_request.student.username,
            "description": help_request.description,
            "pc_number": help_request.pc_number
        }
    )        

    return redirect('tutor_dashboard')

def get_all_students(request):
    students = CustomUser.objects.filter(user_type='student')
    data = []
    for student in students:
        has_active_request = HelpRequest.objects.filter(student=student, status="pending").exists()
        has_assigned_tutor = HelpRequest.objects.filter(student=student, status="in_progress").exists()
        data.append({
            "pc_number": student.pc_number,
            "student": student.username,
            "has_request": has_active_request,
            "has_assigned_tutor": has_assigned_tutor,
        })

    print(data)
    return JsonResponse(data, safe=False)

def lab_map(request):
    return render(request, 'lab_map.html')

def mark_completed(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk, status='in_progress')
    help_request.status = 'completed'
    help_request.save()

    # Notify the student
    notify_dashboard(
        help_request.student.id,
        f"Your request '{help_request.description}' has been marked as completed.",
        event_type="status_update",
        request_id=help_request.id,
        new_status="completed",
        student=help_request.student.username,
        description=help_request.description,
        pc_number=help_request.pc_number
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tutors_group",
        {
            "type": "update_dashboard",
            "message": f"The request '{help_request.description}' was marked as completed by tutor.",
            "event_type": "status_update",
            "request_id": help_request.id,
            "new_status": "completed",
            "student": help_request.student.username,
            "description": help_request.description,
            "pc_number": help_request.pc_number
        }
    )

    return redirect('tutor_dashboard')





def cancel_request(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk)

    if request.user == help_request.student:
        help_request.status = 'canceled'
        help_request.save()

        if help_request in request_queue:
            request_queue.remove(help_request)
        elif help_request in assigned_requests:
            assigned_requests.remove(help_request)

        # Notify the student
        notify_dashboard(
            help_request.student.id,
            f"You have canceled the request '{help_request.description}'.",
            event_type="status_update",
            request_id=help_request.id,
            new_status="canceled",
            student=help_request.student.username,
            description=help_request.description,
            pc_number=help_request.pc_number
        )

        # Notify tutors
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "tutors_group",
            {
                "type": "update_dashboard",
                "message": f"The request '{help_request.description}' was canceled by the student.",
                "event_type": "status_update",
                "request_id": help_request.id,
                "new_status": "canceled",
                "student": help_request.student.username,
                "description": help_request.description,
                "pc_number": help_request.pc_number,
            }
        )

    return redirect('student_dashboard')




@login_required
def request_history(request):
    user = request.user
    help_requests = HelpRequest.objects.filter(tutor=user)
    return render(request, 'request_history.html', {'help_requests': help_requests})


#def about_us(request):
    #return render(request, 'about_us.html')


def references(request):
    return render(request, 'references.html')


# Notify students and tutors on the dashboard about updates
def notify_dashboard(user_id, message, event_type=None, request_id=None, new_status=None, description=None, student=None, pc_number=None):
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
            "PC Number": pc_number,
        }
    )

def update_position(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            student = CustomUser.objects.get(username=data["username"])

            student.x_position = data["x"]
            student.y_position = data["y"]
            student.save()

            return JsonResponse({"message": "Position updated successfully"}, status=200)
        except CustomUser.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)