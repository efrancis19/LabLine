from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser): # here we are extending django's built in abstractuser models to support user types
    USER_TYPE_CHOICES = [
        ('student', 'Student'), # Student user type
        ('tutor', 'Tutor'), # Tutor user type
        ('lecturer', 'Lecturer'),
    ]
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES) # User type field
    pc_number = models.IntegerField(default="")

class HelpRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), # Measure the status of requests sent by users
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requests')  # The student who created the request
    tutor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')   # The tutor who has accepted the request
    pc_number = models.CharField(max_length=10) # The PC number of the student who created the request
    description = models.TextField()    # The description of the problem faced by the student
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending') # The status of the request. It is set to 'pending' by default as this indicates that it has not yet been accepted by a lab tutor.
    created_at = models.DateTimeField(auto_now_add=True)    # The time the request was created and sent at
    updated_at = models.DateTimeField(auto_now=True)    # The time of the most recent update to the request (it's status)

class CanvasLayout(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    layout_data = models.JSONField()  # Store the squares as JSON data
    created_at = models.DateTimeField(auto_now_add=True)
