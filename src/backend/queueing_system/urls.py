from django.urls import path
from . import views
from .forms import *

urlpatterns = [
# index, admin views here.
    path('', views.index, name='index'),
    path('registerstudent/', views.StudentSignupView.as_view(), name='student_register'),
    path('registerteacher/', views.TeacherSignupView.as_view(), name='register_teacher'),
    path('login/',views.LoginView.as_view(template_name="login.html", authentication_form=UserLoginForm)),
    path('logout/', views.logout_user, name="logout"),
]