# notifications/admin.py
from django.contrib import admin
from .models import EmailTemplate, EmailLog, NotificationPreference


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'subject', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'template_type', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject', 'html_content', 'text_content')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = [
        'recipient_email', 'recipient_name', 'subject',
        'status', 'sent_at', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'sent_at']
    search_fields = ['recipient_email', 'recipient_name', 'subject']
    readonly_fields = [
        'template', 'recipient_email', 'recipient_name', 'subject',
        'status', 'error_message', 'opened_at', 'clicked_at',
        'sent_at', 'created_at'
    ]
    
    fieldsets = (
        ('Recipient Information', {
            'fields': ('recipient_email', 'recipient_name')
        }),
        ('Email Details', {
            'fields': ('template', 'subject', 'status', 'error_message')
        }),
        ('Tracking', {
            'fields': ('opened_at', 'clicked_at')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'created_at')
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'email_order_updates', 'email_payment_updates',
        'email_shipping_updates', 'email_promotional'
    ]
    list_filter = [
        'email_order_updates', 'email_payment_updates',
        'email_shipping_updates', 'email_promotional'
    ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Order Notifications', {
            'fields': (
                'email_order_updates', 'email_payment_updates',
                'email_shipping_updates'
            )
        }),
        ('Marketing Notifications', {
            'fields': ('email_promotional', 'email_review_reminders', 'email_cart_abandonment')
        }),
        ('Seller Notifications', {
            'fields': (
                'email_seller_new_orders', 'email_seller_reviews',
                'email_seller_messages'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )