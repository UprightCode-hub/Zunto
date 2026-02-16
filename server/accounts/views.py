# accounts/views.py
from datetime import timedelta
import random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from notifications.email_service import EmailService
from notifications.tasks import send_verification_email_task, send_welcome_email_task
from .models import PendingRegistration, VerificationCode
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    EmailVerificationSerializer,
    GoogleAuthSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationInitiateSerializer,
    RegistrationResendSerializer,
    RegistrationVerifySerializer,
    UserProfileSerializer,
)

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except Exception:  # pragma: no cover
    id_token = None
    google_requests = None


User = get_user_model()


@method_decorator(ratelimit(key='ip', rate='50/h', method='POST'), name='post')
class UserRegistrationView(generics.CreateAPIView):
    """
    Initiate registration: store pending data and send email code.
    A User account is created only after /register/verify/ succeeds.
    """

    queryset = PendingRegistration.objects.all()
    serializer_class = RegistrationInitiateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        code = self.generate_verification_code()
        expires_at = timezone.now() + timedelta(minutes=15)

        PendingRegistration.objects.update_or_create(
            email=data['email'],
            defaults={
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'phone': data.get('phone'),
                'role': data.get('role', 'buyer'),
                'seller_commerce_mode': data.get('seller_commerce_mode', 'direct'),
                'password_hash': make_password(data['password']),
                'verification_code': code,
                'code_expires_at': expires_at,
            },
        )

        email_sent = EmailService.send_verification_email_to_recipient(
            recipient_email=data['email'],
            recipient_name=f"{data['first_name']} {data['last_name']}".strip(),
            code=code,
        )

        if not email_sent:
            return Response(
                {
                    'error': (
                        'Unable to send verification email right now. '
                        'Check email configuration and try again.'
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                'message': 'Verification code sent. Verify code to complete registration.',
                'email': data['email'],
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def generate_verification_code():
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])


@method_decorator(ratelimit(key='ip', rate='20/h', method='POST'), name='post')
class VerifyRegistrationView(APIView):
    """Verify pending registration code and create the actual account."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistrationVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        try:
            pending = PendingRegistration.objects.get(email=email)
        except PendingRegistration.DoesNotExist:
            return Response(
                {'error': 'No pending registration found for this email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pending.is_expired():
            pending.delete()
            return Response(
                {'error': 'Verification code has expired. Request a new code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pending.verification_code != code:
            return Response(
                {'error': 'Invalid verification code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=email).exists():
            pending.delete()
            return Response(
                {'error': 'An account already exists for this email. Please login.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if pending.phone and User.objects.filter(phone=pending.phone).exists():
            return Response(
                {'error': 'A user with this phone number already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                user = User(
                    email=pending.email,
                    first_name=pending.first_name,
                    last_name=pending.last_name,
                    phone=pending.phone,
                    role=pending.role,
                    seller_commerce_mode=pending.seller_commerce_mode,
                    is_verified=True,
                )
                user.password = pending.password_hash
                user.save()
                pending.delete()
        except IntegrityError:
            return Response(
                {
                    'error': (
                        'Could not complete registration due to conflicting account data.'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            send_welcome_email_task.delay(str(user.id))
        except Exception:
            EmailService.send_welcome_email(user)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_verified': user.is_verified,
                    'seller_commerce_mode': user.seller_commerce_mode,
                    'is_managed_seller': user.is_managed_seller,
                    'profile_picture': (
                        user.profile_picture.url if user.profile_picture else None
                    ),
                },
                'message': 'Registration completed successfully.',
            },
            status=status.HTTP_201_CREATED,
        )


@method_decorator(ratelimit(key='ip', rate='10/h', method='POST'), name='post')
class ResendRegistrationCodeView(APIView):
    """Resend code for an existing pending registration."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistrationResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'An account already exists for this email. Please login.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pending = PendingRegistration.objects.get(email=email)
        except PendingRegistration.DoesNotExist:
            return Response(
                {'error': 'No pending registration found for this email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pending.verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        pending.code_expires_at = timezone.now() + timedelta(minutes=15)
        pending.save()

        email_sent = EmailService.send_verification_email_to_recipient(
            recipient_email=pending.email,
            recipient_name=f"{pending.first_name} {pending.last_name}".strip(),
            code=pending.verification_code,
        )

        if not email_sent:
            return Response(
                {
                    'error': (
                        'Unable to send verification email right now. '
                        'Check email configuration and try again.'
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {'message': 'Verification code resent successfully.'},
            status=status.HTTP_200_OK,
        )


@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='post')
class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login endpoint with user data"""

    serializer_class = CustomTokenObtainPairSerializer


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='10/h', method='POST'), name='post')
class GoogleAuthView(APIView):
    """
    Authenticate user with Google OAuth token.
    Endpoint: POST /api/accounts/auth/google/
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if id_token is None or google_requests is None:
            return Response(
                {
                    'error': (
                        'Google authentication is not available. '
                        'Install google-auth dependency on the backend.'
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            return Response(
                {'error': 'GOOGLE_OAUTH_CLIENT_ID is not configured on the backend.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        token = serializer.validated_data['token']

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID,
            )

            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            google_id = idinfo.get('sub')
            email_verified = idinfo.get('email_verified', False)

            if not email:
                return Response(
                    {'error': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not email_verified:
                return Response(
                    {'error': 'Google email is not verified'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing_google_user = User.objects.filter(google_id=google_id).first()
            if existing_google_user and existing_google_user.email.lower() != email.lower():
                return Response(
                    {'error': 'This Google account is already linked to another user.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user, created = User.objects.get_or_create(
                email=email.lower(),
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_verified': True,
                    'role': 'buyer',
                    'google_id': google_id,
                },
            )

            if user.google_id and user.google_id != google_id:
                return Response(
                    {'error': 'This email is linked to a different Google account.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not user.google_id:
                user.google_id = google_id
                user.save(update_fields=['google_id'])

            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'role': user.role,
                        'is_verified': user.is_verified,
                        'seller_commerce_mode': user.seller_commerce_mode,
                        'is_managed_seller': user.is_managed_seller,
                        'profile_picture': (
                            user.profile_picture.url if user.profile_picture else None
                        ),
                    },
                    'message': 'Account created successfully' if created else 'Login successful',
                },
                status=status.HTTP_200_OK,
            )

        except ValueError as exc:
            return Response(
                {'error': 'Invalid Google token', 'details': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {'error': 'Authentication failed', 'details': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change user password"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            user = request.user

            if not user.check_password(serializer.data.get('old_password')):
                return Response(
                    {'old_password': ['Wrong password.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.set_password(serializer.data.get('new_password'))
            user.save()

            return Response(
                {'message': 'Password changed successfully.'},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def Home(request):
    context = {
        'content': 'Welcome to Home Page, by Aikay',
        'superuser': 'Superuser Email:contact@user.com',
        'personnal': 'Personnal Information',
    }
    return render(request, 'accounts/Home.html', context)


class LoginPageView(View):
    """Render the login HTML page"""

    def get(self, request):
        return render(request, 'marketplace/auth/login.html')


class RegisterPageView(View):
    """Render the registration HTML page"""

    def get(self, request):
        return render(request, 'marketplace/auth/register.html')


class LogoutView(APIView):
    """Logout endpoint"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({'message': 'Logout successful.'}, status=status.HTTP_200_OK)
        except Exception:
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    """Verify user email for already-authenticated users"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)

        if serializer.is_valid():
            code = serializer.validated_data.get('code')
            user = request.user

            try:
                verification = VerificationCode.objects.get(
                    user=user,
                    code=code,
                    code_type='email',
                    is_used=False,
                )

                if verification.is_expired():
                    return Response(
                        {'error': 'Verification code has expired.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                user.is_verified = True
                user.save(update_fields=['is_verified'])

                verification.is_used = True
                verification.save(update_fields=['is_used'])

                return Response(
                    {'message': 'Email verified successfully.'},
                    status=status.HTTP_200_OK,
                )

            except VerificationCode.DoesNotExist:
                return Response(
                    {'error': 'Invalid verification code.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationCodeView(APIView):
    """Resend verification code for authenticated user"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.is_verified:
            return Response(
                {'message': 'Email is already verified.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=15)

        VerificationCode.objects.create(
            user=user,
            code=code,
            code_type='email',
            expires_at=expires_at,
        )

        try:
            send_verification_email_task.delay(str(user.id), code)
        except Exception:
            EmailService.send_verification_email(user, code)

        return Response(
            {'message': 'Verification code sent successfully.'},
            status=status.HTTP_200_OK,
        )


@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='post')
class PasswordResetRequestView(APIView):
    """Request password reset"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data.get('email')

            try:
                user = User.objects.get(email=email)

                code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                expires_at = timezone.now() + timedelta(minutes=15)

                VerificationCode.objects.create(
                    user=user,
                    code=code,
                    code_type='password_reset',
                    expires_at=expires_at,
                )

                EmailService.send_password_reset_email(user, code)

                return Response(
                    {'message': 'Password reset code sent to your email.'},
                    status=status.HTTP_200_OK,
                )

            except User.DoesNotExist:
                return Response(
                    {'message': 'If this email exists, a reset code has been sent.'},
                    status=status.HTTP_200_OK,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Confirm password reset with code"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            code = serializer.validated_data.get('code')
            new_password = serializer.validated_data.get('new_password')

            try:
                user = User.objects.get(email=email)
                verification = VerificationCode.objects.get(
                    user=user,
                    code=code,
                    code_type='password_reset',
                    is_used=False,
                )

                if verification.is_expired():
                    return Response(
                        {'error': 'Reset code has expired.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                user.set_password(new_password)
                user.save()

                verification.is_used = True
                verification.save(update_fields=['is_used'])

                return Response(
                    {'message': 'Password reset successfully.'},
                    status=status.HTTP_200_OK,
                )

            except (User.DoesNotExist, VerificationCode.DoesNotExist):
                return Response(
                    {'error': 'Invalid email or reset code.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
