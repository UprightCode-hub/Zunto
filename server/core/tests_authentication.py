#server/core/tests_authentication.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from core.authentication import CookieJWTAuthentication


User = get_user_model()


class CookieJWTAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cookie-auth@example.com',
            password='pass123',
            first_name='Cookie',
            last_name='Auth',
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.factory = APIRequestFactory()
        self.auth = CookieJWTAuthentication()

    def test_authenticates_with_cookie_token(self):
        request = self.factory.get('/health/')
        request.COOKIES['access_token'] = self.access_token

        result = self.auth.authenticate(request)

        self.assertIsNotNone(result)
        authenticated_user, _token = result
        self.assertEqual(authenticated_user.id, self.user.id)

    def test_returns_none_without_auth_header_or_cookie(self):
        request = self.factory.get('/health/')

        result = self.auth.authenticate(request)

        self.assertIsNone(result)
