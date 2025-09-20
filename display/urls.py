from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home ,name='display'),  
    path('current_serving', views.current_serving ,name='current_serving'),  
]