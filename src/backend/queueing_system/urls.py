from django.urls import path
from . import views
from .forms import *

urlpatterns = [
# index, admin views here.
    path('', views.index, name='index'),
    path('registeruser/', views.UserSignupView.as_view(), name='student_register'),
    path('login/',views.LoginView.as_view(template_name="login.html", authentication_form=UserLoginForm)),
    path('logout/', views.logout_user, name="logout"),
    path('about_us/', views.about_us, name='about_us')
]


#    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
#    path('tutor/dashboard/', views.tutor_dashboard, name='tutor_dashboard'),4
