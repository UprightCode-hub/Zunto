#server/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.exceptions import AuthenticationFailed

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone', 'role']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_phone(self, value):
        if not value:
            return None
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone=validated_data.get('phone'),
            role=validated_data.get('role', 'buyer')
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user data"""
    
    def validate(self, attrs):
        data = super().validate(attrs)

        if not self.user.is_verified:
            raise AuthenticationFailed(
                "Email is not verified. Complete email verification before logging in."
            )
        
                                                
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_verified': self.user.is_verified,
            'seller_commerce_mode': self.user.seller_commerce_mode,
            'is_managed_seller': self.user.is_managed_seller,
            'profile_picture': self.user.profile_picture.url if self.user.profile_picture else None,
        }
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone',
            'profile_picture', 'bio', 'role', 'is_verified', 'is_phone_verified',
            'address', 'city', 'state', 'country', 'seller_commerce_mode',
            'is_managed_seller', 'created_at'
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'is_phone_verified', 'created_at', 'is_managed_seller']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, max_length=6)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""
    
    code = serializers.CharField(required=True, max_length=6)


class RegistrationInitiateSerializer(serializers.Serializer):
    """Serializer for registration initiation (code send only)."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=17)
    role = serializers.ChoiceField(required=False, choices=User.ROLE_CHOICES, default='buyer')
    seller_commerce_mode = serializers.ChoiceField(
        required=False,
        choices=User.SELLER_COMMERCE_MODE_CHOICES,
        default='direct',
    )

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        role = attrs.get('role', 'buyer')
        mode = attrs.get('seller_commerce_mode', 'direct')
        if role != 'seller' and mode != 'direct':
            raise serializers.ValidationError({
                'seller_commerce_mode': 'Only seller accounts can choose a commerce mode.'
            })
        return attrs

    def validate_email(self, value):
        normalized = value.lower()
        if User.objects.filter(email=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_phone(self, value):
        if not value:
            return None
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value


class RegistrationVerifySerializer(serializers.Serializer):
    """Serializer for registration code verification."""

    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower()


class RegistrationResendSerializer(serializers.Serializer):
    """Serializer for registration code resend."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower()


class GoogleAuthSerializer(serializers.Serializer):
    """Serializer for Google OAuth authentication"""
    token = serializers.CharField(required=True)
    
    def validate_token(self, value):
        if not value:
            raise serializers.ValidationError("Google token is required")
        return value
