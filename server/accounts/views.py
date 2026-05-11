#server/accounts/views.py
from datetime import timedelta
import logging
import random
import threading

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.core.cache import cache
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
from notifications.tasks import (
    send_verification_email_to_recipient_task,
    send_welcome_email_task,
)
from accounts.seller_utils import (
    get_seller_application_status,
    get_seller_commerce_mode,
    get_seller_profile,
    is_active_seller,
    is_pending_seller,
    is_verified_seller,
)
from .models import PendingRegistration, SellerApplication, SellerProfile, VerificationCode
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
except Exception:                    
    id_token = None
    google_requests = None


User = get_user_model()
logger = logging.getLogger(__name__)


RESEND_COOLDOWN_SECONDS = getattr(settings, 'REGISTRATION_RESEND_COOLDOWN_SECONDS', 60)


def _should_include_debug_code():
    return bool(getattr(settings, 'DEBUG', False) or not getattr(settings, 'IS_PRODUCTION', False))


def _attach_debug_code(payload, email, code):
    if _should_include_debug_code():
        payload['debug_code'] = code
        print(f'[Zunto debug] registration resend code for {email}: {code}', flush=True)
    return payload


def _queue_verification_email(recipient_email, recipient_name, code):
    """Fire-and-forget verification email dispatch."""
    delivery_will_defer = EmailService.is_smtp_backend_unconfigured()
    should_isolate_eager_task = (
        getattr(settings, 'IS_PRODUCTION', False)
        and getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
    )

    def dispatch_task():
        try:
            send_verification_email_to_recipient_task.apply_async(
                args=[recipient_email, recipient_name, code],
                retry=False,
            )
            return True
        except Exception as exc:
            logger.warning(
                "Verification email dispatch failed for %s: %s",
                recipient_email,
                exc,
            )
            return False

    try:
        if should_isolate_eager_task:
            # Render free tier runs eager Celery in the web process; isolate it from the request.
            threading.Thread(
                target=dispatch_task,
                name='verification-email-dispatch',
                daemon=True,
            ).start()
            return not delivery_will_defer
        else:
            return dispatch_task() and not delivery_will_defer
    except Exception as exc:
        logger.warning(
            "Verification email dispatch thread failed for %s: %s",
            recipient_email,
            exc,
        )
        return False


def _create_email_verification(user, code=None):
    verification_code = code or UserRegistrationView.generate_verification_code()
    VerificationCode.objects.filter(user=user, code_type='email', is_used=False).update(is_used=True)
    VerificationCode.objects.create(
        user=user,
        code=verification_code,
        code_type='email',
        expires_at=timezone.now() + timedelta(minutes=15),
    )
    return verification_code


def _issue_auth_payload(user, message, *, email_sent=None, status_code=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)
    payload = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': _user_payload(user),
        'message': message,
        'verification_required': not user.is_verified,
    }
    if email_sent is not None:
        payload['email_delivery_status'] = 'sent' if email_sent else 'deferred'
    return Response(payload, status=status_code)


def _registration_pending_payload(user, email_sent, *, status_code=status.HTTP_201_CREATED):
    if email_sent:
        message = 'Account created. We sent a verification code to your email.'
    else:
        message = (
            'Account created, but we could not send the verification email right now. '
            'Please use Resend Code on the verification page.'
        )

    return Response(
        {
            'message': message,
            'email': user.email,
            'verification_required': True,
            'email_delivery_status': 'sent' if email_sent else 'deferred',
        },
        status=status_code,
    )


def _resend_cooldown_key(email, scope=''):
    return f"registration_resend_cooldown:{email}:{scope}"


def _resend_available(email, scope=''):
    return cache.get(_resend_cooldown_key(email, scope)) is None


def _set_resend_cooldown(email, scope=''):
    cache.set(_resend_cooldown_key(email, scope), True, timeout=RESEND_COOLDOWN_SECONDS)


def _user_payload(user):
    seller_profile = get_seller_profile(user)
    return {
        'id': str(user.id),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        # legacy compatibility
        'is_seller': user.is_seller,
        'is_verified_seller': user.is_verified_seller,
        'seller_commerce_mode': user.seller_commerce_mode,
        # canonical seller identity contract
        'isSellerActive': is_active_seller(user),
        'isSellerPending': is_pending_seller(user),
        'isVerifiedSeller': is_verified_seller(user),
        'sellerProfileStatus': getattr(seller_profile, 'status', None),
        'sellerApplicationStatus': get_seller_application_status(user),
        'sellerCommerceMode': get_seller_commerce_mode(user),
        'is_verified': user.is_verified,
        'is_managed_seller': user.is_managed_seller,
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
    }


