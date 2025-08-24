from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home ,name='students'),
    path("submit/", views.student_submit, name="student_submit"),
  
]