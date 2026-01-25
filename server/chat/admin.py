# chat/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Conversation, Message, MessageRead, TypingIndicator


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'product_link',
        'buyer_link',
        'seller_link',
        'message_count',
        'unread_badge',
        'status_indicator',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'created_at',
        'updated_at',
        ('product__status' ),
        # ('product__status', admin.FieldListFilter),
    ]
    search_fields = [
        'id',
        'buyer__email',
        'buyer__first_name',
        'buyer__last_name',
        'seller__email',
        'seller__first_name',
        'seller__last_name',
        'product__title',
    ]
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'conversation_details',
        'recent_messages_preview'
    ]
    fieldsets = (
        ('Conversation Info', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
        ('Participants', {
            'fields': ('buyer', 'seller')
        }),
        ('Product', {
            'fields': ('product',)
        }),
        ('Activity', {
            'fields': ('conversation_details', 'recent_messages_preview'),
            'classes': ('collapse',)
        }),
    )
    
    def product_link(self, obj):
        if obj.product:
            url = reverse('admin:market_product_change', args=[obj.product.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.product.title[:50]
            )
        return '-'
    product_link.short_description = 'Product'
    
    def buyer_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.buyer.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.buyer.get_full_name() or obj.buyer.email
        )
    buyer_link.short_description = 'Buyer'
    
    def seller_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.seller.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.seller.get_full_name() or obj.seller.email
        )
    seller_link.short_description = 'Seller'
    
    def message_count(self, obj):
        count = obj.messages.count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    message_count.short_description = 'Messages'
    
    def unread_badge(self, obj):
        buyer_unread = obj.messages.filter(is_read=False).exclude(sender=obj.buyer).count()
        seller_unread = obj.messages.filter(is_read=False).exclude(sender=obj.seller).count()
        
        if buyer_unread > 0 or seller_unread > 0:
            return format_html(
                '<span style="background: #f44336; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">B:{} | S:{}</span>',
                buyer_unread,
                seller_unread
            )
        return format_html(
            '<span style="color: #4caf50;">✓ All read</span>'
        )
    unread_badge.short_description = 'Unread'
    
    def status_indicator(self, obj):
        if obj.product and obj.product.deleted_at:
            return format_html(
                '<span style="color: #f44336;">🗑️ Deleted</span>'
            )
        if obj.product and obj.product.status != 'active':
            return format_html(
                '<span style="color: #ff9800;">⚠️ {}</span>',
                obj.product.status.title()
            )
        return format_html(
            '<span style="color: #4caf50;">✓ Active</span>'
        )
    status_indicator.short_description = 'Status'
    
    def conversation_details(self, obj):
        total_messages = obj.messages.count()
        buyer_messages = obj.messages.filter(sender=obj.buyer).count()
        seller_messages = obj.messages.filter(sender=obj.seller).count()
        last_message = obj.get_last_message()
        
        html = f'''
        <div style="font-family: monospace; background: #f5f5f5; padding: 15px; border-radius: 5px;">
            <strong>Total Messages:</strong> {total_messages}<br>
            <strong>Buyer Messages:</strong> {buyer_messages}<br>
            <strong>Seller Messages:</strong> {seller_messages}<br>
            <strong>Last Activity:</strong> {obj.updated_at.strftime("%Y-%m-%d %H:%M:%S")}<br>
        '''
        
        if last_message:
            html += f'<strong>Last Message:</strong> {last_message.content[:100]}...<br>'
        
        html += '</div>'
        return mark_safe(html)
    conversation_details.short_description = 'Details'
    
    def recent_messages_preview(self, obj):
        recent_messages = obj.messages.select_related('sender').order_by('-created_at')[:5]
        
        if not recent_messages:
            return mark_safe('<p style="color: #999;">No messages yet</p>')
        
        html = '<div style="background: #f9f9f9; padding: 10px; border-radius: 5px;">'
        
        for msg in reversed(list(recent_messages)):
            sender_name = msg.sender.get_full_name() or msg.sender.email
            bg_color = '#e3f2fd' if msg.sender == obj.buyer else '#fff3e0'
            
            html += f'''
            <div style="background: {bg_color}; padding: 8px; margin: 5px 0; border-radius: 3px; border-left: 3px solid #2196f3;">
                <strong>{sender_name}</strong> <span style="color: #666; font-size: 11px;">({msg.created_at.strftime("%H:%M")})</span><br>
                <span style="color: #333;">{msg.content[:150]}</span>
                {' <span style="color: #4caf50;">✓ Read</span>' if msg.is_read else ' <span style="color: #f44336;">• Unread</span>'}
            </div>
            '''
        
        html += '</div>'
        return mark_safe(html)
    recent_messages_preview.short_description = 'Recent Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'conversation_link',
        'sender_link',
        'message_preview',
        'message_type',
        'read_status',
        'created_at'
    ]
    list_filter = [
        'message_type',
        'is_read',
        'created_at',
    ]
    search_fields = [
        'id',
        'content',
        'sender__email',
        'sender__first_name',
        'sender__last_name',
        'conversation__id',
    ]
    readonly_fields = [
        'id',
        'created_at',
        'read_at',
        'message_details'
    ]
    fieldsets = (
        ('Message Info', {
            'fields': ('id', 'conversation', 'sender', 'created_at')
        }),
        ('Content', {
            'fields': ('message_type', 'content', 'message_details')
        }),
        ('Attachment', {
            'fields': (
                'attachment_url',
                'attachment_size',
                'attachment_mime',
                'attachment_duration',
                'waveform_data'
            ),
            'classes': ('collapse',)
        }),
        ('Read Status', {
            'fields': ('is_read', 'read_at')
        }),
    )
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            str(obj.conversation.id)[:8]
        )
    conversation_link.short_description = 'Conversation'
    
    def sender_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.sender.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.sender.get_full_name() or obj.sender.email
        )
    sender_link.short_description = 'Sender'
    
    def message_preview(self, obj):
        if obj.message_type == 'text':
            preview = obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
            return format_html('<span>{}</span>', preview)
        else:
            return format_html(
                '<span style="color: #2196f3;">📎 {}</span>',
                obj.message_type.upper()
            )
    message_preview.short_description = 'Message'
    
    def read_status(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="color: #4caf50;">✓ Read</span> <small style="color: #999;">({})</small>',
                obj.read_at.strftime("%H:%M") if obj.read_at else 'N/A'
            )
        return format_html(
            '<span style="color: #f44336;">• Unread</span>'
        )
    read_status.short_description = 'Status'
    
    def message_details(self, obj):
        html = f'''
        <div style="font-family: monospace; background: #f5f5f5; padding: 15px; border-radius: 5px;">
            <strong>Message ID:</strong> {obj.id}<br>
            <strong>Type:</strong> {obj.message_type}<br>
            <strong>Content Length:</strong> {len(obj.content)} chars<br>
            <strong>Created:</strong> {obj.created_at.strftime("%Y-%m-%d %H:%M:%S")}<br>
        '''
        
        if obj.attachment_url:
            html += f'<strong>Attachment:</strong> <a href="{obj.attachment_url}" target="_blank">View</a><br>'
            html += f'<strong>Size:</strong> {obj.attachment_size} bytes<br>' if obj.attachment_size else ''
        
        html += f'<strong>Read:</strong> {"Yes" if obj.is_read else "No"}<br>'
        if obj.read_at:
            html += f'<strong>Read At:</strong> {obj.read_at.strftime("%Y-%m-%d %H:%M:%S")}<br>'
        
        html += '</div>'
        return mark_safe(html)
    message_details.short_description = 'Details'


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ['id', 'message_link', 'user_link', 'read_at']
    list_filter = ['read_at']
    search_fields = ['message__id', 'user__email']
    readonly_fields = ['id', 'read_at']
    
    def message_link(self, obj):
        url = reverse('admin:chat_message_change', args=[obj.message.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.message.id)[:8])
    message_link.short_description = 'Message'
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.email
        )
    user_link.short_description = 'User'


@admin.register(TypingIndicator)
class TypingIndicatorAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_link', 'user_link', 'last_typed_at', 'active_status']
    list_filter = ['last_typed_at']
    search_fields = ['conversation__id', 'user__email']
    readonly_fields = ['id', 'last_typed_at']
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.conversation.id)[:8])
    conversation_link.short_description = 'Conversation'
    
    def user_link(self, obj):
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.user.get_full_name() or obj.user.email
        )
    user_link.short_description = 'User'
    
    def active_status(self, obj):
        if obj.is_active():
            return format_html('<span style="color: #4caf50;">🟢 Active</span>')
        return format_html('<span style="color: #999;">⚪ Inactive</span>')
    active_status.short_description = 'Status'