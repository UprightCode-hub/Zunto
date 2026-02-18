#server/cart/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
import uuid

User = get_user_model()


class Cart(models.Model):
    """Shopping cart for users"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='cart',
        null=True,
        blank=True,
        help_text="User who owns this cart (null for guest carts)"
    )
    session_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        db_index=True,
        help_text="Session ID for guest users"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Guest Cart ({self.session_id[:8]})"

    @property
    def total_items(self):
        """Total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        """Calculate cart subtotal"""
        return sum(item.total_price for item in self.items.all())

    @property
    def is_empty(self):
        """Check if cart is empty"""
        return self.items.count() == 0

    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()


class CartItem(models.Model):
    """Individual items in a cart"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    product = models.ForeignKey(
        'market.Product', 
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    price_at_addition = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Product price when added to cart"
    )

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        ordering = ['-added_at']
        unique_together = ['cart', 'product']
        indexes = [
            models.Index(fields=['cart', 'product']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.title}"

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return (self.price_at_addition or 0) * (self.quantity or 0)

    @property
    def is_available(self):
        """Check if product is still available"""
        return (
            self.product.status == 'active' and 
            self.product.quantity >= self.quantity
        )

    @property
    def has_sufficient_stock(self):
        """Check if there's enough stock for requested quantity"""
        return self.product.quantity >= self.quantity

    def save(self, *args, **kwargs):
        if not self.price_at_addition:
            self.price_at_addition = self.product.price
        super().save(*args, **kwargs)
        self.cart.save(update_fields=['updated_at'])

    def delete(self, *args, **kwargs):
        cart = self.cart
        super().delete(*args, **kwargs)
        cart.save(update_fields=['updated_at'])


class SavedForLater(models.Model):
    """Items saved for later (not in active cart)"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='saved_items'
    )
    product = models.ForeignKey(
        'market.Product', 
        on_delete=models.CASCADE,
        related_name='saved_by_users'
    )

    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saved_for_later'
        ordering = ['-saved_at']
        unique_together = ['user', 'product']
        indexes = [
            models.Index(fields=['user', '-saved_at']),
        ]

    def __str__(self):
        return f"{self.user.email} saved {self.product.title}"


class CartAbandonment(models.Model):
    """Track abandoned carts for marketing/analytics"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='abandonment_records'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='abandoned_carts'
    )

    total_items = models.PositiveIntegerField()
    total_value = models.DecimalField(max_digits=12, decimal_places=2)

    recovered = models.BooleanField(default=False)
    recovered_at = models.DateTimeField(null=True, blank=True)

    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    abandoned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cart_abandonments'
        ordering = ['-abandoned_at']
        indexes = [
            models.Index(fields=['user', '-abandoned_at']),
            models.Index(fields=['recovered']),
        ]

    def __str__(self):
        return f"Abandoned cart - {self.total_items} items (₦{self.total_value})"


class CartEvent(models.Model):
    """Log cart-related user events"""

    EVENT_TYPES = [
        ('cart_item_added', 'Item Added'),
        ('cart_item_updated', 'Item Updated'),
        ('cart_item_removed', 'Item Removed'),
        ('cart_item_saved', 'Item Saved for Later'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cart_events'
    )
    cart_id = models.UUIDField(db_index=True)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'cart_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.created_at}"


class UserScore(models.Model):
    """Track user cart behavior scores for targeting and analytics"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart_score',
        primary_key=True
    )
    
    abandonment_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Score based on abandonment frequency"
    )
    value_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Score based on average cart value"
    )
    conversion_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Score based on recovery/conversion rate"
    )
    hesitation_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Score based on time-to-abandon and save-for-later behavior"
    )
    
    composite_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Weighted composite score (0-100)"
    )
    
    discount_eligibility = models.BooleanField(
        default=False,
        help_text="Whether user qualifies for targeted discounts"
    )
    recommended_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        null=True,
        blank=True,
        help_text="Recommended discount percentage"
    )
    promo_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Assigned promo code for this user"
    )
    
    last_calculated = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        db_table = 'user_scores'
        ordering = ['-composite_score']
        indexes = [
            models.Index(fields=['-composite_score']),
            models.Index(fields=['-value_score']),
            models.Index(fields=['last_calculated']),
            models.Index(fields=['discount_eligibility']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - Score: {self.composite_score}"
    
    @property
    def score_tier(self):
        """Categorize users by composite score"""
        if self.composite_score >= 75:
            return 'high_value'
        elif self.composite_score >= 50:
            return 'medium_value'
        elif self.composite_score >= 25:
            return 'low_value'
        return 'at_risk'
