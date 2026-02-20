#server/orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models import Sum, F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import uuid

User = get_user_model()


class Order(models.Model):
    """Customer orders"""

    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
        ('wallet', 'Wallet'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=30, unique=True, db_index=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='paystack')
    payment_reference = models.CharField(max_length=255, blank=True, db_index=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[('unpaid', 'Unpaid'), ('paid', 'Paid'), ('refunded', 'Refunded')],
        default='unpaid'
    )

                                                       
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Shipping tracking number for the order"
    )

    shipping_address_ref = models.ForeignKey(
        'orders.ShippingAddress',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders'
    )
    shipping_address = models.TextField(blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_country = models.CharField(max_length=100, default='Nigeria')
    shipping_phone = models.CharField(max_length=20, blank=True)
    shipping_email = models.EmailField(blank=True)
    shipping_full_name = models.CharField(max_length=255, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['payment_reference']),
            models.Index(fields=['payment_status']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.customer.email}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            date_str = timezone.now().strftime('%Y%m%d')
            random_part = str(uuid.uuid4())[:4].upper()
            self.order_number = f"ORD-{date_str}-{random_part}"
        super().save(*args, **kwargs)

    def update_totals(self):
        """Update subtotal and total_amount based on order items"""
        subtotal = self.items.aggregate(
            total=Sum(F('unit_price') * F('quantity'))
        )['total'] or 0
        self.subtotal = subtotal
        self.total_amount = subtotal + self.tax_amount + self.shipping_fee - self.discount_amount
        self.save(update_fields=['subtotal', 'total_amount'])

    @property
    def total_items(self):
        """Calculate total quantity of items in order"""
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def can_cancel(self):
        """
        Only allow cancel if order is pending or processing.
        """
        return self.status in ['pending', 'processing']

                                                                                      
                                                                          


class OrderItem(models.Model):
    """Items in an order (linked to Product & Seller)"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('market.Product', on_delete=models.SET_NULL, null=True, related_name='order_items')
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sold_items')

    product_name = models.CharField(max_length=255)
    product_image = models.URLField(blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_items'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    def save(self, *args, **kwargs):
        if not self.unit_price and self.product:
            self.unit_price = self.product.price
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Track order status changes"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_status_history'
        ordering = ['-created_at']
        verbose_name_plural = 'Order status histories'
    
    def __str__(self):
        return f"{self.order.order_number}: {self.old_status} → {self.new_status}"


class ShippingAddress(models.Model):
    """Saved shipping addresses for users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shipping_addresses'
    )
    
    label = models.CharField(
        max_length=50,
        help_text="e.g., Home, Office, etc."
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Nigeria')
    postal_code = models.CharField(max_length=20, blank=True)
    
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shipping_addresses'
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.label} - {self.full_name}"
    
    def save(self, *args, **kwargs):
                                                         
        if self.is_default:
            ShippingAddress.objects.filter(
                user=self.user,
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment records"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
                     
    payment_method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
                         
    gateway_reference = models.CharField(
        max_length=255,
        unique=True,
        help_text="Payment reference from gateway (e.g., Paystack)"
    )
    gateway_response = models.JSONField(
        blank=True,
        null=True,
        help_text="Full response from payment gateway"
    )
    
              
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
                
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', '-created_at']),
            models.Index(fields=['gateway_reference']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payment {self.gateway_reference} - ₦{self.amount}"


class Refund(models.Model):
    """Refund records"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    REASON_CHOICES = [
        ('customer_request', 'Customer Request'),
        ('defective_product', 'Defective Product'),
        ('wrong_product', 'Wrong Product Sent'),
        ('not_received', 'Product Not Received'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        related_name='refunds'
    )
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    description = models.TextField()
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
                         
    refund_reference = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)
    
                 
    admin_notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refunds'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'refunds'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Refund for {self.order.order_number} - ₦{self.amount}"


class OrderNote(models.Model):
    """Internal notes for orders"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_notes'
    )
    
    note = models.TextField()
    is_customer_visible = models.BooleanField(
        default=False,
        help_text="Should customer see this note?"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'order_notes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note for {self.order.order_number}"


                                                               

@receiver([post_save, post_delete], sender=OrderItem)
def update_order_totals(sender, instance, **kwargs):
    """
    Automatically recalculate order subtotal and total_amount 
    whenever an OrderItem is created, updated, or deleted.
    """
    if instance.order:
        instance.order.update_totals()
