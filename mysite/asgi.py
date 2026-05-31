import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

django_asgi_app = get_asgi_application()

from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

static_asgi_app = ASGIStaticFilesHandler(django_asgi_app)

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from api.consumers import GameConsumer, LobbyConsumer

application = ProtocolTypeRouter({
    'http': static_asgi_app,
    'websocket': URLRouter([
        path('ws/game/<str:game_id>/', GameConsumer.as_asgi()),
        path('ws/lobby/<str:game_id>/', LobbyConsumer.as_asgi()),
    ]),
})