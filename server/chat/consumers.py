# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from .models import Conversation
from .utils import verify_ws_token
import logging
import time
import asyncio
from urllib.parse import parse_qs

logger = logging.getLogger('chat')


class ChatConsumer(AsyncWebsocketConsumer):
    
    TYPING_RATE_LIMIT = 5
    TYPING_RATE_WINDOW = 10
    ABUSE_THRESHOLD = 3
    ABUSE_WINDOW = 60
    HEARTBEAT_INTERVAL = 30
    HEARTBEAT_TIMEOUT = 45
    IDLE_TIMEOUT = 300

    async def connect(self):
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')

        if not self.user.is_authenticated:
            await self.log_event('ws_connect_denied', None, 'unauthenticated')
            await self.close(code=4401)
            return

        if not self.conversation_id:
            await self.log_event('ws_connect_denied', None, 'missing_conversation_id')
            await self.close(code=4400)
            return

        query_string = self.scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if not token:
            await self.log_event('ws_connect_denied', str(self.conversation_id), 'missing_token')
            await self.close(code=4401)
            return

        if not verify_ws_token(str(self.conversation_id), str(self.user.id), token):
            await self.log_event('ws_connect_denied', str(self.conversation_id), 'invalid_token')
            await self.close(code=4403)
            return

        conversation_access = await self.validate_conversation_access(str(self.conversation_id))
        if not conversation_access:
            await self.log_event('ws_connect_denied', str(self.conversation_id), 'unauthorized_conversation')
            await self.close(code=4403)
            return

        self.conversations = set()
        self.conversation_cache = {}
        self.abuse_count = 0
        self.last_activity = time.time()
        self.last_heartbeat = time.time()
        self.connection_id = f"{self.user.id}_{self.channel_name}"
        self.delivered_messages = set()

        await self.close_previous_connection()
        await self.register_connection()

        await self.accept()

        await self.log_event('ws_connected', str(self.conversation_id), None)
        await self.send_ack('connected', None, True)
        
        asyncio.create_task(self.heartbeat_monitor())
        
        print(f"✅ User {self.user.get_full_name()} ({self.user.id}) connected to WebSocket")

    async def disconnect(self, close_code):
        for conv_id in list(self.conversations):
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )

        await self.unregister_connection()

        if hasattr(self, 'user'):
            await self.log_event('ws_disconnected', None, None, close_code=close_code)
            print(f"❌ User {self.user.get_full_name()} disconnected (code: {close_code})")

    async def receive(self, text_data):
        self.last_activity = time.time()
        
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')

            if msg_type == 'join':
                await self.handle_join(data)
            elif msg_type == 'leave':
                await self.handle_leave(data)
            elif msg_type == 'typing':
                await self.handle_typing(data)
            elif msg_type == 'ping':
                self.last_heartbeat = time.time()
                await self.send(json.dumps({
                    'type': 'pong',
                    'timestamp': str(data.get('timestamp', ''))
                }))
            elif msg_type == 'heartbeat':
                self.last_heartbeat = time.time()
                await self.send(json.dumps({
                    'type': 'heartbeat_ack',
                    'timestamp': time.time()
                }))
            else:
                await self.send_error(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await self.send_error(str(e))

    async def heartbeat_monitor(self):
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                current_time = time.time()
                
                if current_time - self.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                    await self.log_event('ws_heartbeat_timeout', None, 'no_heartbeat')
                    await self.close(code=4408)
                    break
                
                if current_time - self.last_activity > self.IDLE_TIMEOUT:
                    await self.log_event('ws_idle_timeout', None, 'inactive')
                    await self.close(code=4409)
                    break

                for conv_id in list(self.conversations):
                    if not await self.check_product_available(conv_id):
                        break
                
                await self.send(json.dumps({
                    'type': 'heartbeat_request',
                    'timestamp': current_time
                }))
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"heartbeat_monitor_error user_id={self.user.id} error={str(e)}")

    async def handle_join(self, data):
        conv_id = data.get('conversation_id')

        if not conv_id:
            await self.send_error("conversation_id is required")
            return

        if not self.user.is_authenticated:
            await self.log_event('ws_join_denied', conv_id, 'unauthenticated')
            await self.send_ack('join', conv_id, False, 'unauthenticated')
            await self.close(code=4401)
            return

        if not await self.verify_connection_valid():
            await self.log_event('ws_join_denied', conv_id, 'stale_connection')
            await self.send_ack('join', conv_id, False, 'stale_connection')
            await self.close(code=4410)
            return

        conversation_data = await self.validate_conversation_access(conv_id)
        if not conversation_data:
            await self.log_event('ws_join_denied', conv_id, 'unauthorized')
            await self.send_ack('join', conv_id, False, 'unauthorized')
            await self.send_error(
                "You do not have access to this conversation",
                conv_id
            )
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(
            f"conversation_{conv_id}",
            self.channel_name
        )

        self.conversations.add(conv_id)
        self.conversation_cache[conv_id] = conversation_data

        await self.mark_user_online(conv_id)

        await self.log_event('ws_joined', conv_id, None)

        await self.send(json.dumps({
            'type': 'joined',
            'conversation_id': conv_id,
            'message': 'Successfully joined conversation',
            'ack': True
        }))

        print(f"✅ User {self.user.get_full_name()} joined conversation {conv_id}")

    async def handle_leave(self, data):
        conv_id = data.get('conversation_id')

        if not conv_id:
            return

        if conv_id in self.conversations:
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )
            self.conversations.remove(conv_id)
            self.conversation_cache.pop(conv_id, None)

            await self.mark_user_offline(conv_id)

            await self.log_event('ws_left', conv_id, None)

            await self.send(json.dumps({
                'type': 'left',
                'conversation_id': conv_id,
                'message': 'Successfully left conversation',
                'ack': True
            }))

            print(f"✅ User {self.user.get_full_name()} left conversation {conv_id}")

    async def handle_typing(self, data):
        conv_id = data.get('conversation_id')
        is_typing = data.get('is_typing', False)

        if not conv_id:
            return

        if not self.user.is_authenticated:
            await self.log_event('ws_typing_denied', conv_id, 'unauthenticated')
            await self.send_ack('typing', conv_id, False, 'unauthenticated')
            await self.close(code=4401)
            return

        if conv_id not in self.conversations:
            await self.log_event('ws_typing_denied', conv_id, 'not_joined')
            await self.send_ack('typing', conv_id, False, 'not_joined')
            return

        if not await self.verify_connection_valid():
            await self.log_event('ws_typing_denied', conv_id, 'stale_connection')
            await self.close(code=4410)
            return

        if not await self.check_product_available(conv_id):
            return

        conversation_data = await self.validate_conversation_access(conv_id)
        if not conversation_data:
            await self.log_event('ws_typing_denied', conv_id, 'unauthorized')
            await self.send_ack('typing', conv_id, False, 'unauthorized')
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )
            self.conversations.discard(conv_id)
            self.conversation_cache.pop(conv_id, None)
            await self.close(code=4403)
            return

        allowed = await self.check_typing_rate_limit(str(self.user.id), conv_id)
        if not allowed:
            await self.log_event('ws_typing_rate_limited', conv_id, 'rate_limit_exceeded')
            await self.send_ack('typing', conv_id, False, 'rate_limited')
            self.abuse_count += 1
            
            if self.abuse_count >= self.ABUSE_THRESHOLD:
                await self.log_event('ws_abuse_detected', conv_id, f'abuse_count={self.abuse_count}')
                await self.close(code=4429)
                return
            
            return

        await self.channel_layer.group_send(
            f"conversation_{conv_id}",
            {
                'type': 'typing_indicator',
                'conversation_id': conv_id,
                'user_id': str(self.user.id),
                'username': self.user.get_full_name(),
                'is_typing': is_typing
            }
        )

    async def chat_message(self, event):
        conv_id = event.get('conversation_id')
        message_data = event.get('message', {})
        message_id = message_data.get('id')
        
        if not message_id:
            await self.log_event('ws_message_no_id', conv_id, 'missing_message_id')
            return
        
        if conv_id not in self.conversations:
            return

        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        if not await self.verify_connection_valid():
            await self.close(code=4410)
            return

        if not await self.check_product_available(conv_id):
            return

        conversation_data = await self.validate_conversation_access(conv_id)
        if not conversation_data:
            await self.log_event('ws_message_denied', conv_id, 'unauthorized')
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )
            self.conversations.discard(conv_id)
            self.conversation_cache.pop(conv_id, None)
            await self.close(code=4403)
            return

        if message_id in self.delivered_messages:
            await self.log_event('ws_message_duplicate', conv_id, f'already_delivered_msg_id={message_id}')
            return

        self.delivered_messages.add(message_id)

        await self.send(text_data=json.dumps({
            'type': 'message',
            'conversation_id': conv_id,
            'message': message_data,
            'delivered': True
        }))

    async def typing_indicator(self, event):
        if str(event['user_id']) == str(self.user.id):
            return

        await self.send(text_data=json.dumps({
            'type': 'typing',
            'conversation_id': event.get('conversation_id'),
            'user': {
                'id': event['user_id'],
                'username': event['username']
            },
            'is_typing': event['is_typing']
        }))

    async def read_receipt(self, event):
        if str(event['read_by']) == str(self.user.id):
            return

        await self.send(text_data=json.dumps({
            'type': 'read',
            'conversation_id': event['conversation_id'],
            'message_ids': event['message_ids'],
            'read_by': event['read_by'],
            'read_at': event.get('read_at')
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'conversation_id': event['conversation_id'],
            'message_id': event['message_id']
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'status': event['status'],
            'last_seen': event.get('last_seen')
        }))

    async def force_disconnect(self, event):
        await self.log_event('ws_force_disconnect', None, 'duplicate_connection')
        await self.send(json.dumps({
            'type': 'disconnected',
            'reason': 'New connection established elsewhere'
        }))
        await self.close(code=4411)

    async def send_error(self, message, conv_id=None):
        error_data = {
            'type': 'error',
            'message': message,
            'delivered': False
        }
        if conv_id:
            error_data['conversation_id'] = conv_id

        await self.send(text_data=json.dumps(error_data))

    async def send_ack(self, action, conv_id, success, reason=None):
        ack_data = {
            'type': 'ack',
            'action': action,
            'success': success
        }
        if conv_id:
            ack_data['conversation_id'] = conv_id
        if reason:
            ack_data['reason'] = reason

        await self.send(text_data=json.dumps(ack_data))

    async def check_product_available(self, conv_id):
        conversation_data = await self.validate_conversation_access(conv_id)
        if not conversation_data:
            await self.log_event('ws_product_unavailable', conv_id, 'product_deleted_or_inactive')
            await self.send(json.dumps({
                'type': 'product_unavailable',
                'conversation_id': conv_id,
                'message': 'This product is no longer available'
            }))
            
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )
            self.conversations.discard(conv_id)
            self.conversation_cache.pop(conv_id, None)
            await self.mark_user_offline(conv_id)
            
            await self.close(code=4410)
            return False
        return True

    @database_sync_to_async
    def register_connection(self):
        key = f"chat_active_conn:{self.user.id}"
        cache.set(key, self.channel_name, 3600)

    @database_sync_to_async
    def unregister_connection(self):
        key = f"chat_active_conn:{self.user.id}"
        current_channel = cache.get(key)
        
        if current_channel == self.channel_name:
            cache.delete(key)
        
        for conv_id in list(self.conversations):
            self.mark_user_offline_sync(conv_id)

    @database_sync_to_async
    def close_previous_connection(self):
        key = f"chat_active_conn:{self.user.id}"
        previous_channel = cache.get(key)
        
        if previous_channel and previous_channel != self.channel_name:
            try:
                from asgiref.sync import async_to_sync
                channel_layer = self.channel_layer
                
                async_to_sync(channel_layer.send)(
                    previous_channel,
                    {
                        'type': 'force_disconnect'
                    }
                )
                
                logger.info(
                    f"ws_previous_closed user_id={self.user.id} "
                    f"old_channel={previous_channel} new_channel={self.channel_name}"
                )
            except Exception as e:
                logger.error(f"close_previous_error user_id={self.user.id} error={str(e)}")

    @database_sync_to_async
    def verify_connection_valid(self):
        key = f"chat_active_conn:{self.user.id}"
        current_channel = cache.get(key)
        
        return current_channel == self.channel_name

    @database_sync_to_async
    def mark_user_online(self, conv_id):
        key = f"chat_online:{conv_id}:{self.user.id}"
        cache.set(key, True, 60)

    @database_sync_to_async
    def mark_user_offline(self, conv_id):
        key = f"chat_online:{conv_id}:{self.user.id}"
        cache.delete(key)

    def mark_user_offline_sync(self, conv_id):
        key = f"chat_online:{conv_id}:{self.user.id}"
        cache.delete(key)

    @database_sync_to_async
    def validate_conversation_access(self, conv_id):
        try:
            conv = Conversation.objects.select_related('buyer', 'seller', 'product').get(id=conv_id)
            
            if not conv.user_is_participant(self.user):
                return None
            
            if not conv.product:
                return None
            
            if conv.product.deleted_at is not None:
                return None
            
            if conv.product.status != 'active':
                return None
            
            return {
                'id': str(conv.id),
                'buyer_id': str(conv.buyer.id),
                'seller_id': str(conv.seller.id),
                'product_id': str(conv.product.id)
            }
        except Conversation.DoesNotExist:
            return None
        except Exception:
            return None

    @database_sync_to_async
    def check_typing_rate_limit(self, user_id, conv_id):
        key = f"chat_typing_rate:{user_id}:{conv_id}"
        count = cache.get(key, 0)
        
        if count >= self.TYPING_RATE_LIMIT:
            return False
        
        cache.set(key, count + 1, self.TYPING_RATE_WINDOW)
        return True

    @database_sync_to_async
    def log_event(self, action, conversation_id, error_reason, close_code=None):
        log_msg = f"{action} user_id={self.user.id if hasattr(self, 'user') else 'unknown'}"
        
        if conversation_id:
            log_msg += f" conversation_id={conversation_id}"
        
        if error_reason:
            log_msg += f" reason={error_reason}"
        
        if close_code:
            log_msg += f" close_code={close_code}"
        
        if error_reason or action.endswith('_denied') or 'rate_limited' in action or 'abuse' in action or 'timeout' in action or 'unavailable' in action:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)