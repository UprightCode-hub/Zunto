from django.contrib import admin
from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'seller', 'product_id', 'created_at', 'updated_at', 'message_count']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['buyer__username', 'seller__username', 'product_id', 'id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('buyer', 'seller')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'conversation_preview', 'content_preview', 
                    'message_type', 'is_read', 'created_at']
    list_filter = ['is_read', 'message_type', 'created_at']
    search_fields = ['sender__username', 'content', 'id']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        if obj.content:
            return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        return '[No content]'
    content_preview.short_description = 'Content'
    
    def conversation_preview(self, obj):
        return f"{obj.conversation.buyer.username} ↔ {obj.conversation.seller.username}"
    conversation_preview.short_description = 'Conversation'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'sender', 'conversation__buyer', 'conversation__seller'
        )