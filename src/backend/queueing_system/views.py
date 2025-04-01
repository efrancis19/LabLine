from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, HelpRequestForm, PCNumberForm
from .models import HelpRequest, CustomUser, CanvasLayout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from collections import deque
import json
from django.contrib import messages
from queueing_system.core.state import ONLINE_TUTORS



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
                return redirect('choose_lab_and_pc')
            elif user.user_type == 'tutor':
                return redirect('tutor_dashboard')
            elif user.user_type == 'lecturer':
                return redirect('lecturer_dashboard')  # New dashboard for lecturers
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        request.user.pc_number = None
        request.user.save()

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
                    return redirect('choose_lab_and_pc')
                elif user.user_type == 'tutor':
                    return redirect('tutor_dashboard')
                elif user.user_type == 'lecturer':
                    return redirect('lecturer_dashboard')  # New dashboard
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

def choose_lab_and_pc(request):
    return render(request, 'choose_lab_and_pc.html')

def choose_lab_and_pc(request):
    if request.method == "POST":
        print("POST received")
        form = PCNumberForm(request.POST)
        if form.is_valid():
            pc_number = form.cleaned_data["pc_number"]  # Extract PC number from form
            lab_id = form.cleaned_data["lab_id"]
            request.user.pc_number = pc_number  # Assign to logged-in user
            request.user.lab_id = lab_id
            request.user.save()  # Save user model
            print(f"User: {request.user}, Entered PC Number: {pc_number} and Lab ID: {lab_id}")
            messages.success(request, f"Welcome! Your PC number is {pc_number}.")
            return redirect("student_dashboard")
    else:
        form = PCNumberForm()

    return render(request, "choose_lab_and_pc.html", {"form": form})


@login_required
def student_dashboard(request):
    user = request.user
    help_requests = HelpRequest.objects.filter(student=user)

    # Fetch global queue to calculate positions
    queue = list(
        HelpRequest.objects.filter(status__in=["pending", "in_progress"]).order_by("created_at")
    )
    request_positions = {
        req.id: idx + 1 for idx, req in enumerate(queue)
    }

    # Add .queue_position to each help_request manually
    for req in help_requests:
        req.queue_position = request_positions.get(req.id)

    return render(request, 'student_dashboard.html', {'help_requests': help_requests})



@login_required
def tutor_dashboard(request):
    #Displays a dashboard for tutors with a list of their assigned and pending requests.
    user = request.user
    assigned_requests = HelpRequest.objects.filter(tutor=user, status='in_progress')
    pending_requests = HelpRequest.objects.filter(status='pending', tutor=user)
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

def create_lab(request):
    return render(request, 'create_lab.html')

def save_layout(request):
    if request.method == 'POST':
        try:
            # Get data from the frontend
            data = json.loads(request.body)
            PCs = data.get('PCs', [])

            for i, PC in enumerate(PCs):
                if 'id' not in PC:
                    PC['id'] = i + 1

            # The user is authenticated and logged in.
            user = request.user

            # Save the lab layout to the database
            layout = CanvasLayout(user=user, layout_data=json.dumps(PCs))
            layout.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def get_saved_canvas(request, layout_id):
    layout = get_object_or_404(CanvasLayout, id=layout_id)

    if isinstance(layout.layout_data, str):
        try:
            layout_data = json.loads(layout.layout_data) if isinstance(layout.layout_data, str) else layout.layout_data
        except json.JSONDecodeError:
            layout_data = []
    else:
        layout_data = layout.layout_data

    print("Raw layout_data from DB:", layout_data)

    return render(request, 'get_saved_canvas.html', {
        'layout_data': json.dumps(layout_data)
    })


def delete_layout(request, layout_id):
    if request.method == 'POST':
        try:
            # Get the lab layout associated with the layout id.
            layout = CanvasLayout.objects.get(id=layout_id, user=request.user)
            layout.delete()
            return JsonResponse({'success': True})
        except CanvasLayout.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Lab Layout not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})



