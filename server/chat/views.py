# chat/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Max
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
import hashlib

from .models import Conversation, Message, TransactionConfirmation
from .serializers import (
    ConversationSerializer,
    ConversationListSerializer,
    ConversationDetailSerializer,
    MessageSerializer
)
from .utils import generate_ws_token
from core.audit import audit_event

User = get_user_model()
logger = logging.getLogger('chat')


class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(buyer=user) | Q(seller=user)
        ).select_related(
            'buyer', 
            'seller', 
            'product',
            'transaction_confirmation'
        ).prefetch_related(
            'messages',
            'product__images'
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time')

    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    @action(detail=False, methods=['post'])
    def get_or_create(self, request):
        product_id = request.data.get('product_id')

        if not product_id:
            logger.warning(
                f"conversation_create_failed action=missing_product_id user_id={request.user.id}"
            )
            return Response(
                {'error': 'product_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from market.models import Product
        try:
            product = Product.objects.select_related('seller').get(id=product_id)
        except Product.DoesNotExist:
            logger.warning(
                f"conversation_create_failed action=product_not_found user_id={request.user.id} product_id={product_id}"
            )
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if product.deleted_at is not None:
            logger.warning(
                f"conversation_create_blocked action=product_deleted product_id={product_id} user_id={request.user.id}"
            )
            return Response(
                {'error': 'This product is no longer available'},
                status=status.HTTP_410_GONE
            )

        if product.status != 'active':
            logger.warning(
                f"conversation_create_blocked action=product_inactive product_id={product_id} "
                f"status={product.status} user_id={request.user.id}"
            )
            return Response(
                {'error': f'This product is {product.status} and not available for chat'},
                status=status.HTTP_410_GONE
            )

        seller = product.seller

        if request.user.id == seller.id:
            logger.warning(
                f"conversation_create_denied action=self_conversation user_id={request.user.id} product_id={product_id}"
            )
            return Response(
                {'error': 'Cannot create conversation with yourself'},
                status=status.HTTP_403_FORBIDDEN
            )

        conversation, created = Conversation.objects.get_or_create(
            product=product,
            buyer=request.user,
            seller=seller,
            defaults={
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            }
        )

        TransactionConfirmation.objects.get_or_create(
            conversation=conversation,
            defaults={
                'buyer': conversation.buyer,
                'seller': conversation.seller,
                'product': conversation.product,
            }
        )

        ws_token = generate_ws_token(str(conversation.id), str(request.user.id))

        logger.info(
            f"conversation_{'created' if created else 'retrieved'} conversation_id={conversation.id} "
            f"user_id={request.user.id} product_id={product_id} seller_id={seller.id}"
        )

        serializer = ConversationDetailSerializer(
            conversation, 
            context={'request': request}
        )

        return Response({
            'conversation': serializer.data,
            'ws_token': ws_token,
            'created': created,
            'message': 'Conversation created' if created else 'Conversation already exists'
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def confirm_sale(self, request, pk=None):
        conversation = self.get_object()

        if request.user != conversation.seller:
            return Response(
                {'error': 'Only the seller can confirm sale for this conversation.'},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            confirmation, _ = TransactionConfirmation.objects.select_for_update().get_or_create(
                conversation=conversation,
                defaults={
                    'buyer': conversation.buyer,
                    'seller': conversation.seller,
                    'product': conversation.product,
                }
            )
            confirmation.mark_seller_confirmed()
            confirmation.finalize_if_ready()
            confirmation.save()
            conversation.refresh_from_db(fields=['is_locked'])

        audit_event(request, action='chat.transaction.confirm_sale', session_id=str(conversation.id), extra={'status': confirmation.status, 'chat_locked': conversation.is_locked})
        return Response({
            'conversation_id': str(conversation.id),
            'status': confirmation.status,
            'seller_confirmed': confirmation.seller_confirmed_at is not None,
            'buyer_confirmed': confirmation.buyer_confirmed_at is not None,
            'chat_locked': conversation.is_locked,
            'message': 'Seller confirmation recorded.'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def confirm_receipt(self, request, pk=None):
        conversation = self.get_object()

        if request.user != conversation.buyer:
            return Response(
                {'error': 'Only the buyer can confirm receipt for this conversation.'},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            confirmation, _ = TransactionConfirmation.objects.select_for_update().get_or_create(
                conversation=conversation,
                defaults={
                    'buyer': conversation.buyer,
                    'seller': conversation.seller,
                    'product': conversation.product,
                }
            )
            confirmation.mark_buyer_confirmed()
            confirmation.finalize_if_ready()
            confirmation.save()
            conversation.refresh_from_db(fields=['is_locked'])

        audit_event(request, action='chat.transaction.confirm_receipt', session_id=str(conversation.id), extra={'status': confirmation.status, 'chat_locked': conversation.is_locked})
        return Response({
            'conversation_id': str(conversation.id),
            'status': confirmation.status,
            'seller_confirmed': confirmation.seller_confirmed_at is not None,
            'buyer_confirmed': confirmation.buyer_confirmed_at is not None,
            'chat_locked': conversation.is_locked,
            'message': 'Buyer confirmation recorded.'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def transaction_status(self, request, pk=None):
        conversation = self.get_object()

        if not conversation.user_is_participant(request.user):
            return Response(
                {'error': 'You do not have permission to access this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )

        confirmation, _ = TransactionConfirmation.objects.get_or_create(
            conversation=conversation,
            defaults={
                'buyer': conversation.buyer,
                'seller': conversation.seller,
                'product': conversation.product,
            }
        )

        return Response({
            'conversation_id': str(conversation.id),
            'status': confirmation.status,
            'seller_confirmed_at': confirmation.seller_confirmed_at,
            'buyer_confirmed_at': confirmation.buyer_confirmed_at,
            'completed_at': confirmation.completed_at,
            'chat_locked': conversation.is_locked,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def ws_token(self, request, pk=None):
        conversation = self.get_object()

        if not conversation.user_is_participant(request.user):
            return Response(
                {'error': 'You do not have permission to access this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )

        token = generate_ws_token(str(conversation.id), str(request.user.id))
        return Response(
            {
                'conversation_id': str(conversation.id),
                'ws_token': token,
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        conversation = self.get_object()

        if not conversation.user_is_participant(request.user):
            logger.warning(
                f"conversation_access_denied action=unauthorized_messages_access conversation_id={conversation.id} "
                f"user_id={request.user.id}"
            )
            return Response(
                {'error': 'You do not have permission to view this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )

        limit = min(int(request.query_params.get('limit', 50)), 100)
        before_id = request.query_params.get('before')

        messages = conversation.messages.select_related('sender').all()

        if before_id:
            try:
                messages = messages.filter(created_at__lt=Message.objects.get(id=before_id).created_at)
            except Message.DoesNotExist:
                pass

        messages = messages.order_by('-created_at')[:limit]
        messages = list(reversed(messages))

        unread_messages = conversation.messages.filter(
            is_read=False
        ).exclude(sender=request.user)

        unread_count = unread_messages.count()
        if unread_count > 0:
            message_ids = list(unread_messages.values_list('id', flat=True))
            unread_messages.update(is_read=True, read_at=timezone.now())

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
        conversation = self.get_object()

        if not conversation.user_is_participant(request.user):
            logger.warning(
                f"conversation_access_denied action=unauthorized_mark_read conversation_id={conversation.id} "
                f"user_id={request.user.id}"
            )
            return Response(
                {'error': 'You do not have permission to access this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )

        unread_messages = conversation.messages.filter(
            is_read=False
        ).exclude(sender=request.user)

        message_ids = list(unread_messages.values_list('id', flat=True))
        updated = unread_messages.update(is_read=True, read_at=timezone.now())

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
        conversation = self.get_object()

        if not conversation.user_is_participant(request.user):
            logger.warning(
                f"conversation_access_denied action=unauthorized_retrieve conversation_id={conversation.id} "
                f"user_id={request.user.id}"
            )
            return Response(
                {'error': 'You do not have permission to view this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    def _broadcast_read_receipt(self, conversation_id, message_ids, user_id):
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
            print(f"Failed to broadcast read receipt: {e}")


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']

    MESSAGE_RATE_LIMIT = 20
    MESSAGE_RATE_WINDOW = 60
    CONVERSATION_RATE_LIMIT = 10
    CONVERSATION_RATE_WINDOW = 60
    IDEMPOTENCY_WINDOW = 5

    def get_queryset(self):
        user = self.request.user
        queryset = Message.objects.filter(
            Q(conversation__buyer=user) | Q(conversation__seller=user)
        ).select_related('conversation', 'sender')

        conversation_id = self.request.query_params.get('conversation')
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)

        return queryset

    def _check_rate_limit(self, user_id, conversation_id):
        user_key = f"chat_msg_rate:{user_id}"
        conv_key = f"chat_msg_rate:{user_id}:{conversation_id}"
        
        user_count = cache.get(user_key, 0)
        conv_count = cache.get(conv_key, 0)
        
        if user_count >= self.MESSAGE_RATE_LIMIT:
            return False, 'global'
        
        if conv_count >= self.CONVERSATION_RATE_LIMIT:
            return False, 'conversation'
        
        cache.set(user_key, user_count + 1, self.MESSAGE_RATE_WINDOW)
        cache.set(conv_key, conv_count + 1, self.CONVERSATION_RATE_WINDOW)
        
        return True, None

    def _generate_idempotency_key(self, user_id, conversation_id, content, message_type):
        key_data = f"{user_id}:{conversation_id}:{content[:100]}:{message_type}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _check_duplicate(self, idempotency_key):
        cache_key = f"chat_msg_idem:{idempotency_key}"
        cached_message_id = cache.get(cache_key)
        
        if cached_message_id:
            try:
                message = Message.objects.get(id=cached_message_id)
                return True, message
            except Message.DoesNotExist:
                pass
        
        return False, None

    def _store_idempotency(self, idempotency_key, message_id):
        cache_key = f"chat_msg_idem:{idempotency_key}"
        cache.set(cache_key, str(message_id), self.IDEMPOTENCY_WINDOW)

    def create(self, request):
        conversation_id = request.data.get('conversation_id')
        content = request.data.get('content', '').strip()
        message_type = request.data.get('message_type', 'text')
        attachment_url = request.data.get('attachment_url', '').strip()
        attachment_size = request.data.get('attachment_size')
        attachment_mime = request.data.get('attachment_mime', '')
        attachment_duration = request.data.get('attachment_duration')
        waveform_data = request.data.get('waveform_data')

        if not conversation_id:
            logger.warning(
                f"message_create_failed action=missing_conversation_id user_id={request.user.id}"
            )
            return Response(
                {'error': 'conversation_id is required', 'delivered': False},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not content and not attachment_url:
            logger.warning(
                f"message_create_failed action=missing_content user_id={request.user.id} conversation_id={conversation_id}"
            )
            return Response(
                {'error': 'Either content or attachment_url is required', 'delivered': False},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            conversation = Conversation.objects.select_related(
                'buyer', 'seller', 'product'
            ).get(id=conversation_id)
        except Conversation.DoesNotExist:
            logger.warning(
                f"message_create_failed action=conversation_not_found user_id={request.user.id} conversation_id={conversation_id}"
            )
            return Response(
                {'error': 'Conversation not found', 'delivered': False},
                status=status.HTTP_404_NOT_FOUND
            )

        if not conversation.user_is_participant(request.user):
            logger.warning(
                f"message_create_denied action=unauthorized_send conversation_id={conversation_id} "
                f"user_id={request.user.id} product_id={conversation.product.id}"
            )
            return Response(
                {'error': 'You do not have permission to send messages in this conversation', 'delivered': False},
                status=status.HTTP_403_FORBIDDEN
            )

        if not conversation.product:
            logger.warning(
                f"message_blocked action=product_deleted conversation_id={conversation_id} user_id={request.user.id}"
            )
            return Response(
                {'error': 'This product is no longer available', 'delivered': False},
                status=status.HTTP_410_GONE
            )

        if conversation.product.deleted_at is not None:
            logger.warning(
                f"message_blocked action=product_soft_deleted conversation_id={conversation_id} "
                f"product_id={conversation.product.id} user_id={request.user.id}"
            )
            return Response(
                {'error': 'This product is no longer available', 'delivered': False},
                status=status.HTTP_410_GONE
            )

        if conversation.product.status != 'active':
            logger.warning(
                f"message_blocked action=product_inactive conversation_id={conversation_id} "
                f"product_id={conversation.product.id} status={conversation.product.status} user_id={request.user.id}"
            )
            return Response(
                {'error': f'This product is {conversation.product.status} and not available for chat', 'delivered': False},
                status=status.HTTP_410_GONE
            )

        if conversation.is_locked:
            logger.warning(
                f"message_blocked action=conversation_locked conversation_id={conversation_id} user_id={request.user.id}"
            )
            return Response(
                {'error': 'This chat is locked after dual confirmation. Please use dispute support for further issues.', 'delivered': False},
                status=status.HTTP_423_LOCKED
            )

        allowed, limit_type = self._check_rate_limit(str(request.user.id), str(conversation_id))
        if not allowed:
            logger.warning(
                f"message_rate_limited user_id={request.user.id} conversation_id={conversation_id} "
                f"limit_type={limit_type}"
            )
            return Response(
                {'error': f'Rate limit exceeded. Please slow down.', 'delivered': False},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        idempotency_key = self._generate_idempotency_key(
            str(request.user.id), 
            str(conversation_id), 
            content or attachment_url,
            message_type
        )
        
        is_duplicate, existing_message = self._check_duplicate(idempotency_key)
        if is_duplicate:
            logger.info(
                f"message_duplicate_detected message_id={existing_message.id} conversation_id={conversation_id} "
                f"user_id={request.user.id}"
            )
            serializer = self.get_serializer(existing_message, context={'request': request})
            return Response({
                'message': serializer.data,
                'success': 'Message already exists',
                'delivered': True,
                'duplicate': True
            }, status=status.HTTP_200_OK)

        try:
            with transaction.atomic():
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

                conversation.updated_at = timezone.now()
                conversation.save(update_fields=['updated_at'])

                self._store_idempotency(idempotency_key, message.id)

            logger.info(
                f"message_created message_id={message.id} conversation_id={conversation_id} "
                f"user_id={request.user.id} message_type={message_type}"
            )

        except Exception as e:
            logger.error(
                f"message_create_failed action=db_error user_id={request.user.id} "
                f"conversation_id={conversation_id} error={str(e)}"
            )
            return Response(
                {'error': 'Failed to save message', 'delivered': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        broadcast_success = self._broadcast_message(message, conversation)

        serializer = self.get_serializer(message, context={'request': request})
        return Response({
            'message': serializer.data,
            'success': 'Message sent successfully',
            'delivered': True,
            'broadcast': broadcast_success
        }, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()

        if message.sender != request.user:
            logger.warning(
                f"message_delete_denied action=unauthorized_delete message_id={message.id} "
                f"user_id={request.user.id} sender_id={message.sender.id}"
            )
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )

        conversation_id = str(message.conversation.id)
        message_id = str(message.id)

        logger.info(
            f"message_deleted message_id={message_id} conversation_id={conversation_id} user_id={request.user.id}"
        )

        message.delete()

        self._broadcast_message_deletion(conversation_id, message_id)

        return Response(
            {'message': 'Message deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )

    def _broadcast_message(self, message, conversation):
        try:
            channel_layer = get_channel_layer()

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
            return True
        except Exception as e:
            logger.error(f"message_broadcast_failed message_id={message.id} error={str(e)}")
            print(f"❌ Failed to broadcast message: {e}")
            return False

    def _broadcast_message_deletion(self, conversation_id, message_id):
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