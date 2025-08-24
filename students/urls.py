from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home ,name='students'),
    path('live_updates', views.live_updates ,name='live_updates'),
]