from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm, HelpRequestForm, PCNumberForm
from .models import HelpRequest, CustomUser, CanvasLayout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json
from django.contrib import messages
from queueing_system.core.state import ONLINE_TUTORS
from django.contrib.sessions.models import Session
from django.contrib.auth.decorators import user_passes_test
from django.contrib.sessions.backends.db import SessionStore
from datetime import datetime, timezone




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


def student_register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.user_type = 'student'  #  Force student type here
            user.save()
            login(request, user)
            return redirect('choose_lab_and_pc')
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
    lab_pc_count = {    # Indicate the number of PCs available to choose from each lab.
        'lg25': 50,
        'lg26': 50,
    }
    if request.method == "POST":
        form = PCNumberForm(request.POST)
        if form.is_valid():
            pc_number = form.cleaned_data["pc_number"]  # Extract PC number from form.
            lab_id = form.cleaned_data["lab_id"]
            request.user.pc_number = pc_number  # Assign to logged-in user.
            request.user.lab_id = lab_id
            request.user.save() # Save user model.
            messages.success(request, f"Your PC number is {pc_number} in lab {lab_id}.")
            return redirect("student_dashboard")
    else:
        lab_id = request.GET.get('lab_id', None)
        form = PCNumberForm()

        if lab_id in lab_pc_count:
            available_pcs = [(i, str(i)) for i in range(1, lab_pc_count[lab_id] + 1)]   # List the available PCs to choose from.
            form.fields['pc_number'].choices = available_pcs
            form.fields['lab_id'].initial = lab_id

    return render(request, "choose_lab_and_pc.html", {"form": form})


@login_required
def student_dashboard(request):
    user = request.user
    help_requests = HelpRequest.objects.filter(student=user)

    queue = list(
        HelpRequest.objects.filter(status="pending").order_by("created_at")
    )

    AVERAGE_WAIT_PER_REQUEST = 5  # minutes
    request_positions = {
        req.id: idx + 1 for idx, req in enumerate(queue)
    }

    for req in help_requests:
        req.queue_position = request_positions.get(req.id)
        if req.status == "pending" and req.queue_position:
            req.estimated_wait_time = (req.queue_position - 1) * AVERAGE_WAIT_PER_REQUEST
        else:
            req.estimated_wait_time = None

    return render(request, 'student_dashboard.html', {'help_requests': help_requests})




from datetime import datetime, timezone