def submit_request(request):
    if request.method == 'POST':
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            help_request = form.save(commit=False)
            help_request.student = request.user
            if ONLINE_TUTORS:
                selected_tutor_id = ONLINE_TUTORS.popleft()
                ONLINE_TUTORS.append(selected_tutor_id)
                selected_tutor = CustomUser.objects.get(id=selected_tutor_id)
                help_request.tutor = selected_tutor

            help_request.save()

            # Notify tutors
            channel_layer = get_channel_layer()
            if help_request.tutor:
                async_to_sync(channel_layer.group_send)(
                    f"tutor_{help_request.tutor.id}",
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

            # Notify the student with status update and queue position
            notify_dashboard(
                user_id=help_request.student.id,
                message=f"Your request '{help_request.description}' has been received.",
                event_type="status_update",
                request_id=help_request.id,
                new_status="pending",
                description=help_request.description,
                student=help_request.student.username,
                pc_number=help_request.pc_number
            )

            return redirect('student_dashboard')
    else:
        form = HelpRequestForm()
    return render(request, 'submit_request.html', {'form': form})


def accept_request(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk, status='pending')

    # Make sure the tutor is only accepting their own assigned request
    if help_request.tutor != request.user:
        return redirect('tutor_dashboard')

    # Mark request as in progress
    help_request.status = 'in_progress'
    help_request.save()

    # Notify the student
    notify_dashboard(
        help_request.student.id,
        f"Your request '{help_request.description}' has been accepted by {request.user.username}.",
        event_type="status_update",
        request_id=help_request.id,
        new_status="in_progress",
        student=help_request.student.username,
        description=help_request.description
    )

    # Notify the assigned tutor (the one accepting it) to update their dashboard
    channel_layer = get_channel_layer()
    if help_request.tutor:
        async_to_sync(channel_layer.group_send)(
            f"tutor_{help_request.tutor.id}",
            {
                "type": "update_dashboard",
                "message": f"The request '{help_request.description}' was accepted.",
                "event_type": "status_update",
                "request_id": help_request.id,
                "new_status": "in_progress",
                "student": help_request.student.username,
                "description": help_request.description
            }
        )
    
    broadcast_queue_positions()

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

def lg25_map(request):
    users = CustomUser.objects.all()
    return render(request, 'lg25_map.html', {'users': users})

def pc_data(request):
    users = CustomUser.objects.all().values("pc_number")
    return JsonResponse(list(users), safe=False)

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
        description=help_request.description
    )

    # Notify assigned tutor to remove from dashboard
    channel_layer = get_channel_layer()
    if help_request.tutor:
        async_to_sync(channel_layer.group_send)(
            f"tutor_{help_request.tutor.id}",

        {
            "type": "update_dashboard",
            "message": f"The request '{help_request.description}' was marked as completed by tutor.",
            "event_type": "status_update",
            "request_id": help_request.id,
            "new_status": "completed",
            "student": help_request.student.username,
            "description": help_request.description
        }
    )
    broadcast_queue_positions()

    return redirect('tutor_dashboard')



def cancel_request(request, pk):
    help_request = get_object_or_404(HelpRequest, pk=pk)

    if request.user == help_request.student:
        help_request.status = 'canceled'
        help_request.save()

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
        if help_request.tutor:
            async_to_sync(channel_layer.group_send)(
                f"tutor_{help_request.tutor.id}",
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

        broadcast_queue_positions()

    return redirect('student_dashboard')




@login_required
def request_history(request):
    user = request.user
    help_requests = HelpRequest.objects.filter(tutor=user)
    return render(request, 'request_history.html', {'help_requests': help_requests})




# Notify students and tutors on the dashboard about updates
def notify_dashboard(user_id, message, event_type=None, request_id=None, new_status=None, description=None, student=None, pc_number=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        print("Channel layer is not configured. Cannot send notifications.")
        return

    # Determine the queue position if the request is still active (pending or in_progress)
    queue_position = None
    if new_status in ["pending", "in_progress"] and request_id:
        pending_requests = HelpRequest.objects.filter(status__in=["pending", "in_progress"]).order_by('created_at')
        for idx, req in enumerate(pending_requests):
            if req.id == request_id:
                queue_position = idx + 1  # 1-based index
                break

    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "update_dashboard",
            "message": message,
            "event_type": event_type,
            "request_id": request_id,
            "new_status": new_status,
            "description": description,
            "student": student,
            "PC Number": pc_number,
            "queue_position": queue_position,  # <-- send position
        }
    )


def broadcast_queue_positions():
    queue = HelpRequest.objects.filter(status__in=["pending", "in_progress"]).order_by("created_at")
    for idx, req in enumerate(queue):
        notify_dashboard(
            user_id=req.student.id,
            message=f"Your queue position has been updated.",
            event_type="status_update",
            request_id=req.id,
            new_status=req.status,
            description=req.description,
            student=req.student.username,
            pc_number=req.pc_number,
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