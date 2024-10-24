from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

# Create your models here.

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('tutor', 'Tutor'),
    ]
    
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')

    def __str__(self):
        return self.username
    
class HelpRequest(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="help_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Help request from {self.student.username} at {self.created_at}"