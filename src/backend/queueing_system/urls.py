from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),    
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('tutor_dashboard/', views.tutor_dashboard, name='tutor_dashboard'),
    path('submit_request/', views.submit_request, name='submit_request'),
    path('accept_request/<int:pk>/', views.accept_request, name='accept_request'),
    path('cancel_request/<int:pk>/', views.cancel_request, name='cancel_request'),
    path('mark_completed/<int:pk>/', views.mark_completed, name='mark_completed'),
    path('request_history/', views.request_history, name='request_history'),
    #path('about_us/', views.about_us, name='about_us'),
    path('references/', views.references, name='references'),
]
