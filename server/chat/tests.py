from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from market.models import Category, Product
from .models import Conversation, Message


User = get_user_model()


class ChatConversationFlowTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            password='testpass123',
            first_name='Buyer',
            last_name='User',
            role='buyer',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='testpass123',
            first_name='Seller',
            last_name='User',
            role='seller',
            is_verified=True,
        )

        self.category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Wireless Keyboard',
            description='Compact wireless keyboard',
            category=self.category,
            location=None,
            price=Decimal('49.99'),
            quantity=5,
            status='active',
        )

    def test_buyer_can_create_conversation_for_product_and_seller_can_reply(self):
        self.client.force_authenticate(user=self.buyer)
        create_url = reverse('chat:conversation-get-or-create')
        create_response = self.client.post(create_url, {'product_id': str(self.product.id)}, format='json')

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        conversation_id = create_response.data['conversation']['id']
        self.assertTrue(Conversation.objects.filter(id=conversation_id).exists())

        self.client.force_authenticate(user=self.seller)
        message_url = reverse('chat:message-list')
        message_response = self.client.post(
            message_url,
            {
                'conversation_id': conversation_id,
                'content': 'Hi! Yes, this item is available.',
                'message_type': 'text',
            },
            format='json',
        )

        self.assertEqual(message_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Message.objects.filter(
                conversation_id=conversation_id,
                sender=self.seller,
                content='Hi! Yes, this item is available.',
            ).exists()
        )

    def test_seller_cannot_create_conversation_with_own_product(self):
        self.client.force_authenticate(user=self.seller)
        create_url = reverse('chat:conversation-get-or-create')

        response = self.client.post(create_url, {'product_id': str(self.product.id)}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Cannot create conversation with yourself')
