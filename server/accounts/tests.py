#server/accounts/tests.py
import io
from contextlib import redirect_stdout

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from notifications.email_service import EmailService
from .models import PendingRegistration, SellerProfile, VerificationCode

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

    def test_registration_creates_inactive_account_pending_email_verification(self):
        response = self.client.post(self.register_url, self.user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertNotIn('access', response.data)
        self.assertTrue(response.data['verification_required'])
        user = User.objects.get(email=self.user_data['email'])
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_verified)
        self.assertFalse(PendingRegistration.objects.filter(email=self.user_data['email']).exists())
        self.assertTrue(
            VerificationCode.objects.filter(
                user__email=self.user_data['email'],
                code_type='email',
                is_used=False,
            ).exists()
        )

    def test_registration_verify_marks_user_verified_and_returns_tokens(self):
        initiate = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(initiate.status_code, status.HTTP_201_CREATED)

        verification = VerificationCode.objects.get(user__email=self.user_data['email'], code_type='email')
        verify_payload = {
            'email': self.user_data['email'],
            'code': verification.code,
        }
        response = self.client.post(self.verify_registration_url, verify_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

        user = User.objects.get(email=self.user_data['email'])
        self.assertTrue(user.is_verified)
        self.assertTrue(user.is_active)
        self.assertFalse(PendingRegistration.objects.filter(email=self.user_data['email']).exists())

    def test_resend_registration_code(self):
        initiate = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(initiate.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            self.resend_registration_url,
            {'email': self.user_data['email']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)


    def test_registration_requires_phone_number(self):
        payload = self.user_data.copy()
        payload.pop('phone')

        response = self.client.post(self.register_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data)

    def test_registration_sends_verification_email(self):
        from django.core import mail

        response = self.client.post(self.register_url, self.user_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertIn(self.user_data['email'], mail.outbox[-1].to)

    def test_resend_registration_sends_email(self):
        from django.core import mail

        initiate = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(initiate.status_code, status.HTTP_201_CREATED)
        initial_count = len(mail.outbox)

        response = self.client.post(
            self.resend_registration_url,
            {'email': self.user_data['email']},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(mail.outbox), initial_count)
        self.assertIn(self.user_data['email'], mail.outbox[-1].to)


    def test_resend_registration_code_respects_cooldown(self):
        initiate = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(initiate.status_code, status.HTTP_201_CREATED)

        first = self.client.post(
            self.resend_registration_url,
            {'email': self.user_data['email']},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            self.resend_registration_url,
            {'email': self.user_data['email']},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_login_blocks_unverified_user_with_resend_message(self):
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
        self.assertIn('Email verification required', str(response.data['detail']))

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
        self.assertIn('is_staff', response.data['user'])

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_console_email_backend_prints_verification_code(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            sent = EmailService.send_verification_email_to_recipient(
                recipient_email='console-code@example.com',
                recipient_name='Console Code',
                code='123456',
            )

        self.assertTrue(sent)
        output = buffer.getvalue()
        self.assertIn('[Zunto email verification] console-code@example.com code: 123456', output)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST_USER='',
        EMAIL_HOST_PASSWORD='',
    )
    def test_unconfigured_smtp_defers_verification_email(self):
        sent = EmailService.send_verification_email_to_recipient(
            recipient_email='deferred-code@example.com',
            recipient_name='Deferred Code',
            code='123456',
        )

        self.assertFalse(sent)

    def test_logout_prefers_jwt_over_session_csrf(self):
        user = User.objects.create_user(
            email='logout-csrf@example.com',
            password='TestPass123!',
            first_name='Logout',
            last_name='CSRF',
            is_verified=True,
        )
        refresh = RefreshToken.for_user(user)
        csrf_client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(csrf_client.login(email=user.email, password='TestPass123!'))
        csrf_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = csrf_client.post(
            '/api/accounts/logout/',
            {'refresh_token': str(refresh)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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


class SellerRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/seller/register/'
        self.user = User.objects.create_user(
            email='buyer-upgrade@example.com',
            password='TestPass123!',
            first_name='Buyer',
            last_name='Upgrade',
            role='buyer',
            is_verified=True,
        )

    def test_seller_registration_requires_authentication(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_registration_creates_pending_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['seller_profile_status'], SellerProfile.STATUS_PENDING)
        self.assertTrue(response.data['isSellerPending'])
        self.assertFalse(response.data['isSellerActive'])

        profile = SellerProfile.objects.get(user=self.user)
        self.assertEqual(profile.status, SellerProfile.STATUS_PENDING)
        self.assertFalse(profile.is_verified_seller)
