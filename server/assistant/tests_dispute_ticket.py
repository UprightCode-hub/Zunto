#server/assistant/tests_dispute_ticket.py
from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from assistant.models import DisputeTicket, DisputeTicketCommunication, DisputeAuditLog, Report, ConversationSession, ConversationLog
from assistant.services.dispute_ai_service import DisputeAIService
from assistant.services.dispute_oversight_metrics import DisputeOversightMetricsService
from market.models import Category, Product
from orders.models import Order, OrderItem, Payment, Refund

User = get_user_model()


class DisputeTicketAPITests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email='buyer@example.com',
            password='BuyerPass123!',
            first_name='Buyer',
            last_name='One',
            role='buyer',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='SellerPass123!',
            first_name='Seller',
            last_name='One',
            role='seller',
            is_verified=True,
            seller_commerce_mode='managed',
        )
        self.staff = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='One',
            role='admin',
            is_verified=True,
            is_staff=True,
        )

        category = Category.objects.create(name='Phones')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Sample Product',
            description='Sample description',
            category=category,
            price=1000,
            quantity=1,
            status='active',
        )
        self.order = Order.objects.create(
            order_number=f'ORD-TEST-{str(uuid4())[:6]}',
            customer=self.buyer,
            status='paid',
            payment_method='paystack',
            payment_status='paid',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            seller=self.seller,
            product_name=self.product.title,
            quantity=1,
            unit_price=1000,
            total_price=1000,
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_method='paystack',
            amount=1000,
            status='success',
            gateway_reference=f'pay-{str(uuid4())[:8]}',
        )
        self.session = ConversationSession.objects.create(
            session_id='sess-ticket-tests',
            user=self.buyer,
            assistant_mode='customer_service',
            assistant_lane='customer_service',
            current_state='dispute_mode',
            context={'history': []},
        )

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_create_dispute_ticket_creates_ticket_and_communications(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Item not delivered as promised.',
                'desired_resolution': 'refund',
                'evidence': ['https://cdn.example.com/evidence1.png'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['ticket_id'].startswith('TICKET-'))

        ticket = DisputeTicket.objects.get(ticket_id=response.data['ticket_id'])
        self.assertEqual(ticket.buyer_id, self.buyer.id)
        self.assertEqual(ticket.seller_id, self.seller.id)
        self.assertEqual(ticket.seller_type, DisputeTicket.SELLER_TYPE_VERIFIED)
        self.assertEqual(ticket.status, DisputeTicket.STATUS_OPEN)

        comms = DisputeTicketCommunication.objects.filter(ticket=ticket)
        self.assertGreaterEqual(comms.count(), 4)  # buyer create + buyer email + seller email + admin alert


    @patch('assistant.services.dispute_ai_service.LocalModelAdapter.get_instance')
    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_ticket_creation_triggers_ai_evaluation(self, _send_mail, get_instance_mock):
        llm = get_instance_mock.return_value
        llm.is_available.return_value = True
        llm.generate.return_value = {
            'response': '{"recommended_decision":"approved","confidence_score":0.8,"risk_score":0.6,"reasoning_summary":"structured ai summary","policy_flags":["delivery_claim"]}'
        }

        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Item not delivered as promised.',
                'desired_resolution': 'refund',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = DisputeTicket.objects.get(ticket_id=response.data['ticket_id'])
        self.assertIsNotNone(ticket.ai_evaluated_at)
        self.assertEqual(ticket.ai_recommended_decision, 'approved')
        self.assertTrue(
            ticket.communications.filter(message_type=DisputeAIService.MESSAGE_TYPE_AI_RECOMMENDATION).exists()
        )

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_create_dispute_ticket_denies_non_owner_order(self, _send_mail):
        other_buyer = User.objects.create_user(
            email='other-buyer@example.com',
            password='BuyerPass123!',
            first_name='Other',
            last_name='Buyer',
            role='buyer',
            is_verified=True,
        )
        self.client.force_authenticate(other_buyer)

        response = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Not mine.',
                'desired_resolution': 'refund',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('buyer does not own', response.data['error'])

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_create_report_with_ids_creates_single_linked_ticket(self, _send_mail):
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            '/assistant/api/report/',
            {
                'report_type': 'dispute',
                'description': 'Package arrived broken',
                'category': 'damaged_item',
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'desired_resolution': 'replacement',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.filter(report_type='dispute').count(), 1)
        self.assertEqual(DisputeTicket.objects.count(), 1)

        ticket = DisputeTicket.objects.first()
        self.assertEqual(response.data['ticket_id'], ticket.ticket_id)
        self.assertIsNotNone(ticket.legacy_report_id)


    @patch('assistant.views.DisputeAIService.evaluate_ticket', return_value=True)
    @patch('assistant.views.validate_dispute_media_task.delay', return_value=None)
    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_evidence_upload_triggers_ai_reevaluation_for_linked_ticket(self, _send_mail, _delay, evaluate_mock):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/report/',
            {
                'report_type': 'dispute',
                'description': 'Packaging issue',
                'category': 'damaged_item',
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'desired_resolution': 'replacement',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket = DisputeTicket.objects.get(ticket_id=create_resp.data['ticket_id'])

        from django.core.files.uploadedfile import SimpleUploadedFile
        evidence = SimpleUploadedFile('proof.png', b'fakepngdata', content_type='image/png')

        upload_resp = self.client.post(
            f'/assistant/api/report/{ticket.legacy_report_id}/evidence/',
            {'file': evidence, 'media_type': 'image'},
            format='multipart',
        )
        self.assertEqual(upload_resp.status_code, status.HTTP_202_ACCEPTED)
        evaluate_mock.assert_called_once_with(ticket=ticket, trigger='evidence_uploaded')
        self.assertTrue(
            ticket.communications.filter(message_type='evidence_uploaded').exists()
        )

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_admin_decision_updates_existing_ticket_without_duplicates_and_logs_conversation(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Still waiting for product',
                'desired_resolution': 'refund',
                'session_id': self.session.session_id,
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket_id = create_resp.data['ticket_id']
        self.assertEqual(DisputeTicket.objects.count(), 1)

        self.client.force_authenticate(self.staff)
        decision_resp = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'RESOLVED_DENIED',
                'admin_decision': 'Claim denied after reviewing seller proof.',
                'admin_decision_reason': 'Seller submitted signed delivery evidence.',
            },
            format='json',
        )

        self.assertEqual(decision_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(DisputeTicket.objects.count(), 1)

        ticket = DisputeTicket.objects.get(ticket_id=ticket_id)
        self.assertEqual(ticket.status, DisputeTicket.STATUS_RESOLVED_DENIED)
        self.assertEqual(ticket.admin_user_id, self.staff.id)
        self.assertTrue(
            ticket.communications.filter(
                message_type='admin_decision',
                sender_role=DisputeTicketCommunication.SENDER_ADMIN,
            ).exists()
        )

        self.assertTrue(
            ConversationLog.objects.filter(
                anonymous_session_id=self.session.session_id,
                explanation='Source: admin_decision',
            ).exists()
        )

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_admin_approve_executes_refund_and_blocks_double_execution(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Item never arrived',
                'desired_resolution': 'refund',
                'session_id': self.session.session_id,
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket_id = create_resp.data['ticket_id']

        ticket = DisputeTicket.objects.get(ticket_id=ticket_id)
        self.assertEqual(ticket.escrow_state, DisputeTicket.ESCROW_FROZEN)

        self.client.force_authenticate(self.staff)
        decision_resp = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'RESOLVED_APPROVED',
                'admin_decision': 'Refund approved after review.',
                'admin_decision_reason': 'Seller missed response window.',
            },
            format='json',
        )
        self.assertEqual(decision_resp.status_code, status.HTTP_200_OK)

        ticket.refresh_from_db()
        self.order.refresh_from_db()
        self.payment.refresh_from_db()

        self.assertEqual(ticket.escrow_state, DisputeTicket.ESCROW_RELEASED_TO_BUYER)
        self.assertEqual(self.order.payment_status, 'refunded')
        self.assertEqual(self.order.status, 'refunded')
        self.assertEqual(self.payment.status, 'refunded')
        self.assertEqual(Refund.objects.filter(order=self.order).count(), 1)

        second_resp = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'RESOLVED_DENIED',
                'admin_decision': 'Reversing decision.',
                'admin_decision_reason': 'Should not be allowed.',
            },
            format='json',
        )
        self.assertEqual(second_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already decided', second_resp.data['error'])

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_admin_denied_releases_to_seller_and_creates_no_refund(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'quality_issue',
                'description': 'Buyer claim rejected by evidence',
                'desired_resolution': 'replacement',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket_id = create_resp.data['ticket_id']

        self.client.force_authenticate(self.staff)
        decision_resp = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'RESOLVED_DENIED',
                'admin_decision': 'Seller proof accepted.',
                'admin_decision_reason': 'Delivery evidence verified.',
            },
            format='json',
        )
        self.assertEqual(decision_resp.status_code, status.HTTP_200_OK)

        ticket = DisputeTicket.objects.get(ticket_id=ticket_id)
        self.assertEqual(ticket.escrow_state, DisputeTicket.ESCROW_RELEASED_TO_SELLER)
        self.assertEqual(Refund.objects.filter(order=self.order).count(), 0)

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_invalid_transition_blocks_closing_open_ticket(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Still pending',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket_id = create_resp.data['ticket_id']

        self.client.force_authenticate(self.staff)
        close_resp = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'CLOSED',
                'admin_decision': 'Closing directly',
            },
            format='json',
        )
        self.assertEqual(close_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Illegal status transition', close_resp.data['error'])


    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_non_staff_cannot_submit_admin_decision(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Need admin review',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        ticket_id = create_resp.data['ticket_id']
        decision_resp = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'RESOLVED_APPROVED',
                'admin_decision': 'Unauthorized decision',
            },
            format='json',
        )
        self.assertEqual(decision_resp.status_code, status.HTTP_403_FORBIDDEN)

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_duplicate_admin_payload_rejected_without_reexecution(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Need refund',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket_id = create_resp.data['ticket_id']

        self.client.force_authenticate(self.staff)
        payload = {
            'status': 'RESOLVED_APPROVED',
            'admin_decision': 'Approved after review',
            'admin_decision_reason': 'Policy aligned',
        }
        first = self.client.post(f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/', payload, format='json')
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/', payload, format='json')
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Duplicate admin decision payload', second.data['error'])

        ticket = DisputeTicket.objects.get(ticket_id=ticket_id)
        self.assertTrue(ticket.escrow_execution_locked)
        self.assertIsNotNone(ticket.escrow_executed_at)
        self.assertEqual(Refund.objects.filter(order=self.order).count(), 1)

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_escrow_execution_requires_frozen_state(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Not delivered',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket = DisputeTicket.objects.get(ticket_id=create_resp.data['ticket_id'])
        ticket.escrow_state = DisputeTicket.ESCROW_NOT_APPLICABLE
        ticket.save(update_fields=['escrow_state'])

        self.client.force_authenticate(self.staff)
        decision_resp = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket.ticket_id}/admin-decision/',
            {
                'status': 'RESOLVED_APPROVED',
                'admin_decision': 'Attempt execution',
            },
            format='json',
        )
        self.assertEqual(decision_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Escrow must be frozen', decision_resp.data['error'])


    @patch('assistant.services.dispute_ai_service.LocalModelAdapter.get_instance')
    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_high_risk_ai_score_auto_escalates_ticket(self, _send_mail, get_instance_mock):
        llm = get_instance_mock.return_value
        llm.is_available.return_value = True
        llm.generate.return_value = {
            'response': '{"recommended_decision":"denied","confidence_score":0.9,"risk_score":0.96,"reasoning_summary":"high fraud risk","policy_flags":["fraud_signal"]}'
        }

        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'fraud_issue',
                'description': 'Possible fraud pattern',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ticket = DisputeTicket.objects.get(ticket_id=response.data['ticket_id'])
        self.assertEqual(ticket.status, DisputeTicket.STATUS_ESCALATED)
        self.assertTrue(ticket.audit_logs.filter(action_type=DisputeAuditLog.ACTION_ESCALATION_TRIGGER).exists())

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_high_value_dispute_requires_senior_review_before_resolution(self, _send_mail):
        self.order.total_amount = 300000
        self.order.save(update_fields=['total_amount'])

        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Need review',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket_id = create_resp.data['ticket_id']

        self.client.force_authenticate(self.staff)
        under_review = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'UNDER_REVIEW',
                'admin_decision': 'Initial review',
            },
            format='json',
        )
        self.assertEqual(under_review.status_code, status.HTTP_200_OK)

        denied_direct = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {
                'status': 'RESOLVED_DENIED',
                'admin_decision': 'Direct deny',
            },
            format='json',
        )
        self.assertEqual(denied_direct.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('High-value disputes must transition through UNDER_SENIOR_REVIEW', denied_direct.data['error'])

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_escalated_path_cannot_bypass_under_senior_review(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Need hierarchy enforcement',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket_id = create_resp.data['ticket_id']

        self.client.force_authenticate(self.staff)
        self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {'status': 'UNDER_REVIEW', 'admin_decision': 'Move under review'},
            format='json',
        )
        self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {'status': 'ESCALATED', 'admin_decision': 'Escalate'},
            format='json',
        )
        bypass = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket_id}/admin-decision/',
            {'status': 'RESOLVED_APPROVED', 'admin_decision': 'Bypass senior review'},
            format='json',
        )
        self.assertEqual(bypass.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Illegal status transition', bypass.data['error'])

    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_ai_admin_agreement_and_override_flag_are_recorded(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Mismatch test',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket = DisputeTicket.objects.get(ticket_id=create_resp.data['ticket_id'])
        ticket.ai_recommended_decision = 'approved'
        ticket.ai_confidence_score = 0.95
        ticket.save(update_fields=['ai_recommended_decision', 'ai_confidence_score'])

        self.client.force_authenticate(self.staff)
        under_review = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket.ticket_id}/admin-decision/',
            {'status': 'UNDER_REVIEW', 'admin_decision': 'review'},
            format='json',
        )
        self.assertEqual(under_review.status_code, status.HTTP_200_OK)

        final = self.client.post(
            f'/assistant/api/dispute-tickets/{ticket.ticket_id}/admin-decision/',
            {'status': 'RESOLVED_DENIED', 'admin_decision': 'admin denied'},
            format='json',
        )
        self.assertEqual(final.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertFalse(ticket.ai_admin_agreement)
        self.assertTrue(ticket.ai_override_flag)
        self.assertIsNotNone(ticket.ai_evaluated_against_admin_at)


    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_admin_decision_creates_structured_audit_logs(self, _send_mail):
        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'Audit coverage',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket = DisputeTicket.objects.get(ticket_id=create_resp.data['ticket_id'])

        self.client.force_authenticate(self.staff)
        self.client.post(
            f'/assistant/api/dispute-tickets/{ticket.ticket_id}/admin-decision/',
            {'status': 'UNDER_REVIEW', 'admin_decision': 'start review'},
            format='json',
        )
        self.client.post(
            f'/assistant/api/dispute-tickets/{ticket.ticket_id}/admin-decision/',
            {'status': 'RESOLVED_APPROVED', 'admin_decision': 'approved'},
            format='json',
        )

        action_types = set(ticket.audit_logs.values_list('action_type', flat=True))
        self.assertIn(DisputeAuditLog.ACTION_STATUS_CHANGE, action_types)
        self.assertIn(DisputeAuditLog.ACTION_ADMIN_DECISION, action_types)
        self.assertIn(DisputeAuditLog.ACTION_ESCROW_EXECUTION, action_types)

    @patch('assistant.services.dispute_ai_service.LocalModelAdapter.get_instance')
    @patch('assistant.services.dispute_ticket_service.send_mail', return_value=1)
    def test_ai_recommendation_creates_audit_entry(self, _send_mail, get_instance_mock):
        llm = get_instance_mock.return_value
        llm.is_available.return_value = True
        llm.generate.return_value = {
            'response': '{"recommended_decision":"approved","confidence_score":0.9,"risk_score":0.2,"reasoning_summary":"ok","policy_flags":["policy_ok"]}'
        }

        self.client.force_authenticate(self.buyer)
        create_resp = self.client.post(
            '/assistant/api/dispute-tickets/',
            {
                'order_id': str(self.order.id),
                'product_id': str(self.product.id),
                'dispute_category': 'delivery_issue',
                'description': 'AI audit',
                'desired_resolution': 'refund',
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        ticket = DisputeTicket.objects.get(ticket_id=create_resp.data['ticket_id'])
        self.assertTrue(ticket.audit_logs.filter(action_type=DisputeAuditLog.ACTION_AI_RECOMMENDATION).exists())

    def test_admin_oversight_endpoints_staff_only_and_read_only(self):
        self.client.force_authenticate(self.buyer)
        for path in [
            '/assistant/api/admin/disputes/oversight-summary/',
            '/assistant/api/admin/disputes/escalated/',
            '/assistant/api/admin/disputes/high-risk/',
            '/assistant/api/admin/disputes/threshold-config/',
        ]:
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.staff)
        summary = self.client.get('/assistant/api/admin/disputes/oversight-summary/')
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertIn('ai_accuracy_rate_pct', summary.data)

        escalated = self.client.get('/assistant/api/admin/disputes/escalated/')
        self.assertEqual(escalated.status_code, status.HTTP_200_OK)
        self.assertIn('results', escalated.data)

        high_risk = self.client.get('/assistant/api/admin/disputes/high-risk/')
        self.assertEqual(high_risk.status_code, status.HTTP_200_OK)
        self.assertIn('threshold', high_risk.data)

        thresholds = self.client.get('/assistant/api/admin/disputes/threshold-config/')
        self.assertEqual(thresholds.status_code, status.HTTP_200_OK)
        self.assertIn('HIGH_RISK_THRESHOLD', thresholds.data)

        post_resp = self.client.post('/assistant/api/admin/disputes/oversight-summary/', {}, format='json')
        self.assertEqual(post_resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class DisputeAIServiceTests(APITestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email='buyer-ai@example.com',
            password='BuyerPass123!',
            role='buyer',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            email='seller-ai@example.com',
            password='SellerPass123!',
            role='seller',
            is_verified=True,
            seller_commerce_mode='managed',
        )
        category = Category.objects.create(name='AI Phones')
        self.product = Product.objects.create(
            seller=self.seller,
            title='AI Product',
            description='AI description',
            category=category,
            price=1000,
            quantity=1,
            status='active',
        )
        self.order = Order.objects.create(
            order_number=f'ORD-AI-{str(uuid4())[:6]}',
            customer=self.buyer,
            status='paid',
            payment_method='paystack',
            payment_status='paid',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            seller=self.seller,
            product_name=self.product.title,
            quantity=1,
            unit_price=1000,
            total_price=1000,
        )
        Payment.objects.create(
            order=self.order,
            payment_method='paystack',
            amount=1000,
            status='success',
            gateway_reference=f'pay-ai-{str(uuid4())[:8]}',
        )

        self.ticket = DisputeTicket.objects.create(
            ticket_id=DisputeTicket.generate_ticket_id(),
            buyer=self.buyer,
            seller=self.seller,
            seller_type=DisputeTicket.SELLER_TYPE_VERIFIED,
            order=self.order,
            product=self.product,
            dispute_category='delivery_issue',
            description='Item not delivered',
            desired_resolution='refund',
            status=DisputeTicket.STATUS_OPEN,
            escrow_state=DisputeTicket.ESCROW_FROZEN,
        )
        DisputeTicketCommunication.objects.create(
            ticket=self.ticket,
            sender_role=DisputeTicketCommunication.SENDER_BUYER,
            channel=DisputeTicketCommunication.CHANNEL_CHAT,
            message_type='ticket_created',
            body='Item not delivered',
            meta={},
        )

    @patch('assistant.services.dispute_ai_service.LocalModelAdapter.get_instance')
    def test_ai_output_is_stored_and_logged_without_status_or_escrow_mutation(self, get_instance_mock):
        llm = get_instance_mock.return_value
        llm.is_available.return_value = True
        llm.generate.return_value = {
            'response': '{"recommended_decision":"approved","confidence_score":0.82,"risk_score":0.64,"reasoning_summary":"policy aligned","policy_flags":["delivery_claim","evidence_present"]}'
        }

        old_status = self.ticket.status
        old_escrow = self.ticket.escrow_state
        changed = DisputeAIService.evaluate_ticket(ticket=self.ticket, trigger='ticket_created')

        self.assertTrue(changed)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ai_recommended_decision, 'approved')
        self.assertEqual(self.ticket.status, old_status)
        self.assertEqual(self.ticket.escrow_state, old_escrow)
        self.assertIsNotNone(self.ticket.ai_evaluated_at)
        self.assertTrue(
            DisputeTicketCommunication.objects.filter(
                ticket=self.ticket,
                sender_role=DisputeTicketCommunication.SENDER_AI,
                message_type=DisputeAIService.MESSAGE_TYPE_AI_RECOMMENDATION,
            ).exists()
        )

    @patch('assistant.services.dispute_ai_service.LocalModelAdapter.get_instance')
    def test_ai_rerun_idempotent_without_new_inputs(self, get_instance_mock):
        llm = get_instance_mock.return_value
        llm.is_available.return_value = True
        llm.generate.return_value = {
            'response': '{"recommended_decision":"denied","confidence_score":0.61,"risk_score":0.41,"reasoning_summary":"insufficient evidence","policy_flags":["limited_evidence"]}'
        }

        first_changed = DisputeAIService.evaluate_ticket(ticket=self.ticket, trigger='ticket_created')
        second_changed = DisputeAIService.evaluate_ticket(ticket=self.ticket, trigger='ticket_created')

        self.assertTrue(first_changed)
        self.assertFalse(second_changed)
        self.assertEqual(
            DisputeTicketCommunication.objects.filter(
                ticket=self.ticket,
                message_type=DisputeAIService.MESSAGE_TYPE_AI_RECOMMENDATION,
            ).count(),
            1,
        )


class DisputeOversightMetricsTests(APITestCase):
    def test_metrics_summary_structure(self):
        summary = DisputeOversightMetricsService.summary()
        self.assertIn('total_tickets', summary)
        self.assertIn('ai_accuracy_rate_pct', summary)
        self.assertIn('admin_override_rate_pct', summary)
        self.assertIn('high_risk_dispute_pct', summary)
        self.assertIn('escalation_rate_pct', summary)
        self.assertIn('senior_review_rate_pct', summary)
