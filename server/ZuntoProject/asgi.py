"""
ASGI config for ZuntoProject with WebSocket support.
"""

import os
# CRITICAL: Set Django settings FIRST before any other imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')

# Now import Django's ASGI application after settings are configured
from django.core.asgi import get_asgi_application

# Initialize Django ASGI application early to setup Django
django_asgi_app = get_asgi_application()

# NOW import channels stuff AFTER Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from chat import routing

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,

    # WebSocket chat handler
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})