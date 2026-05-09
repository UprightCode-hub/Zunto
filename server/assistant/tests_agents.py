from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import re
from uuid import UUID
from unittest.mock import patch

from assistant.models import ConversationSession, DisputeTicket
from assistant.services.customer_service_agent import CustomerServiceAgent
from assistant.services.gigi_agent import GigiRecommendationAgent
from assistant.utils.validators import is_spam_message, validate_chat_request
from orders.models import Order, OrderItem


User = get_user_model()
UUID_RE = re.compile(
    r'\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b',
    re.I,
)


class OfflineAdapter:
    model_name = 'offline-test'
    cooldown_seconds = 0
    rate_limited_until = 0

    def is_available(self):
        return False


class AgentSmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='agent-smoke@example.com',
            password='TestPass123!',
            first_name='Ada',
            last_name='Buyer',
            is_verified=True,
        )

    @patch('assistant.services.gigi_agent.LocalModelAdapter.get_instance', return_value=OfflineAdapter())
    def test_gigi_recommendation_agent_empty_message_smoke(self, _adapter_mock):
        session = ConversationSession.objects.create(
            session_id='gigi-agent-smoke',
            user=self.user,
            assistant_mode='homepage_reco',
            assistant_lane='inbox',
            context_type=ConversationSession.CONTEXT_TYPE_SUPPORT,
        )

        result = GigiRecommendationAgent().run(
            conversation_history=[],
            user_message='',
            session=session,
        )

        self.assertEqual(result['source'], 'gigi_agent_empty_message')
        self.assertIsInstance(result.get('reply'), str)
        self.assertTrue(result['reply'])
        self.assertEqual(result['metadata']['assistant_mode'], 'homepage_reco')

        session.refresh_from_db()
        self.assertEqual(session.context_type, ConversationSession.CONTEXT_TYPE_RECOMMENDATION)

    def test_customer_service_agent_greeting_smoke(self):
        session = ConversationSession.objects.create(
            session_id='customer-service-agent-smoke',
            user=self.user,
            assistant_mode='customer_service',
            assistant_lane='customer_service',
            context_type=ConversationSession.CONTEXT_TYPE_SUPPORT,
        )

        result = CustomerServiceAgent(session).run('hello')

        self.assertEqual(result['source'], 'customer_service_agent')
        self.assertEqual(result['metadata']['assistant_mode'], 'customer_service')
        self.assertEqual(result['metadata']['intent'], 'greeting')
        self.assertIn('Customer Service', result['reply'])

    def test_customer_service_agent_adds_empathy_for_frustration(self):
        session = ConversationSession.objects.create(
            session_id='customer-service-agent-frustrated',
            user=self.user,
            assistant_mode='customer_service',
            assistant_lane='customer_service',
            context_type=ConversationSession.CONTEXT_TYPE_SUPPORT,
        )

        result = CustomerServiceAgent(session).run('I am very frustrated and tired of this nonsense')

        self.assertTrue(result['metadata']['empathy_applied'])
        self.assertIn(result['metadata']['emotion'], {'angry', 'frustrated'})
        self.assertIn('payment, refund, delivery, or a buyer/seller dispute', result['reply'])

    def test_customer_service_agent_links_explicit_order_number(self):
        seller = User.objects.create_user(
            email='agent-seller@example.com',
            password='TestPass123!',
            first_name='Sade',
            is_verified=True,
        )
        order = Order.objects.create(
            customer=self.user,
            order_number='ORD-20260509-ABCD',
            status='shipped',
            payment_status='paid',
            total_amount=Decimal('1500.00'),
        )
        OrderItem.objects.create(
            order=order,
            seller=seller,
            product=None,
            product_name='Test Phone',
            quantity=1,
            unit_price=Decimal('1500.00'),
            total_price=Decimal('1500.00'),
        )
        session = ConversationSession.objects.create(
            session_id='customer-service-agent-order-ref',
            user=self.user,
            assistant_mode='customer_service',
            assistant_lane='customer_service',
            context_type=ConversationSession.CONTEXT_TYPE_SUPPORT,
        )

        result = CustomerServiceAgent(session).run('Order ORD-20260509-ABCD has not arrived')

        self.assertEqual(result['metadata']['intent'], 'order_reference_matched')
        self.assertIn('ORD-20260509-ABCD', result['reply'])
        self.assertIn('delivery problem', result['reply'])

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_customer_service_dispute_flow_uses_displayed_number_and_persists_context(self, _send_mail):
        seller_one = User.objects.create_user(
            email='seller-one@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='One',
            role='seller',
            is_verified=True,
        )
        seller_two = User.objects.create_user(
            email='seller-two@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='Two',
            role='seller',
            is_verified=True,
        )
        seller_three = User.objects.create_user(
            email='seller-three@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='Three',
            role='seller',
            is_verified=True,
        )

        now = timezone.now()

        def create_order(*, order_id, order_number, seller, product_name, created_at, amount):
            order = Order.objects.create(
                id=order_id,
                customer=self.user,
                order_number=order_number,
                status='paid',
                payment_status='paid',
                total_amount=Decimal(amount),
            )
            OrderItem.objects.create(
                order=order,
                seller=seller,
                product=None,
                product_name=product_name,
                quantity=1,
                unit_price=Decimal(amount),
                total_price=Decimal(amount),
            )
            Order.objects.filter(id=order.id).update(created_at=created_at)
            order.refresh_from_db()
            return order

        first_order = create_order(
            order_id=UUID('33333333-3333-4333-8333-333333333333'),
            order_number='ORD-20260509-FIRST',
            seller=seller_one,
            product_name='First Test Item',
            created_at=now,
            amount='1000.00',
        )
        create_order(
            order_id=UUID('22222222-2222-4222-8222-222222222222'),
            order_number='ORD-20260509-SECOND',
            seller=seller_two,
            product_name='Second Test Item',
            created_at=now - timedelta(minutes=1),
            amount='2000.00',
        )
        third_order = create_order(
            order_id=UUID('11111111-1111-4111-8111-111111111111'),
            order_number='ORD-20260509-THIRD',
            seller=seller_three,
            product_name='Third Test Item',
            created_at=now - timedelta(minutes=2),
            amount='3000.00',
        )

        session = ConversationSession.objects.create(
            session_id='customer-service-dispute-regression',
            user=self.user,
            assistant_mode='customer_service',
            assistant_lane='customer_service',
            context_type=ConversationSession.CONTEXT_TYPE_SUPPORT,
        )

        first_response = CustomerServiceAgent(session).run('I have an issue with a buyer')
        self.assertIn('Recent orders:', first_response['reply'])
        self.assertIn('1. ORD-20260509-FIRST', first_response['reply'])
        self.assertIn('3. ORD-20260509-THIRD', first_response['reply'])
        self.assertNotRegex(first_response['reply'], UUID_RE)
        self.assertNotRegex(str(first_response['metadata']), UUID_RE)

        session.refresh_from_db()
        second_response = CustomerServiceAgent(session).run('3')
        self.assertIn('ORD-20260509-THIRD', second_response['reply'])
        self.assertNotIn(first_order.order_number, second_response['reply'])
        self.assertNotRegex(second_response['reply'], UUID_RE)

        session.refresh_from_db()
        flow = session.context_data[CustomerServiceAgent.FLOW_KEY]
        self.assertEqual(flow['selected_order_id'], str(third_order.id))
        self.assertEqual(flow['stage'], CustomerServiceAgent.STAGE_DISPUTE_AWAITING_DESCRIPTION)

        third_response = CustomerServiceAgent(session).run('he recorded what i did not say')
        self.assertIn('he recorded what i did not say', third_response['reply'])
        self.assertIn('What resolution do you want', third_response['reply'])
        self.assertIn('refund, replacement, or escalation to Zunto support team', third_response['reply'])
        self.assertNotRegex(third_response['reply'], UUID_RE)

        session.refresh_from_db()
        fourth_response = CustomerServiceAgent(session).run('I want this escalated to Zunto support')
        self.assertIn('I have escalated this dispute to the Zunto support team.', fourth_response['reply'])
        self.assertIn('Order: ORD-20260509-THIRD', fourth_response['reply'])
        self.assertIn('Third Test Item', fourth_response['reply'])
        self.assertIn('he recorded what i did not say', fourth_response['reply'])
        self.assertNotRegex(fourth_response['reply'], UUID_RE)
        self.assertEqual(DisputeTicket.objects.count(), 1)

    def test_uppercase_support_message_is_not_spam(self):
        message = 'I HAVE AN ISSUE WITH A BUYER'

        self.assertFalse(is_spam_message(message))

        is_valid, error, sanitized = validate_chat_request({'message': message})
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        self.assertEqual(sanitized['message'], message)
