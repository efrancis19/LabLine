from django.urls import path
from . import consumers
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import queueing_system.routing 

websocket_urlpatterns = [
    path('ws/tutor/', consumers.TutorConsumer.as_asgi()),
]
