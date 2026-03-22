# server/chat/consumers.py
import json
from uuid import uuid4
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from .models import Conversation
from .utils import verify_ws_token
from .ws_protocol import build_envelope, parse_ws_message, PROTOCOL_VERSION
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
    EVENT_DEDUPE_TTL_SECONDS = 300

    def _user_display(self):
        """Safe user display name — works for both authenticated and anonymous users."""
        user = getattr(self, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return 'anonymous'
        return getattr(user, 'get_full_name', lambda: '')() or getattr(user, 'email', 'unknown')

    async def connect(self):
        # --- Initialize ALL instance state here, before any early return ---
        # This guarantees disconnect() and unregister_connection() never crash
        # even when connect() exits early due to auth/validation failure.
        self.conversations = set()
        self.conversation_cache = {}
        self.abuse_count = 0
        self.last_activity = time.time()
        self.last_heartbeat = time.time()
        self.connection_id = None
        self.delivered_messages = set()
        self.seen_inbound_event_ids = set()
        # --- End initialization ---

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

        self.connection_id = f"{self.user.id}_{self.channel_name}"

        await self.close_previous_connection()
        await self.register_connection()

        await self.accept()

        await self.channel_layer.group_add(
            f"conversation_{self.conversation_id}",
            self.channel_name
        )
        self.conversations.add(str(self.conversation_id))
        self.conversation_cache[str(self.conversation_id)] = conversation_access
        await self.mark_user_online(str(self.conversation_id))
        await self.broadcast_presence_event(str(self.conversation_id), 'online')
        await self.send_presence_snapshot(str(self.conversation_id))
        await self.send_read_snapshot(str(self.conversation_id))

        await self.log_event('ws_connected', str(self.conversation_id), None)
        await self.send_ack('connected', str(self.conversation_id), True)

        asyncio.create_task(self.heartbeat_monitor())

        print(f"✅ User {self._user_display()} ({self.user.id}) connected to WebSocket")

    async def disconnect(self, close_code):
        # self.conversations is always initialized (set in connect before any return)
        # so this loop is always safe.
        for conv_id in list(self.conversations):
            await self.broadcast_presence_event(str(conv_id), 'offline')
            await self.mark_user_offline(str(conv_id))
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )

        await self.unregister_connection()

        await self.log_event('ws_disconnected', None, None, close_code=close_code)
        print(f"❌ User {self._user_display()} disconnected (code: {close_code})")

    async def receive(self, text_data):
        self.last_activity = time.time()

        try:
            event, parse_error = parse_ws_message(text_data)
            if parse_error:
                await self.send_error(
                    'Malformed or unsupported websocket payload',
                    reason=parse_error,
                )
                return

            if await self.is_duplicate_inbound_event(event['event_id'], event.get('conversation_id')):
                await self.send_ack(
                    'duplicate',
                    event.get('conversation_id'),
                    False,
                    'duplicate_event_id',
                    correlation_id=event.get('correlation_id'),
                )
                return

            msg_type = event.get('type')
            payload = event.get('payload', {})

            if msg_type == 'chat.join':
                await self.handle_join(event.get('conversation_id'))
            elif msg_type == 'chat.leave':
                await self.handle_leave(event.get('conversation_id'))
            elif msg_type == 'chat.ping':
                self.last_heartbeat = time.time()
                await self.send_event(
                    event_type='chat.pong',
                    conversation_id=event.get('conversation_id') or str(self.conversation_id),
                    payload={'timestamp': str(payload.get('timestamp', ''))},
                    correlation_id=event.get('event_id'),
                )
            elif msg_type == 'chat.pong':
                self.last_heartbeat = time.time()
            elif msg_type == 'chat.typing.start':
                await self.handle_typing_event(event, is_typing=True)
            elif msg_type == 'chat.typing.stop':
                await self.handle_typing_event(event, is_typing=False)
            elif msg_type == 'chat.read.updated':
                await self.handle_read_event(event)
            elif msg_type == 'chat.message.send':
                await self.send_ack(
                    'chat.message.send',
                    event.get('conversation_id'),
                    False,
                    'message_send_via_rest_only',
                    correlation_id=event.get('event_id'),
                )
            else:
                await self.send_error(
                    'Unknown message type',
                    conv_id=event.get('conversation_id'),
                    reason=msg_type,
                    correlation_id=event.get('event_id'),
                )

        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await self.send_error('Websocket processing failed', reason=str(e))

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

                await self.send_event(
                    event_type='chat.ping',
                    conversation_id=str(self.conversation_id),
                    payload={'timestamp': current_time},
                )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"heartbeat_monitor_error user_id={self.user.id} error={str(e)}")

    async def handle_join(self, conv_id):
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
        await self.broadcast_presence_event(conv_id, 'online')
        await self.send_presence_snapshot(conv_id)
        await self.send_read_snapshot(conv_id)

        await self.log_event('ws_joined', conv_id, None)
        await self.send_ack('join', conv_id, True)

        print(f"✅ User {self._user_display()} joined conversation {conv_id}")

    async def handle_leave(self, conv_id):
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
            await self.broadcast_presence_event(conv_id, 'offline')

            await self.log_event('ws_left', conv_id, None)
            await self.send_ack('leave', conv_id, True)

            print(f"✅ User {self._user_display()} left conversation {conv_id}")

    async def handle_typing_event(self, event, is_typing):
        conv_id = event.get('conversation_id')

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
                'username': self._user_display(),
                'is_typing': is_typing,
                'event_id': event.get('event_id') or str(uuid4()),
                'occurred_at': event.get('occurred_at'),
                'correlation_id': event.get('correlation_id'),
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

        await self.send_event(
            event_type='chat.message.created',
            conversation_id=conv_id,
            payload={'message': message_data},
            event_id=event.get('event_id') or str(uuid4()),
            occurred_at=event.get('occurred_at'),
            seq=event.get('seq'),
            correlation_id=event.get('correlation_id'),
        )

    async def typing_indicator(self, event):
        if str(event['user_id']) == str(self.user.id):
            return

        if event.get('conversation_id') not in self.conversations:
            return

        await self.send_event(
            event_type='chat.typing.start' if event.get('is_typing') else 'chat.typing.stop',
            conversation_id=event.get('conversation_id'),
            payload={
                'actor_id': str(event['user_id']),
            },
            event_id=event.get('event_id') or str(uuid4()),
            occurred_at=event.get('occurred_at'),
            correlation_id=event.get('correlation_id'),
        )

    async def read_receipt(self, event):
        await self.send_event(
            event_type='chat.read.updated',
            conversation_id=event.get('conversation_id') or str(self.conversation_id),
            payload={
                'actor_id': str(event.get('read_by') or event.get('actor_id') or event.get('user_id')),
                'last_read_message_id': event.get('last_read_message_id'),
                'message_ids': event.get('message_ids'),
                'read_at': event.get('read_at'),
            },
            event_id=event.get('event_id') or str(uuid4()),
            occurred_at=event.get('occurred_at'),
        )

    async def message_deleted(self, event):
        await self.send_event(
            event_type='chat.message.deleted',
            conversation_id=event['conversation_id'],
            payload={'message_id': event['message_id']},
            event_id=event.get('event_id') or str(uuid4()),
            occurred_at=event.get('occurred_at'),
            seq=event.get('seq'),
        )

    async def user_status(self, event):
        status = event.get('status')
        event_type = 'chat.presence.online' if status == 'online' else 'chat.presence.offline'
        await self.send_event(
            event_type=event_type,
            conversation_id=event.get('conversation_id') or str(self.conversation_id),
            payload={
                'actor_id': str(event.get('user_id')),
                'status': status,
            },
            event_id=event.get('event_id') or str(uuid4()),
            occurred_at=event.get('occurred_at'),
        )

    async def force_disconnect(self, event):
        await self.log_event('ws_force_disconnect', None, 'duplicate_connection')
        await self.send_event(
            event_type='chat.warning',
            conversation_id=str(self.conversation_id),
            payload={'reason': 'New connection established elsewhere'},
        )
        await self.close(code=4411)

    async def send_event(self, event_type, conversation_id, payload, **kwargs):
        envelope = build_envelope(
            event_type=event_type,
            conversation_id=str(conversation_id),
            payload=payload,
            actor_id=str(self.user.id) if hasattr(self, 'user') and self.user.is_authenticated else None,
            protocol_version=PROTOCOL_VERSION,
            **kwargs,
        )
        await self.send(text_data=json.dumps(envelope))

    async def send_error(self, message, conv_id=None, reason=None, correlation_id=None):
        await self.send_event(
            event_type='chat.error',
            conversation_id=str(conv_id or self.conversation_id),
            payload={'message': message, 'reason': reason, 'delivered': False},
            correlation_id=correlation_id,
        )

    async def send_ack(self, action, conv_id, success, reason=None, correlation_id=None):
        await self.send_event(
            event_type='chat.message.ack',
            conversation_id=str(conv_id or self.conversation_id),
            payload={'action': action, 'success': bool(success), 'reason': reason},
            correlation_id=correlation_id,
        )

    async def check_product_available(self, conv_id):
        conversation_data = await self.validate_conversation_access(conv_id)
        if not conversation_data:
            await self.log_event('ws_product_unavailable', conv_id, 'product_deleted_or_inactive')
            await self.send_error(
                'This product is no longer available',
                conv_id=conv_id,
                reason='product_unavailable',
            )
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

    async def broadcast_presence_event(self, conv_id, status):
        if not conv_id:
            return
        await self.channel_layer.group_send(
            f"conversation_{conv_id}",
            {
                'type': 'user_status',
                'conversation_id': str(conv_id),
                'user_id': str(self.user.id) if getattr(self.user, 'is_authenticated', False) else 'anonymous',
                'status': status,
                'event_id': str(uuid4()),
                'occurred_at': time.time(),
            }
        )

    async def send_presence_snapshot(self, conv_id):
        snapshot = await self.build_presence_snapshot(conv_id)
        await self.send_event(
            event_type='chat.presence.snapshot',
            conversation_id=str(conv_id),
            payload={'participants': snapshot},
            event_id=str(uuid4()),
        )

    async def handle_read_event(self, event):
        conv_id = event.get('conversation_id')
        if not conv_id:
            await self.send_ack('chat.read.updated', self.conversation_id, False, 'missing_conversation_id', correlation_id=event.get('event_id'))
            return

        if conv_id not in self.conversations:
            await self.send_ack('chat.read.updated', conv_id, False, 'not_joined', correlation_id=event.get('event_id'))
            return

        conversation_data = await self.validate_conversation_access(conv_id)
        if not conversation_data:
            await self.send_ack('chat.read.updated', conv_id, False, 'unauthorized', correlation_id=event.get('event_id'))
            return

        payload = event.get('payload', {})
        last_read_message_id = payload.get('last_read_message_id')
        if not last_read_message_id:
            message_ids = payload.get('message_ids') if isinstance(payload.get('message_ids'), list) else []
            last_read_message_id = message_ids[-1] if message_ids else None

        if not last_read_message_id:
            await self.send_ack('chat.read.updated', conv_id, False, 'missing_last_read_message_id', correlation_id=event.get('event_id'))
            return

        accepted = await self.upsert_read_watermark(conv_id, str(self.user.id), str(last_read_message_id))
        if not accepted:
            await self.send_ack('chat.read.updated', conv_id, False, 'stale_watermark', correlation_id=event.get('event_id'))
            return

        await self.channel_layer.group_send(
            f"conversation_{conv_id}",
            {
                'type': 'read_receipt',
                'conversation_id': str(conv_id),
                'read_by': str(self.user.id),
                'last_read_message_id': str(last_read_message_id),
                'read_at': time.time(),
                'event_id': event.get('event_id') or str(uuid4()),
                'occurred_at': event.get('occurred_at'),
            }
        )

        await self.send_ack('chat.read.updated', conv_id, True, correlation_id=event.get('event_id'))

    async def send_read_snapshot(self, conv_id):
        snapshot = await self.build_read_snapshot(conv_id)
        await self.send_event(
            event_type='chat.read.snapshot',
            conversation_id=str(conv_id),
            payload={'watermarks': snapshot},
            event_id=str(uuid4()),
        )

    @database_sync_to_async
    def is_duplicate_inbound_event(self, event_id, conv_id):
        if not event_id:
            return False
        if event_id in self.seen_inbound_event_ids:
            return True
        self.seen_inbound_event_ids.add(event_id)
        dedupe_key = f"chat_ws_evt:{self.user.id}:{conv_id}:{event_id}"
        if cache.get(dedupe_key):
            return True
        cache.set(dedupe_key, True, self.EVENT_DEDUPE_TTL_SECONDS)
        return False

    @database_sync_to_async
    def register_connection(self):
        key = f"chat_active_conn:{self.user.id}"
        cache.set(key, self.channel_name, 3600)

    @database_sync_to_async
    def unregister_connection(self):
        if not getattr(self, 'user', None) or not getattr(self.user, 'is_authenticated', False):
            return

        key = f"chat_active_conn:{self.user.id}"
        current_channel = cache.get(key)

        if current_channel == self.channel_name:
            cache.delete(key)

        for conv_id in list(getattr(self, 'conversations', set())):
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
                    {'type': 'force_disconnect'}
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
        if not getattr(self, 'user', None) or not getattr(self.user, 'is_authenticated', False):
            return
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
    def build_presence_snapshot(self, conv_id):
        conversation_data = self.conversation_cache.get(str(conv_id), {})
        participant_ids = [
            str(conversation_data.get('buyer_id')) if conversation_data.get('buyer_id') else None,
            str(conversation_data.get('seller_id')) if conversation_data.get('seller_id') else None,
        ]
        snapshot = []
        for participant_id in filter(None, participant_ids):
            online_key = f"chat_online:{conv_id}:{participant_id}"
            snapshot.append({
                'actor_id': participant_id,
                'status': 'online' if cache.get(online_key) else 'offline',
            })
        return snapshot

    @database_sync_to_async
    def build_read_snapshot(self, conv_id):
        conversation_data = self.conversation_cache.get(str(conv_id), {})
        participant_ids = [
            str(conversation_data.get('buyer_id')) if conversation_data.get('buyer_id') else None,
            str(conversation_data.get('seller_id')) if conversation_data.get('seller_id') else None,
        ]
        watermarks = []
        for participant_id in filter(None, participant_ids):
            key = f"chat_read_wm:{conv_id}:{participant_id}"
            message_id = cache.get(key)
            if message_id:
                watermarks.append({'actor_id': participant_id, 'last_read_message_id': str(message_id)})
        return watermarks

    @database_sync_to_async
    def upsert_read_watermark(self, conv_id, actor_id, last_read_message_id):
        key = f"chat_read_wm:{conv_id}:{actor_id}"
        current = cache.get(key)

        def to_int(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        incoming_int = to_int(last_read_message_id)
        current_int = to_int(current)

        if current_int is not None and incoming_int is not None and incoming_int < current_int:
            return False

        cache.set(key, str(last_read_message_id), 60 * 60 * 24)
        return True

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
        user_id = getattr(self.user, 'id', None) if hasattr(self, 'user') else None
        log_msg = f"{action} user_id={user_id or 'unknown'}"

        if conversation_id:
            log_msg += f" conversation_id={conversation_id}"
        if error_reason:
            log_msg += f" reason={error_reason}"
        if close_code:
            log_msg += f" close_code={close_code}"

        if (error_reason or action.endswith('_denied') or 'rate_limited' in action
                or 'abuse' in action or 'timeout' in action or 'unavailable' in action):
            logger.warning(log_msg)
        else:
            logger.info(log_msg)