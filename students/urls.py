from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home ,name='students'),
    path("student_submit/", views.student_submit, name="student_submit"),
    path("guest_submit/", views.guest_submit, name="guest_submit"),
  
]