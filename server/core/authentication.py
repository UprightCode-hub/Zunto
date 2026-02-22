#server/core/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication


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

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
