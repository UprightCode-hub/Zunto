# server/chat/jwt_middleware.py
"""
JWT authentication middleware for Django Channels WebSocket connections.

AuthMiddlewareStack only resolves session cookies. This middleware reads
a JWT access token from the ?auth= query param and populates scope['user'].

The ?token= query param is the conversation-specific HMAC ws_token — a
different thing. Never try to JWT-decode ?token=.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async
def get_user_from_jwt(token_str):
    """
    Validate a JWT access token and return the corresponding User,
    or AnonymousUser if the token is invalid/expired.
    """
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        user_id = AccessToken(token_str)['user_id']
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Resolves JWT access tokens for WebSocket scopes.

    Reads from ?auth=<jwt_access_token> in the query string.
    The ?token= param is the HMAC ws_token for conversation verification
    and must not be touched here.
    """

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)

        # Already authenticated via session
        if scope.get('user') and getattr(scope['user'], 'is_authenticated', False):
            return await super().__call__(scope, receive, send)

        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        auth_token = params.get('auth', [None])[0]

        if auth_token:
            scope['user'] = await get_user_from_jwt(auth_token)

        return await super().__call__(scope, receive, send)