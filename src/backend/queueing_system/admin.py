from django.contrib import admin
from .models import *
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

# Register your models here.

class UserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('user_type',)}),
    )
admin.site.register(CustomUser, UserAdmin)
admin.site.register(HelpRequest)