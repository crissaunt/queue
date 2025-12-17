# personel/urls.py
from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

urlpatterns = [
    # Public routes - USE YOUR CUSTOM VIEWS
    path('auth/login/', views.login, name='auth_login'),
    path('auth/register/', views.register, name='auth_register'),
    path('auth/logout/', views.logout, name='auth_logout'),

    # Protected routes
    path('', views.home, name='personel'),
    path('api/queue-data/', views.queue_data_api, name='queue_data_api'),
    path('new/home/', views.new_home, name='new_personel'),
    path('done_current_number/', views.done_current_number, name='done_current_number'),
    path('standby/', views.standby, name='standby'),
    path('priority_standby/', views.priority_standby, name='priority_standby'),
    path('end_all_appointments/', views.end_all_appointments, name='end_all_appointments'),
    path('debug_all_students/', views.debug_all_students, name='debug_all_students'),
     # Queue control
    path('toggle_queue/', views.toggle_queue, name='toggle_queue'),

]