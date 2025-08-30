# chat/routing.py
from django.urls import re_path

from students import students_consumers
from display import display_consumers

websocket_urlpatterns = [
    re_path(r"ws/students/$", students_consumers.StudentsConsumer.as_asgi()),
    re_path(r"ws/display/$", display_consumers.DisplayConsumer.as_asgi()),
]