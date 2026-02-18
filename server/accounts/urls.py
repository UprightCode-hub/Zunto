#server/accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView,
    VerifyRegistrationView,
    ResendRegistrationCodeView,
    CustomTokenObtainPairView,
    UserProfileView,
    ChangePasswordView,
    LogoutView,
    VerifyEmailView,
    ResendVerificationCodeView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    LoginPageView,
    RegisterPageView,
    GoogleAuthView,
)

app_name = 'accounts'

urlpatterns = [
                                  
    
                                         
    path('login_page/', LoginPageView.as_view(), name='login_page'),
    path('register-page/', RegisterPageView.as_view(), name='register_page'),
    
                                                       
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('register/verify/', VerifyRegistrationView.as_view(), name='register_verify'),
    path('register/resend/', ResendRegistrationCodeView.as_view(), name='register_resend'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('auth/google/', GoogleAuthView.as_view(), name='google_auth'),  
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
             
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
                        
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('resend-verification/', ResendVerificationCodeView.as_view(), name='resend_verification'),
    
                    
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
