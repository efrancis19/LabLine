from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('register/', views.register, name='register'),
    path('register/student/', views.student_register, name='student_register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('choose_lab_and_pc/', views.choose_lab_and_pc, name='choose_lab_and_pc'),
    path('lg25_map/', views.lg25_map, name='lg25_map'),
    path("api/pc-data/", views.pc_data, name="pc-data"),    
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('tutor_dashboard/', views.tutor_dashboard, name='tutor_dashboard'),
    path('submit_request/', views.submit_request, name='submit_request'),
    path('accept_request/<int:pk>/', views.accept_request, name='accept_request'),
    path('cancel_request/<int:pk>/', views.cancel_request, name='cancel_request'),
    path('mark_completed/<int:pk>/', views.mark_completed, name='mark_completed'),
    path('request_history/', views.request_history, name='request_history'),
    path('lab_map/', views.lab_map, name='lab_map'),
    path('api/get_all_students/', views.get_all_students, name='active_requests'),
    path('api/update_position/', views.update_position, name='update_position'),
    path('lecturer_dashboard/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('create_lab', views.create_lab, name='create_lab'),
    path('save_layout/', views.save_layout, name='save_layout'),
    path('get_saved_canvas/<int:layout_id>/', views.get_saved_canvas, name='get_saved_canvas'),
    path('delete_layout/<int:layout_id>/', views.delete_layout, name='delete_layout'),
    path('logout_all_users/', views.force_logout_users, name='force_logout_users'),
]
