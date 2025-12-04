from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Max
from django.utils import timezone
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer
)

User = get_user_model()


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations between buyers and sellers
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Only show conversations where user is buyer or seller"""
        user = self.request.user
        return Conversation.objects.filter(
            Q(buyer=user) | Q(seller=user)
        ).select_related(
            'buyer', 
            'seller', 
            'product'
        ).prefetch_related(
            'messages',
            'product__images'
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time')
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer
    
    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        """
        Get existing conversation or create new one
        POST data: {product_id: uuid, seller_id: uuid}
        
        Example:
        POST /api/chat/conversations/get_or_create/
        {
            "product_id": "123e4567-e89b-12d3-a456-426614174000",
            "seller_id": "123e4567-e89b-12d3-a456-426614174001"
        }
        """
        product_id = request.data.get('product_id')
        seller_id = request.data.get('seller_id')
        
        # Validation
        if not product_id or not seller_id:
            return Response(
                {'error': 'product_id and seller_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if seller exists
        try:
            seller = User.objects.get(id=seller_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Seller not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if product exists
        from market.models import Product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Prevent users from chatting with themselves
        if request.user.id == seller.id:
            return Response(
                {'error': 'Cannot create conversation with yourself'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            product=product,
            buyer=request.user,
            seller=seller,
            defaults={
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            }
        )
        
        serializer = ConversationDetailSerializer(
            conversation, 
            context={'request': request}
        )
        
        return Response({
            'conversation': serializer.data,
            'created': created,
            'message': 'Conversation created' if created else 'Conversation already exists'
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get all messages in a conversation with pagination support
        
        Query params:
        - limit: Number of messages (default 50, max 100)
        - before: Message ID for cursor-based pagination
        
        Example:
        GET /api/chat/conversations/{uuid}/messages/?limit=50&before={message_id}
        """
        conversation = self.get_object()
        
        # Security check: Only buyer or seller can view messages
        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {'error': 'You do not have permission to view this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Pagination parameters
        limit = min(int(request.query_params.get('limit', 50)), 100)
        before_id = request.query_params.get('before')
        
        # Base queryset
        messages = conversation.messages.select_related('sender').all()
        
        # Cursor-based pagination
        if before_id:
            try:
                messages = messages.filter(created_at__lt=Message.objects.get(id=before_id).created_at)
            except Message.DoesNotExist:
                pass
        
        # Get messages with limit
        messages = messages.order_by('-created_at')[:limit]
        messages = list(reversed(messages))  # Oldest first
        
        # Mark unread messages as read (only messages sent by the other person)
        unread_messages = conversation.messages.filter(
            is_read=False
        ).exclude(sender=request.user)
        
        unread_count = unread_messages.count()
        if unread_count > 0:
            message_ids = list(unread_messages.values_list('id', flat=True))
            unread_messages.update(is_read=True, read_at=timezone.now())
            
            # Broadcast read receipts via WebSocket
            self._broadcast_read_receipt(
                str(conversation.id),
                [str(mid) for mid in message_ids],
                str(request.user.id)
            )
        
        serializer = MessageSerializer(
            messages, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'messages': serializer.data,
            'total_count': conversation.messages.count(),
            'returned_count': len(messages),
            'marked_as_read': unread_count,
            'has_more': conversation.messages.count() > len(messages)
        })
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark all messages in a conversation as read
        
        Example:
        POST /api/chat/conversations/{uuid}/mark_as_read/
        """
        conversation = self.get_object()
        
        # Security check
        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {'error': 'You do not have permission to access this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark messages as read
        unread_messages = conversation.messages.filter(
            is_read=False
        ).exclude(sender=request.user)
        
        message_ids = list(unread_messages.values_list('id', flat=True))
        updated = unread_messages.update(is_read=True, read_at=timezone.now())
        
        # Broadcast read receipts
        if updated > 0:
            self._broadcast_read_receipt(
                str(conversation.id),
                [str(mid) for mid in message_ids],
                str(request.user.id)
            )
        
        return Response({
            'message': f'{updated} message(s) marked as read',
            'count': updated
        })
    
    def retrieve(self, request, *args, **kwargs):
        """Get a single conversation with security check"""
        conversation = self.get_object()
        
        # Security check
        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {'error': 'You do not have permission to view this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    def _broadcast_read_receipt(self, conversation_id, message_ids, user_id):
        """Broadcast read receipt via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"conversation_{conversation_id}",
                {
                    'type': 'read_receipt',
                    'conversation_id': conversation_id,
                    'message_ids': message_ids,
                    'read_by': user_id,
                    'read_at': timezone.now().isoformat()
                }
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to broadcast read receipt: {e}")


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for sending and managing messages
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']  # No PUT/PATCH - messages can't be edited
    
    def get_queryset(self):
        """Only show messages from conversations user is part of"""
        user = self.request.user
        return Message.objects.filter(
            Q(conversation__buyer=user) | Q(conversation__seller=user)
        ).select_related('conversation', 'sender')
    
    def create(self, request):
        """
        Send a message in a conversation
        POST data: {
            conversation_id: uuid, 
            content: str, 
            message_type: str (optional),
            attachment_url: str (optional),
            attachment_size: int (optional),
            attachment_mime: str (optional),
            attachment_duration: float (optional),
            waveform_data: list (optional)
        }
        
        Example:
        POST /api/chat/messages/
        {
            "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
            "content": "Is this product still available?",
            "message_type": "text"
        }
        """
        conversation_id = request.data.get('conversation_id')
        content = request.data.get('content', '').strip()
        message_type = request.data.get('message_type', 'text')
        attachment_url = request.data.get('attachment_url', '').strip()
        attachment_size = request.data.get('attachment_size')
        attachment_mime = request.data.get('attachment_mime', '')
        attachment_duration = request.data.get('attachment_duration')
        waveform_data = request.data.get('waveform_data')
        
        # Validation
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not content and not attachment_url:
            return Response(
                {'error': 'Either content or attachment_url is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get conversation
        try:
            conversation = Conversation.objects.select_related(
                'buyer', 'seller', 'product'
            ).get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Security check: Only buyer or seller can send messages
        if request.user not in [conversation.buyer, conversation.seller]:
            return Response(
                {'error': 'You do not have permission to send messages in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=message_type,
            attachment_url=attachment_url if attachment_url else None,
            attachment_size=attachment_size,
            attachment_mime=attachment_mime,
            attachment_duration=attachment_duration,
            waveform_data=waveform_data,
            is_read=False
        )
        
        # Update conversation timestamp (already handled in model save, but explicit is good)
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        # Broadcast message via WebSocket
        self._broadcast_message(message, conversation)
        
        serializer = self.get_serializer(message, context={'request': request})
        return Response({
            'message': serializer.data,
            'success': 'Message sent successfully'
        }, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a message (only sender can delete their own messages)
        
        Example:
        DELETE /api/chat/messages/{uuid}/
        """
        message = self.get_object()
        
        # Only sender can delete their message
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversation_id = str(message.conversation.id)
        message_id = str(message.id)
        
        message.delete()
        
        # Broadcast deletion via WebSocket
        self._broadcast_message_deletion(conversation_id, message_id)
        
        return Response(
            {'message': 'Message deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    def _broadcast_message(self, message, conversation):
        """Broadcast new message via WebSocket to all participants"""
        try:
            channel_layer = get_channel_layer()
            
            # Serialize message for WebSocket
            serializer = MessageSerializer(message)
            
            async_to_sync(channel_layer.group_send)(
                f"conversation_{conversation.id}",
                {
                    'type': 'chat_message',
                    'conversation_id': str(conversation.id),
                    'message': serializer.data
                }
            )
            
            print(f"✅ Broadcasted message {message.id} to conversation {conversation.id}")
        except Exception as e:
            # Log error but don't fail the request
            print(f"❌ Failed to broadcast message: {e}")
    
    def _broadcast_message_deletion(self, conversation_id, message_id):
        """Broadcast message deletion via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"conversation_{conversation_id}",
                {
                    'type': 'message_deleted',
                    'conversation_id': conversation_id,
                    'message_id': message_id
                }
            )
        except Exception as e:
            print(f"❌ Failed to broadcast message deletion: {e}")