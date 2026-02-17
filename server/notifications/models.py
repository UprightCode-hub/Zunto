#server/notifications/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class EmailTemplate(models.Model):
    """Email templates for different notification types"""
    
    TEMPLATE_TYPES = [
        ('welcome', 'Welcome Email'),
        ('email_verification', 'Email Verification'),
        ('password_reset', 'Password Reset'),
        ('order_confirmation', 'Order Confirmation'),
        ('payment_success', 'Payment Success'),
        ('order_shipped', 'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('refund_processed', 'Refund Processed'),
        ('cart_abandonment', 'Cart Abandonment'),
        ('review_reminder', 'Review Reminder'),
        ('seller_new_order', 'New Order (Seller)'),
        ('seller_review', 'New Review (Seller)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES, unique=True)
    subject = models.CharField(max_length=255)
    html_content = models.TextField(help_text="HTML email content with {{variables}}")
    text_content = models.TextField(blank=True, help_text="Plain text fallback")
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_templates'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class EmailLog(models.Model):
    """Log of all emails sent"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    
    recipient_email = models.EmailField()
    recipient_name = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
                  
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_email', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Email to {self.recipient_email} - {self.status}"


class NotificationPreference(models.Model):
    """User notification preferences"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
                         
    email_order_updates = models.BooleanField(default=True)
    email_payment_updates = models.BooleanField(default=True)
    email_shipping_updates = models.BooleanField(default=True)
    email_promotional = models.BooleanField(default=True)
    email_review_reminders = models.BooleanField(default=True)
    email_cart_abandonment = models.BooleanField(default=True)
    
                          
    email_seller_new_orders = models.BooleanField(default=True)
    email_seller_reviews = models.BooleanField(default=True)
    email_seller_messages = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.email}"


class Notification(models.Model):
    """In-app notifications for users"""
    
    NOTIFICATION_TYPES = [
        ('order', 'Order'),
        ('message', 'Message'),
        ('review', 'Review'),
        ('product', 'Product'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    
    is_read = models.BooleanField(default=False)
    
                    
    related_url = models.CharField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
