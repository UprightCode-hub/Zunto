from django.shortcuts import render
from notifications.email_service import EmailService
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
from notifications.tasks import send_welcome_email_task, send_verification_email_task
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .serializers import (
    UserRegistrationSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer
)
from .models import VerificationCode

User = get_user_model()

@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='post')
class UserRegistrationView(generics.CreateAPIView):
    """
    User registration endpoint
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate verification code
        code = self.generate_verification_code(user, 'email')

        # ❌ Remove synchronous email sending
        # EmailService.send_verification_email(user, code)
        # EmailService.send_welcome_email(user)

        # ✅ Send emails only through Celery async tasks
        send_verification_email_task.delay(str(user.id), code)
        send_welcome_email_task.delay(str(user.id))

        return Response({
            'message': 'Registration successful. Please check your email for verification code.',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }, status=status.HTTP_201_CREATED)

    def generate_verification_code(self, user, code_type):
        """Generate and store a 6-digit verification code."""
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=15)

        VerificationCode.objects.create(
            user=user,
            code=code,
            code_type=code_type,
            expires_at=expires_at
        )
        return code


@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='post')
class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login endpoint with user data"""
    
    serializer_class = CustomTokenObtainPairSerializer


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
            
            # Check old password
            if not user.check_password(serializer.data.get('old_password')):
                return Response(
                    {'old_password': ['Wrong password.']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(serializer.data.get('new_password'))
            user.save()
            
            return Response({
                'message': 'Password changed successfully.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """Logout endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'message': 'Logout successful.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Invalid token.'
            }, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    """Verify user email"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        
        if serializer.is_valid():
            code = serializer.data.get('code')
            user = request.user
            
            try:
                verification = VerificationCode.objects.get(
                    user=user,
                    code=code,
                    code_type='email',
                    is_used=False
                )
                
                if verification.is_expired():
                    return Response({
                        'error': 'Verification code has expired.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Mark as verified
                user.is_verified = True
                user.save()
                
                verification.is_used = True
                verification.save()
                
                return Response({
                    'message': 'Email verified successfully.'
                }, status=status.HTTP_200_OK)
                
            except VerificationCode.DoesNotExist:
                return Response({
                    'error': 'Invalid verification code.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationCodeView(APIView):
    """Resend email verification code"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.is_verified:
            return Response({
                'message': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate new code
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        expires_at = timezone.now() + timedelta(minutes=15)
        
        VerificationCode.objects.create(
            user=user,
            code=code,
            code_type='email',
            expires_at=expires_at
        )
        
        # TODO: Send email with verification code
        send_verification_email(user.email, code)
        
        return Response({
            'message': 'Verification code sent successfully.'
        }, status=status.HTTP_200_OK)


@method_decorator(ratelimit(key='ip', rate='5/h', method='POST'), name='post')
class PasswordResetRequestView(APIView):
    """Request password reset"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.data.get('email')
            
            try:
                user = User.objects.get(email=email)
                
                # Generate reset code
                code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                expires_at = timezone.now() + timedelta(minutes=15)
                
                VerificationCode.objects.create(
                    user=user,
                    code=code,
                    code_type='password_reset',
                    expires_at=expires_at
                )
                
                # TODO: Send email with reset code
                # send_password_reset_email(user.email, code)
                EmailService.send_password_reset_email(user, code)
                
                return Response({
                    'message': 'Password reset code sent to your email.'
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                # Don't reveal if email exists or not (security)
                return Response({
                    'message': 'If this email exists, a reset code has been sent.'
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    """Confirm password reset with code"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.data.get('email')
            code = serializer.data.get('code')
            new_password = serializer.data.get('new_password')
            
            try:
                user = User.objects.get(email=email)
                verification = VerificationCode.objects.get(
                    user=user,
                    code=code,
                    code_type='password_reset',
                    is_used=False
                )
                
                if verification.is_expired():
                    return Response({
                        'error': 'Reset code has expired.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Reset password
                user.set_password(new_password)
                user.save()
                
                verification.is_used = True
                verification.save()
                
                return Response({
                    'message': 'Password reset successfully.'
                }, status=status.HTTP_200_OK)
                
            except (User.DoesNotExist, VerificationCode.DoesNotExist):
                return Response({
                    'error': 'Invalid email or reset code.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