@login_required
def tutor_dashboard(request):
    user = request.user
    assigned_requests = HelpRequest.objects.filter(tutor=user, status='in_progress')
    pending_requests = HelpRequest.objects.filter(status='pending', tutor=user)

    for req in pending_requests:
        if req.created_at:
            delta = datetime.now(timezone.utc) - req.created_at
            req.waiting_minutes = int(delta.total_seconds() // 60)
        else:
            req.waiting_minutes = 0

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
            lab_name = data.get('name', 'Unnamed Lab')

            for i, PC in enumerate(PCs):
                if 'id' not in PC:
                    PC['id'] = i + 1

            # The user is authenticated and logged in.
            user = request.user

            # Save the lab layout to the database
            layout = CanvasLayout(user=user, name=lab_name, layout_data=json.dumps(PCs))
            layout.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


def view_layouts(request):
    lab_layouts = CanvasLayout.objects.all()  # Get all saved canvas layouts

    return render(request, 'list_saved_labs.html', {
        'layouts': lab_layouts
    })


def get_saved_canvas(request, layout_id):
    layout = get_object_or_404(CanvasLayout, id=layout_id)
    selected_pc = request.GET.get('selected_pc')

    if isinstance(layout.layout_data, str):
        try:
            layout_data = json.loads(layout.layout_data) if isinstance(layout.layout_data, str) else layout.layout_data
        except json.JSONDecodeError:
            layout_data = []
    else:
        layout_data = layout.layout_data

    print("Raw layout_data from DB:", layout_data)

    return render(request, 'get_saved_canvas.html', {
        'layout_data': json.dumps(layout_data),
        'selected_pc': selected_pc,
    })


def delete_layout(request, layout_id):
    if request.method == 'DELETE':
        layout = get_object_or_404(CanvasLayout, id=layout_id)
        
        try:
            # Delete the layout
            layout.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'})



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
                from datetime import datetime, timezone
                delta = datetime.now(timezone.utc) - help_request.created_at
                waiting_minutes = int(delta.total_seconds() // 60)

                async_to_sync(channel_layer.group_send)(
                    f"tutor_{help_request.tutor.id}",
                    {
                        "type": "update_dashboard",
                        "message": f"New help request from {request.user.username}: {help_request.description}",
                        "event_type": "new_request",
                        "request_id": help_request.id,
                        "description": help_request.description,
                        "student": request.user.username,
                        "pc_number": request.user.pc_number,
                        "lab_id": request.user.lab_id,
                        "waiting_minutes": waiting_minutes,  # ✅ Added this!
                    }
                )
            
            # Notify lecturers
            async_to_sync(channel_layer.group_send)(
                "lecturers_group",
                {
                    "type": "update_dashboard",
                    "message": "A new help request has been submitted.",
                    "event_type": "new_request",
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

            channel_layer = get_channel_layer()

            # Calculate queue position and estimated wait time
            pending_queue = HelpRequest.objects.filter(status="pending").order_by("created_at")
            queue_position = list(pending_queue).index(help_request) + 1
            estimated_wait = (queue_position - 1) * 5

            # Notify the student with full details
            notify_dashboard(
                user_id=help_request.student.id,
                message=f"Your request '{help_request.description}' has been received.",
                event_type="status_update",
                request_id=help_request.id,
                new_status="pending",
                description=help_request.description,
                student=help_request.student.username,
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
                "description": help_request.description,
                "pc_number": help_request.student.pc_number,
                "lab_id": help_request.student.lab_id,
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
    # Get the list of active PCs for LG25
    users = CustomUser.objects.filter(lab_id="lg25").values("pc_number")
    activePCs = [user["pc_number"] for user in users]
    
    return render(request, 'lg25_map.html', {'activePCs': activePCs})

def lg26_map(request):
    # Get the list of active PCs for LG26
    users = CustomUser.objects.filter(lab_id="lg26").values("pc_number")
    activePCs = [user["pc_number"] for user in users]
    
    return render(request, 'lg26_map.html', {'activePCs': activePCs})

def pc_data(request):
    lab_id = request.GET.get('lab_id')  # Get lab_id from the query string
    if not lab_id:
        return JsonResponse({'error': 'lab_id is required'}, status=400)

    # Get users from the specific lab
    users = CustomUser.objects.filter(lab_id=lab_id)
    data = []
    for user in users:
        # Check if the user has a request that is pending.
        active_request = HelpRequest.objects.filter(student=user, status='pending').first()
        status = 'pending' if active_request else 'active'

        # Add the PC number, status of the requests associated with it and it's lab location to the data that will be sent as JSON.
        data.append({
            "pc_number": user.pc_number,
            "status": status,
            "lab_id": user.lab_id,
        })

    return JsonResponse(data, safe=False)


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
                "pc_number": request.user.pc_number,
                "lab_id": request.user.lab_id,
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
def notify_dashboard(user_id, message, event_type=None, request_id=None, new_status=None, description=None, student=None, pc_number=None, lab_id=None):
    from datetime import datetime, timezone

    channel_layer = get_channel_layer()
    if not channel_layer:
        print("Channel layer is not configured. Cannot send notifications.")
        return

    queue_position = None
    estimated_wait_time = None
    waiting_minutes = None

    if new_status == "pending" and request_id:
        queue = HelpRequest.objects.filter(status="pending").order_by("created_at")
        for idx, req in enumerate(queue):
            if req.id == request_id:
                queue_position = idx + 1
                estimated_wait_time = (queue_position - 1) * 5
                break

        help_request = HelpRequest.objects.get(id=request_id)
        if help_request.created_at:
            delta = datetime.now(timezone.utc) - help_request.created_at
            waiting_minutes = int(delta.total_seconds() // 60)

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
            "pc_number": pc_number,
            "lab_id": lab_id,
            "queue_position": queue_position,
            "estimated_wait_time": estimated_wait_time,
            "waiting_minutes": waiting_minutes,
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
        


def is_tutor_or_lecturer(user):
    return user.is_authenticated and user.user_type in ['tutor', 'lecturer']

@user_passes_test(is_tutor_or_lecturer)
def force_logout_users(request):
    current_session_key = request.session.session_key

    for session in Session.objects.all():
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if str(user_id) == str(request.user.id):
            continue  # Don't log out the person triggering the logout

        try:
            user = CustomUser.objects.get(id=user_id)
            if user.user_type in ['student', 'tutor']:  # Only log out students and tutors
                session.delete()
        except CustomUser.DoesNotExist:
            pass

    messages.success(request, "All students and tutors (except you) have been logged out.")
    if request.user.user_type == 'tutor':
        return redirect('tutor_dashboard')
    else:
        return redirect('lecturer_dashboard')