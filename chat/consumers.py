import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality.
    Handles: joining conversations, typing indicators, new messages, read receipts.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Get user from Django session (automatically handled by AuthMiddlewareStack)
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            # Close connection with auth error code
            await self.close(code=4401)
            return
        
        # Track which conversations this user has joined
        self.conversations = set()
        
        # Accept the WebSocket connection
        await self.accept()
        
        print(f"✅ User {self.user.get_full_name()} ({self.user.id}) connected to WebSocket")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Unsubscribe from all conversations
        for conv_id in self.conversations:
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )
        
        if hasattr(self, 'user'):
            print(f"❌ User {self.user.get_full_name()} disconnected (code: {close_code})")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages from client"""
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            
            # Route message based on type
            if msg_type == 'join':
                await self.handle_join(data)
            elif msg_type == 'leave':
                await self.handle_leave(data)
            elif msg_type == 'typing':
                await self.handle_typing(data)
            elif msg_type == 'ping':
                await self.send(json.dumps({
                    'type': 'pong',
                    'timestamp': str(data.get('timestamp', ''))
                }))
            else:
                await self.send_error(f"Unknown message type: {msg_type}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            await self.send_error(str(e))
    
    async def handle_join(self, data):
        """Handle user joining a conversation"""
        conv_id = data.get('conversation_id')
        
        if not conv_id:
            await self.send_error("conversation_id is required")
            return
        
        # Verify user has access to this conversation
        has_access = await self.check_access(conv_id)
        if not has_access:
            await self.send_error(
                "You do not have access to this conversation",
                conv_id
            )
            return
        
        # Join the conversation room
        await self.channel_layer.group_add(
            f"conversation_{conv_id}",
            self.channel_name
        )
        
        self.conversations.add(conv_id)
        
        # Send confirmation
        await self.send(json.dumps({
            'type': 'joined',
            'conversation_id': conv_id,
            'message': 'Successfully joined conversation'
        }))
        
        print(f"✅ User {self.user.get_full_name()} joined conversation {conv_id}")
    
    async def handle_leave(self, data):
        """Handle user leaving a conversation"""
        conv_id = data.get('conversation_id')
        
        if not conv_id:
            return
        
        if conv_id in self.conversations:
            await self.channel_layer.group_discard(
                f"conversation_{conv_id}",
                self.channel_name
            )
            self.conversations.remove(conv_id)
            
            await self.send(json.dumps({
                'type': 'left',
                'conversation_id': conv_id,
                'message': 'Successfully left conversation'
            }))
            
            print(f"✅ User {self.user.get_full_name()} left conversation {conv_id}")
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        conv_id = data.get('conversation_id')
        is_typing = data.get('is_typing', False)
        
        if conv_id not in self.conversations:
            return
        
        # Broadcast typing to others in conversation
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
    
    # ============ Handler methods (called from channel layer) ============
    
    async def chat_message(self, event):
        """
        Handle new message broadcast from REST API
        Called when a new message is sent via the MessageViewSet
        """
        await self.send(text_data=json.dumps({
            'type': 'message',
            'conversation_id': event.get('conversation_id'),
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        """
        Handle typing indicator broadcast
        Don't send typing indicator back to the person who's typing
        """
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
        """
        Handle read receipt broadcast
        Called when messages are marked as read
        """
        # Don't send read receipt back to the person who read the messages
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
        """
        Handle message deletion broadcast
        Called when a message is deleted via the MessageViewSet
        """
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'conversation_id': event['conversation_id'],
            'message_id': event['message_id']
        }))
    
    async def user_status(self, event):
        """
        Handle user online/offline status broadcast
        Optional: implement if you want to show online status
        """
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'status': event['status'],  # 'online' or 'offline'
            'last_seen': event.get('last_seen')
        }))
    
    # ============ Helper methods ============
    
    async def send_error(self, message, conv_id=None):
        """Send error message to client"""
        error_data = {
            'type': 'error',
            'message': message
        }
        if conv_id:
            error_data['conversation_id'] = conv_id
        
        await self.send(text_data=json.dumps(error_data))
    
    @database_sync_to_async
    def check_access(self, conv_id):
        """Check if user has access to conversation"""
        try:
            conv = Conversation.objects.get(id=conv_id)
            return conv.buyer == self.user or conv.seller == self.user
        except Conversation.DoesNotExist:
            return False