#server/notifications/serializers.py
from rest_framework import serializers
from .models import EmailTemplate, EmailLog, NotificationPreference, Notification


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for email templates"""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'template_type', 'subject',
            'html_content', 'text_content', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for email logs"""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = [
            'id', 'template', 'template_name', 'recipient_email',
            'recipient_name', 'subject', 'status', 'error_message',
            'opened_at', 'clicked_at', 'sent_at', 'created_at'
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'email_order_updates', 'email_payment_updates',
            'email_shipping_updates', 'email_promotional',
            'email_review_reminders', 'email_cart_abandonment',
            'email_seller_new_orders', 'email_seller_reviews',
            'email_seller_messages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for user notifications"""
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'type', 'type_display',
            'is_read', 'related_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
