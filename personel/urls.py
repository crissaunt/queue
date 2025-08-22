from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home ,name='personel'),
    path('start_btn', views.home ,name='start_btn'),
    path('done_current_number', views.done_current_number ,name='done_current_number'),
    path('standby', views.standby ,name='standby'),
    path('priority_standby', views.priority_standby ,name='priority_standby'),
    path('end_all_appointments', views.end_all_appointments ,name='end_all_appointments'),
]