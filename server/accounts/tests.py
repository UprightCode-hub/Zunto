#server/accounts/tests.py
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from .models import PendingRegistration

User = get_user_model()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthenticationFlowTestCase(TestCase):
    """Covers registration verification and login constraints."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/accounts/register/'
        self.verify_registration_url = '/api/accounts/register/verify/'
        self.resend_registration_url = '/api/accounts/register/resend/'
        self.login_url = '/api/accounts/login/'
        self.profile_url = '/api/accounts/profile/'

        self.user_data = {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+2348012345678',
            'role': 'buyer',
        }

    def test_registration_initiates_pending_record(self):
        response = self.client.post(self.register_url, self.user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertFalse(User.objects.filter(email=self.user_data['email']).exists())
        self.assertTrue(PendingRegistration.objects.filter(email=self.user_data['email']).exists())

    def test_registration_verify_creates_user_and_tokens(self):
        initiate = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(initiate.status_code, status.HTTP_200_OK)

        pending = PendingRegistration.objects.get(email=self.user_data['email'])
        verify_payload = {
            'email': self.user_data['email'],
            'code': pending.verification_code,
        }
        response = self.client.post(self.verify_registration_url, verify_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

        user = User.objects.get(email=self.user_data['email'])
        self.assertTrue(user.is_verified)
        self.assertFalse(PendingRegistration.objects.filter(email=self.user_data['email']).exists())

    def test_resend_registration_code(self):
        initiate = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(initiate.status_code, status.HTTP_200_OK)

        response = self.client.post(
            self.resend_registration_url,
            {'email': self.user_data['email']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)

    def test_login_blocks_unverified_user(self):
        User.objects.create_user(
            email='unverified@example.com',
            password='TestPass123!',
            first_name='Unverified',
            last_name='User',
            is_verified=False,
        )

        response = self.client.post(
            self.login_url,
            {'email': 'unverified@example.com', 'password': 'TestPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_verified_user(self):
        User.objects.create_user(
            email='verified@example.com',
            password='TestPass123!',
            first_name='Verified',
            last_name='User',
            is_verified=True,
        )

        response = self.client.post(
            self.login_url,
            {'email': 'verified@example.com', 'password': 'TestPass123!'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_get_user_profile(self):
        user = User.objects.create_user(
            email='profile@example.com',
            password='TestPass123!',
            first_name='Profile',
            last_name='User',
            is_verified=True,
        )

        self.client.force_authenticate(user=user)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], user.email)
