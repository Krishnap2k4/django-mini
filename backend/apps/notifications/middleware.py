"""
JWT authentication middleware for WebSocket connections.

Usage: ws://host/ws/notifications/?token=<jwt_access_token>
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import User


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate a JWT access token and return the corresponding user."""
    try:
        token = AccessToken(token_str)
        return User.objects.get(id=token["user_id"])
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Extracts JWT token from the WebSocket query string and
    populates scope["user"] before the consumer runs.
    """

    async def __call__(self, scope, receive, send):
        # If the user is already authenticated via Django sessions, keep it.
        if scope.get("user") and not scope["user"].is_anonymous:
            return await super().__call__(scope, receive, send)

        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token", [])

        if token_list:
            scope["user"] = await get_user_from_token(token_list[0])
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
