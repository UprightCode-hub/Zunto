#server/accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
import uuid
from core.storage_backends import PublicMediaStorage

class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email=None, password=None, **extra_fields):
        username = extra_fields.pop('username', None)
        if not email and username:
            email = f'{username}@example.com'
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
    
                                              
    username = None
    
                    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)                     
    phone = models.CharField(validators=[phone_regex], max_length=17, unique=True, null=True, blank=True)
    
                    
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    profile_picture = models.ImageField(
        upload_to='public/marketplace/profile_pictures/',
        storage=PublicMediaStorage(),
        null=True,
        blank=True,
    )
    bio = models.TextField(max_length=500, blank=True)
    
                           
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='buyer')
    is_seller = models.BooleanField(default=False)
    is_verified_seller = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    
                           
    nin = models.CharField(max_length=11, unique=True, null=True, blank=True, help_text="National Identification Number")
    bvn = models.CharField(max_length=11, unique=True, null=True, blank=True, help_text="Bank Verification Number")
    seller_commerce_mode = models.CharField(
        max_length=20,
        choices=SELLER_COMMERCE_MODE_CHOICES,
        default='direct',
        help_text='Direct sellers handle payment off-platform. Managed sellers use Zunto payment, shipping, and refunds.',
    )
    
                         
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Nigeria')
    
                
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
                    
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
        try:
            seller_profile = self.seller_profile
        except SellerProfile.DoesNotExist:
            return False
        return (
            seller_profile.status == SellerProfile.STATUS_APPROVED
            and seller_profile.is_verified_seller
            and seller_profile.seller_commerce_mode == 'managed'
        )

    @property
    def is_seller_active(self):
        try:
            return self.seller_profile.status == SellerProfile.STATUS_APPROVED
        except SellerProfile.DoesNotExist:
            return False

    @property
    def is_seller_pending(self):
        try:
            return self.seller_profile.status == SellerProfile.STATUS_PENDING
        except SellerProfile.DoesNotExist:
            return False

    @property
    def is_verified_seller_effective(self):
        try:
            return bool(self.seller_profile.is_verified_seller)
        except SellerProfile.DoesNotExist:
            return False


class SellerProfile(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    SELLER_COMMERCE_MODE_CHOICES = User.SELLER_COMMERCE_MODE_CHOICES

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    is_verified_seller = models.BooleanField(default=False)

    verified = models.BooleanField(default=False)
    rating = models.FloatField(default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    
    seller_commerce_mode = models.CharField(
        max_length=20,
        choices=SELLER_COMMERCE_MODE_CHOICES,
        default='direct',
        help_text='Direct sellers handle payment off-platform. Managed sellers use Zunto payment, shipping, and refunds.',
    )
    active_location = models.ForeignKey(
        'market.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seller_profiles',
        help_text='Canonical active location for seller listings.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seller_profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_verified_seller']),
            
            # ADD THESE
            models.Index(fields=['verified']),
            models.Index(fields=['rating']),
        ]    

    def __str__(self):
        return f"SellerProfile<{self.user.email}> ({self.status})"

    def update_rating(self):
        from reviews.models import ProductReview
        from django.db.models import Avg

        reviews = ProductReview.objects.filter(product__seller=self.user)

        if reviews.exists():
            avg = reviews.aggregate(Avg("rating"))["rating__avg"]
            self.rating = round(avg, 2)
            self.total_reviews = reviews.count()
            self.save()    


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
