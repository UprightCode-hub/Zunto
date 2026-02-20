#server/market/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
import uuid
from core.models import SoftDeleteModel

User = get_user_model()


class Category(models.Model):
    """Product/Service Categories"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class or emoji")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories'
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_full_path(self):
        """Get full category path (e.g., Electronics > Phones > Android)"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class Location(models.Model):
    """Location for products/services"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'locations'
        ordering = ['state', 'city']
        unique_together = ['state', 'city', 'area']
        indexes = [
            models.Index(fields=['state', 'city']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        if self.area:
            return f"{self.area}, {self.city}, {self.state}"
        return f"{self.city}, {self.state}"


class Product(SoftDeleteModel):
    """Products and Services Listing"""
    
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('sold', 'Sold'),
        ('reserved', 'Reserved'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    ]
    
    LISTING_TYPE_CHOICES = [
        ('product', 'Product'),
        ('service', 'Service'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
                        
    seller = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='products'
    )
    
                       
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField()
    listing_type = models.CharField(
        max_length=20, 
        choices=LISTING_TYPE_CHOICES, 
        default='product'
    )
    
                    
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products'
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='products'
    )
    
             
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    negotiable = models.BooleanField(default=False)
    
                     
    condition = models.CharField(
        max_length=20, 
        choices=CONDITION_CHOICES, 
        blank=True
    )
    brand = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    
            
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='active',
        db_index=True
    )
    
               
    is_featured = models.BooleanField(default=False)
    is_boosted = models.BooleanField(default=False)
    boost_expires_at = models.DateTimeField(null=True, blank=True)
    
                  
    is_verified = models.BooleanField(
        default=False, 
        help_text="Admin verified listing"
    )
    
                        
    views_count = models.PositiveIntegerField(default=0)
    favorites_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    
                
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
            models.Index(fields=['is_boosted', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    @property
    def is_available(self):
        """Check if product is available for purchase"""
        return self.status == 'active' and self.quantity > 0
    
    @property
    def is_expired(self):
        """Check if listing has expired"""
        from django.utils import timezone
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        from django.db.models import Avg
        avg = self.reviews.filter(is_approved=True).aggregate(Avg('rating'))['rating__avg']
        return round(avg, 2) if avg else 0

    @property
    def review_count(self):
        """Get total number of approved reviews"""
        return self.reviews.filter(is_approved=True).count()


class ProductImage(models.Model):
    """Product Images"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(upload_to='products/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_images'
        ordering = ['order', '-is_primary']
        indexes = [
            models.Index(fields=['product', 'is_primary']),
        ]
    
    def __str__(self):
        return f"Image for {self.product.title}"
    
    def save(self, *args, **kwargs):
                                                               
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, 
                is_primary=True
            ).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductVideo(models.Model):
    """Product Videos"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='videos'
    )
    video = models.FileField(upload_to='products/videos/%Y/%m/')
    thumbnail = models.ImageField(upload_to='products/video_thumbnails/%Y/%m/', blank=True)
    caption = models.CharField(max_length=255, blank=True)
    duration = models.PositiveIntegerField(help_text="Duration in seconds", null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_videos'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Video for {self.product.title}"


class Favorite(models.Model):
    """User's favorite products"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='favorites'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'favorites'
        unique_together = ['user', 'product']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} favorited {self.product.title}"


class ProductView(models.Model):
    """Track product views"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='product_views'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='viewed_products'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_views'
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['product', '-viewed_at']),
            models.Index(fields=['product', 'user']),
            models.Index(fields=['user', '-viewed_at']),
        ]
    
    def __str__(self):
        return f"View of {self.product.title}"


class ProductShareEvent(models.Model):
    """Track authorized product shares."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='share_events'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_products'
    )
    shared_via = models.CharField(max_length=30, default='link')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_share_events'
        ordering = ['-created_at']
        unique_together = ['product', 'user']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} shared {self.product.title}"


class ProductReport(models.Model):
    """Report inappropriate products"""
    
    REASON_CHOICES = [
        ('fake', 'Fake/Counterfeit'),
        ('inappropriate', 'Inappropriate Content'),
        ('spam', 'Spam'),
        ('fraud', 'Fraudulent'),
        ('duplicate', 'Duplicate Listing'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='reports'
    )
    reporter = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='product_reports'
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField()
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'product_reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['product', 'status']),
        ]
    
    def __str__(self):
        return f"Report: {self.product.title} - {self.reason}"