@method_decorator(ratelimit(key='ip', rate='50/h', method='POST'), name='post')
class UserRegistrationView(generics.CreateAPIView):
    """
    Create an inactive account and send the verification code best-effort.
    The account only receives auth tokens after the code is verified.
    """

    queryset = PendingRegistration.objects.all()
    serializer_class = RegistrationInitiateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=data['email'],
                    password=data['password'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    phone=data.get('phone'),
                    role='buyer',
                    is_seller=False,
                    is_active=False,
                    is_verified=False,
                    is_verified_seller=False,
                    seller_commerce_mode='direct',
                )

                PendingRegistration.objects.filter(email=user.email).delete()
                code = _create_email_verification(user)
        except IntegrityError:
            return Response(
                {'error': 'Could not complete registration due to conflicting account data.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipient_name = user.get_full_name() or user.email
        email_sent = _queue_verification_email(
            recipient_email=user.email,
            recipient_name=recipient_name,
            code=code,
        )

        return _registration_pending_payload(
            user,
            email_sent=email_sent,
            status_code=status.HTTP_201_CREATED,
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

        pending = PendingRegistration.objects.filter(email=email).first()
        if not pending:
            user = User.objects.filter(email=email).first()
            if not user:
                return Response(
                    {'error': 'No account or pending registration found for this email.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                verification = VerificationCode.objects.get(
                    user=user,
                    code=code,
                    code_type='email',
                    is_used=False,
                )
            except VerificationCode.DoesNotExist:
                return Response(
                    {'error': 'Invalid verification code.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if verification.is_expired():
                return Response(
                    {'error': 'Verification code has expired. Request a new code.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.is_verified = True
            user.is_active = True
            user.save(update_fields=['is_verified', 'is_active'])
            verification.is_used = True
            verification.save(update_fields=['is_used'])

            try:
                send_welcome_email_task.delay(str(user.id))
            except Exception:
                try:
                    EmailService.send_welcome_email(user)
                except Exception:
                    pass

            return _issue_auth_payload(
                user,
                'Email verified successfully.',
                status_code=status.HTTP_200_OK,
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
                    role='buyer',
                    is_seller=False,
                    is_active=True,
                    is_verified_seller=False,
                    seller_commerce_mode='direct',
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
            try:
                EmailService.send_welcome_email(user)
            except Exception:
                pass

        return _issue_auth_payload(
            user,
            'Registration completed successfully.',
            status_code=status.HTTP_201_CREATED,
        )


@method_decorator(ratelimit(key='ip', rate='10/h', method='POST'), name='post')
class ResendRegistrationCodeView(APIView):
    """Resend code for an existing pending registration."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistrationResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        user = User.objects.filter(email=email).first()
        if user:
            if user.is_verified:
                return Response(
                    {'message': 'Email is already verified.'},
                    status=status.HTTP_200_OK,
                )

            scope = str(user.id)
            if not _resend_available(email, scope):
                return Response(
                    {
                        'error': (
                            f'Resend cooldown active. Please wait {RESEND_COOLDOWN_SECONDS} seconds before trying again.'
                        )
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            code = _create_email_verification(user)
            email_sent = _queue_verification_email(
                recipient_email=user.email,
                recipient_name=user.get_full_name() or user.email,
                code=code,
            )
            _set_resend_cooldown(email, scope)
            payload = {
                'message': 'Verification code queued.' if email_sent else 'Verification code created; email delivery will retry later.',
                'email_delivery_status': 'sent' if email_sent else 'deferred',
            }
            return Response(
                _attach_debug_code(payload, email, code),
                status=status.HTTP_200_OK,
            )

        try:
            pending = PendingRegistration.objects.get(email=email)
        except PendingRegistration.DoesNotExist:
            return Response(
                {'error': 'No pending registration found for this email.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scope = str(pending.id)
        if not _resend_available(email, scope):
            return Response(
                {
                    'error': (
                        f'Resend cooldown active. Please wait {RESEND_COOLDOWN_SECONDS} seconds before trying again.'
                    )
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        pending.verification_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        pending.code_expires_at = timezone.now() + timedelta(minutes=15)
        pending.save()

        recipient_name = f"{pending.first_name} {pending.last_name}".strip()
        email_sent = _queue_verification_email(
            recipient_email=pending.email,
            recipient_name=recipient_name,
            code=pending.verification_code,
        )

        _set_resend_cooldown(email, scope)
        payload = {
            'message': 'Verification code resent successfully.' if email_sent else 'Verification code refreshed; email delivery will retry later.',
            'email_delivery_status': 'sent' if email_sent else 'deferred',
        }
        return Response(
            _attach_debug_code(payload, email, pending.verification_code),
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
                    'is_seller': False,
                    'is_verified_seller': False,
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
                    'user': _user_payload(user),
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


class SellerApplicationView(APIView):
    """Create or update a seller application. Requires admin approval to become active."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        if is_active_seller(user):
            return Response(
                {'error': 'You are already an approved seller.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_fields = ['business_name', 'business_type', 'category', 'location', 'description', 'phone']
        missing_fields = [field for field in required_fields if not str(request.data.get(field, '')).strip()]
        if missing_fields:
            return Response(
                {'error': f"Missing required fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        business_type = request.data.get('business_type')
        valid_business_types = dict(SellerApplication.BUSINESS_TYPE_CHOICES)
        if business_type not in valid_business_types:
            return Response(
                {'error': 'Invalid business type.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category_id = request.data.get('category')
        try:
            from market.models import Category
            category_exists = Category.objects.filter(pk=category_id).exists()
        except Exception:
            category_exists = False

        if not category_exists:
            return Response(
                {'error': 'Invalid product category.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application, created = SellerApplication.objects.update_or_create(
            user=user,
            defaults={
                'business_name': request.data.get('business_name', '').strip(),
                'business_type': business_type,
                'category_id': category_id,
                'location': request.data.get('location', '').strip(),
                'description': request.data.get('description', '').strip(),
                'phone': request.data.get('phone', '').strip(),
                'status': SellerApplication.STATUS_PENDING,
            },
        )

        return Response({
            'message': 'Your application has been submitted and is under review. You will be notified by email once approved.',
            'user': _user_payload(user),
            'seller_application_status': application.status,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)



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

        email_sent = _queue_verification_email(
            recipient_email=user.email,
            recipient_name=user.get_full_name() or user.email,
            code=code,
        )

        payload = {
            'message': 'Verification code queued.' if email_sent else 'Verification code created; email delivery will retry later.',
            'email_delivery_status': 'sent' if email_sent else 'deferred',
        }

        return Response(
            _attach_debug_code(payload, user.email, code),
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
