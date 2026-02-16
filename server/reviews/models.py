#server/reviews/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg
import uuid

User = get_user_model()


class ProductReview(models.Model):
    """Reviews for products"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        'market.Product', 
        on_delete=models.CASCADE, 
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='product_reviews_given'
    )
    
                        
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    
                    
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    
                                                        
    quality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Product quality rating"
    )
    value_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Value for money rating"
    )
    accuracy_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Description accuracy rating"
    )
    
                  
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="Did reviewer actually purchase this product?"
    )
    
            
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    flagged_reason = models.TextField(blank=True)
    
                
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
                
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_reviews'
        ordering = ['-created_at']
        unique_together = ['product', 'reviewer']                                   
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['reviewer', '-created_at']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.reviewer.get_full_name()} - {self.product.title} ({self.rating}★)"
    
    @property
    def average_detailed_rating(self):
        """Calculate average of detailed ratings"""
        ratings = [
            r for r in [self.quality_rating, self.value_rating, self.accuracy_rating] 
            if r is not None
        ]
        return sum(ratings) / len(ratings) if ratings else self.rating


class SellerReview(models.Model):
    """Reviews for sellers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='seller_reviews_received',
        limit_choices_to={'role__in': ['seller', 'service_provider']}
    )
    reviewer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='seller_reviews_given'
    )
    
                                             
    product = models.ForeignKey(
        'market.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seller_reviews'
    )
    
                        
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    
                    
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    
                                  
    communication_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Communication rating"
    )
    reliability_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Reliability rating"
    )
    professionalism_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="Professionalism rating"
    )
    
                  
    is_verified_transaction = models.BooleanField(
        default=False,
        help_text="Did reviewer actually transact with this seller?"
    )
    
            
    is_approved = models.BooleanField(default=True)
    is_flagged = models.BooleanField(default=False)
    flagged_reason = models.TextField(blank=True)
    
                
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
                
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'seller_reviews'
        ordering = ['-created_at']
        unique_together = ['seller', 'reviewer', 'product']                                              
        indexes = [
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['reviewer', '-created_at']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.reviewer.get_full_name()} → {self.seller.get_full_name()} ({self.rating}★)"
    
    @property
    def average_detailed_rating(self):
        """Calculate average of detailed ratings"""
        ratings = [
            r for r in [self.communication_rating, self.reliability_rating, self.professionalism_rating] 
            if r is not None
        ]
        return sum(ratings) / len(ratings) if ratings else self.rating


class ReviewResponse(models.Model):
    """Seller responses to reviews"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
                                                        
    product_review = models.OneToOneField(
        ProductReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='response'
    )
    seller_review = models.OneToOneField(
        SellerReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='response'
    )
    
    responder = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_responses'
    )
    response = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'review_responses'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.product_review:
            return f"Response to product review by {self.responder.get_full_name()}"
        return f"Response to seller review by {self.responder.get_full_name()}"


class ReviewHelpful(models.Model):
    """Track helpful votes on reviews"""
    
    VOTE_CHOICES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
                                                 
    product_review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='helpful_votes'
    )
    seller_review = models.ForeignKey(
        SellerReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='helpful_votes'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_votes'
    )
    vote = models.CharField(max_length=20, choices=VOTE_CHOICES)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'review_helpful_votes'
        indexes = [
            models.Index(fields=['product_review', 'user']),
            models.Index(fields=['seller_review', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} voted {self.vote}"


class ReviewImage(models.Model):
    """Images attached to reviews"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
                                                   
    product_review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='images'
    )
    seller_review = models.ForeignKey(
        SellerReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='images'
    )
    
    image = models.ImageField(upload_to='reviews/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'review_images'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        if self.product_review:
            return f"Image for product review {self.product_review.id}"
        return f"Image for seller review {self.seller_review.id}"


class ReviewFlag(models.Model):
    """Flag inappropriate reviews"""
    
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('offensive', 'Offensive Language'),
        ('fake', 'Fake Review'),
        ('irrelevant', 'Irrelevant Content'),
        ('personal_info', 'Contains Personal Information'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
                                              
    product_review = models.ForeignKey(
        ProductReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='flags'
    )
    seller_review = models.ForeignKey(
        SellerReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='flags'
    )
    
    flagger = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_flags'
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
        db_table = 'review_flags'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Flag: {self.reason} - {self.status}"
