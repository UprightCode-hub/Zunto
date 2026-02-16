# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
import uuid

class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User Model"""
    
    ROLE_CHOICES = [
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('service_provider', 'Service Provider'),
        ('delivery_rider', 'Delivery Rider'),
        ('admin', 'Admin'),
    ]

    SELLER_COMMERCE_MODE_CHOICES = [
        ('direct', 'Direct Seller (buyer pays seller directly)'),
        ('managed', 'Managed by Zunto (buyer pays Zunto)'),
    ]
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    
    # Remove username field, use email instead
    username = None
    
    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)  # ← ADDED THIS LINE
    phone = models.CharField(validators=[phone_regex], max_length=17, unique=True, null=True, blank=True)
    
    # Profile fields
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Role and verification
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='buyer')
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    
    # Identity verification
    nin = models.CharField(max_length=11, unique=True, null=True, blank=True, help_text="National Identification Number")
    bvn = models.CharField(max_length=11, unique=True, null=True, blank=True, help_text="Bank Verification Number")
    seller_commerce_mode = models.CharField(
        max_length=20,
        choices=SELLER_COMMERCE_MODE_CHOICES,
        default='direct',
        help_text='Direct sellers handle payment off-platform. Managed sellers use Zunto payment, shipping, and refunds.',
    )
    
    # Address information
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Nigeria')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    # Account status
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_identity_verified(self):
        """Check if user has verified their identity"""
        return bool(self.nin or self.bvn)

    @property
    def is_managed_seller(self):
        """Managed sellers are verified sellers that opted into Zunto-managed commerce."""
        return self.role == 'seller' and self.is_verified and self.seller_commerce_mode == 'managed'


class VerificationCode(models.Model):
    """Email and Phone verification codes"""
    
    CODE_TYPES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('password_reset', 'Password Reset'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_codes')
    code = models.CharField(max_length=6)
    code_type = models.CharField(max_length=20, choices=CODE_TYPES)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'verification_codes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.code_type} - {self.code}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class PendingRegistration(models.Model):
    """
    Stores registration data until email verification succeeds.
    A real User record is created only after code verification.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=17, null=True, blank=True)
    role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='buyer')
    seller_commerce_mode = models.CharField(
        max_length=20,
        choices=User.SELLER_COMMERCE_MODE_CHOICES,
        default='direct',
    )
    password_hash = models.CharField(max_length=128)
    verification_code = models.CharField(max_length=6)
    code_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pending_registrations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"PendingRegistration<{self.email}>"

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.code_expires_at
