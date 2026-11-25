from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/settings/', views.api_course_settings, name='api_settings'),
    path('api/secretary/requests/', views.api_secretary_requests, name='api_secretary_requests'),
    path('api/secretary/requests/<int:request_id>/approve/', views.api_approve_request, name='api_approve_request'),
    path('api/secretary/requests/<int:request_id>/reject/', views.api_reject_request, name='api_reject_request'),
    path('api/secretary/students/', views.api_students_list, name='api_students_list'),
    path('api/secretary/students/<int:student_id>/delete/', views.api_delete_student, name='api_delete_student'),
    path('api/secretary/attendance/toggle/', views.api_attendance_toggle, name='api_attendance_toggle'),
    path('api/secretary/session-note/', views.api_save_session_day_note, name='api_save_session_day_note'),
    path('api/student/<int:student_id>/dashboard/', views.api_student_dashboard, name='api_student_dashboard'),
    path('api/student/<int:student_id>/upload-achievement/', views.api_upload_achievement, name='api_upload_achievement'),
    path('api/student/achievements/<int:achievement_id>/delete/', views.api_delete_achievement, name='api_delete_achievement'),
]
