from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.


class UserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('user_type',)}),
    )
admin.site.register(User, UserAdmin)