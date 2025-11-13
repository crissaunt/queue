# chat/routing.py
# from django.urls import re_path

# from students import consumers
# from display import display_consumers
# from personel import consumers
# from personel.consumers import QueueConsumer
# from students.consumers import StudentsConsumer

# websocket_urlpatterns = [
#     # re_path(r"ws/students/$", consumers.StudentsConsumer.as_asgi()),
#     re_path(r"ws/display/$", display_consumers.DisplayConsumer.as_asgi()),
#     # re_path(r"ws/queue/$", consumers.QueueConsumer.as_asgi()),

#      re_path(r'ws/queue/$', QueueConsumer.as_asgi()),      # For personnel dashboard
#     re_path(r'ws/students/$', StudentsConsumer.as_asgi()), # For student page
    
# ]


# my_queue/routing.py
from django.urls import re_path
from personel.consumers import QueueConsumer
from students.consumers import StudentsConsumer
from students.consumers import StudentsConsumer
from display.consumers import DisplayConsumer
from survey.consumers import SurveyConsumer


websocket_urlpatterns = [
    re_path(r'ws/queue/$', QueueConsumer.as_asgi()),      # For personnel dashboard
    re_path(r'ws/students/$', StudentsConsumer.as_asgi()), # For student page
    re_path(r"ws/display/$", DisplayConsumer.as_asgi()),
    re_path(r'ws/survey/updates/$',SurveyConsumer.as_asgi()),


]