# chat/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, MessageRead

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information in chat"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 
            'email', 
            'first_name', 
            'last_name', 
            'full_name',
            'profile_picture',
            'role'
        ]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    sender = UserSerializer(read_only=True)
    is_own_message = serializers.SerializerMethodField()
    attachment_filename = serializers.CharField(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender',
            'message_type',
            'content',
            'attachment_url',
            'attachment_size',
            'attachment_mime',
            'attachment_duration',
            'attachment_filename',
            'waveform_data',
            'is_read',
            'read_at',
            'created_at',
            'is_own_message'
        ]
        read_only_fields = [
            'id',
            'sender',
            'created_at',
            'read_at',
            'is_own_message',
            'attachment_filename'
        ]
    
    def get_is_own_message(self, obj):
        """Check if the current user is the sender"""
        request = self.context.get('request')
        if request and request.user:
            return obj.sender == request.user
        return False
    
    def validate(self, data):
        """Ensure either content or attachment_url is provided"""
        content = data.get('content', '').strip()
        attachment_url = data.get('attachment_url', '').strip()
        
        if not content and not attachment_url:
            raise serializers.ValidationError(
                "Either 'content' or 'attachment_url' must be provided"
            )
        
        # Validate message type
        message_type = data.get('message_type', 'text')
        if message_type != 'text' and not attachment_url:
            raise serializers.ValidationError(
                f"Message type '{message_type}' requires an attachment_url"
            )
        
        return data


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation list"""
    buyer = UserSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_image = serializers.SerializerMethodField()
    product_price = serializers.DecimalField(
        source='product.price',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'buyer',
            'seller',
            'other_user',
            'product',
            'product_title',
            'product_image',
            'product_price',
            'last_message',
            'unread_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_other_user(self, obj):
        """Get the other participant (not the current user)"""
        request = self.context.get('request')
        if request and request.user:
            other = obj.get_other_user(request.user)
            return UserSerializer(other).data
        return None
    
    def get_last_message(self, obj):
        """Get the most recent message preview"""
        last_msg = obj.get_last_message()
        if last_msg:
            return {
                'id': str(last_msg.id),
                'content': last_msg.content[:100] if last_msg.content else '[Attachment]',
                'message_type': last_msg.message_type,
                'sender_id': str(last_msg.sender.id),
                'is_read': last_msg.is_read,
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        """Get number of unread messages for current user"""
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_product_image(self, obj):
        """Get product's primary image URL"""
        if obj.product and obj.product.images.exists():
            primary_image = obj.product.images.filter(is_primary=True).first()
            if not primary_image:
                primary_image = obj.product.images.first()
            
            if primary_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(primary_image.image.url)
                return primary_image.image.url
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single conversation view"""
    buyer = UserSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    # Product details
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_price = serializers.DecimalField(
        source='product.price',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    product_status = serializers.CharField(source='product.status', read_only=True)
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'buyer',
            'seller',
            'other_user',
            'product',
            'product_title',
            'product_slug',
            'product_price',
            'product_status',
            'product_image',
            'messages',
            'unread_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_other_user(self, obj):
        """Get the other participant"""
        request = self.context.get('request')
        if request and request.user:
            other = obj.get_other_user(request.user)
            return UserSerializer(other).data
        return None
    
    def get_unread_count(self, obj):
        """Get unread count for current user"""
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_product_image(self, obj):
        """Get product's primary image"""
        if obj.product and obj.product.images.exists():
            primary_image = obj.product.images.filter(is_primary=True).first()
            if not primary_image:
                primary_image = obj.product.images.first()
            
            if primary_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(primary_image.image.url)
                return primary_image.image.url
        return None


class ConversationSerializer(serializers.ModelSerializer):
    """
    Default serializer - automatically chooses between list and detail
    based on context
    """
    buyer = UserSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'buyer',
            'seller',
            'product',
            'product_title',
            'product_image',
            'last_message',
            'unread_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = fields
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count(request.user)
        return 0
    
    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        if last_msg:
            return {
                'content': last_msg.content[:50] if last_msg.content else '[Attachment]',
                'created_at': last_msg.created_at
            }
        return None
    
    def get_product_image(self, obj):
        if obj.product and obj.product.images.exists():
            primary_image = obj.product.images.filter(is_primary=True).first()
            if not primary_image:
                primary_image = obj.product.images.first()
            
            if primary_image:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(primary_image.image.url)
                return primary_image.image.url
        return None


class MessageReadSerializer(serializers.ModelSerializer):
    """Serializer for read receipts"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageRead
        fields = ['id', 'message', 'user', 'read_at']
        read_only_fields = ['id', 'read_at']