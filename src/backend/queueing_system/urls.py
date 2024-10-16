from django.urls import path
from . import views
from .forms import *

urlpatterns = [
   path('', views.index, name="index"),
   path('sign_up/', views.UserSignupView.as_view(), name="sign_up"),
   path('login/',views.LoginView.as_view(template_name="login.html", authentication_form=UserLoginForm)),
   path('logout/', views.logout_user, name="logout"),
] 