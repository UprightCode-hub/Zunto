#server/core/authentication.py
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """Allow JWT auth via Authorization header or HttpOnly cookie fallback."""

    cookie_names = ('access_token', 'token', 'jwt', 'access')

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = None
        for cookie_name in self.cookie_names:
            token_value = request.COOKIES.get(cookie_name)
            if token_value:
                raw_token = token_value
                break

        if not raw_token:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            # Ignore stale fallback cookies so public endpoints can still behave anonymously.
            return None

        return self.get_user(validated_token), validated_token


class HeaderAwareSessionAuthentication(SessionAuthentication):
    """Avoid session CSRF checks when a request is clearly using JWT auth."""

    def authenticate(self, request):
        has_auth_header = bool(request.META.get('HTTP_AUTHORIZATION'))
        has_jwt_cookie = any(request.COOKIES.get(name) for name in CookieJWTAuthentication.cookie_names)
        if has_auth_header or has_jwt_cookie:
            return None

        return super().authenticate(request)
