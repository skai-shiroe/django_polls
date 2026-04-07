# c:/Users/skais/Desktop/Labo dev/DJANGO/django_polls/polls/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/polls/<int:poll_id>/', consumers.PollConsumer.as_asgi()),
]
