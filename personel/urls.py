from django.urls import path
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Public routes
    path('auth/login/', auth_views.LoginView.as_view(template_name="personel/auth/login.html"), name='auth_login'),
    path('auth/register/', views.register, name='auth_register'),
    path("auth/logout/", auth_views.LogoutView.as_view(next_page="auth_login"), name="auth_logout"),


    # Protected routes (wrap with login_required)
    path('', login_required(views.home)  , name='personel'),
    path('done_current_number', login_required(views.done_current_number) , name='done_current_number'),
    path('standby', login_required(views.standby) , name='standby'),
    path('priority_standby', login_required(views.priority_standby) , name='priority_standby'),
    path('end_all_appointments', login_required(views.end_all_appointments) , name='end_all_appointments'),
]
