#server/orders/tests.py
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from market.models import Category, Product
from .models import Order, OrderItem, Payment, Refund


User = get_user_model()


class SellerOrderPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email='buyer-orders@example.com',
            password='TestPass123!',
            first_name='Buyer',
            last_name='User',
            role='buyer',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            email='seller-orders@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='User',
            role='seller',
            is_verified=True,
        )
        self.admin_role_user = User.objects.create_user(
            email='admin-role-orders@example.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='Role',
            role='admin',
            is_verified=True,
        )
        category = Category.objects.create(name='Phones')
        product = Product.objects.create(
            seller=self.seller,
            title='Phone X',
            description='Phone',
            category=category,
            price=Decimal('200.00'),
            quantity=5,
            status='active',
        )
        order = Order.objects.create(
            customer=self.buyer,
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('0.00'),
            shipping_fee=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('200.00'),
            payment_method='paystack',
            shipping_address='Campus road',
            shipping_city='Lagos',
            shipping_state='Lagos',
            shipping_country='Nigeria',
            shipping_phone='08000000000',
            shipping_email='buyer-orders@example.com',
        )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.title,
            seller=self.seller,
            quantity=1,
            unit_price=Decimal('200.00'),
        )

    def test_buyer_cannot_access_seller_statistics(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get('/api/orders/seller/statistics/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_can_access_seller_statistics(self):
        self.client.force_authenticate(user=self.seller)
        response = self.client.get('/api/orders/seller/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_orders', response.data)


    def test_seller_can_update_item_status_to_shipped(self):
        item = OrderItem.objects.first()
        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(
            f'/api/orders/seller/items/{item.id}/update-status/',
            {'status': 'shipped'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.status, 'shipped')

    def test_seller_update_item_status_rejects_invalid_value(self):
        item = OrderItem.objects.first()
        self.client.force_authenticate(user=self.seller)
        response = self.client.patch(
            f'/api/orders/seller/items/{item.id}/update-status/',
            {'status': 'delivered'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid status', response.data['error'])


    def test_buyer_cannot_access_seller_orders_list(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get('/api/orders/seller/orders/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    def test_admin_role_can_access_seller_orders_list(self):
        self.client.force_authenticate(user=self.admin_role_user)
        response = self.client.get('/api/orders/seller/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    @patch('orders.views.audit_event')
    def test_admin_role_seller_orders_list_emits_audit_event(self, audit_mock):
        self.client.force_authenticate(user=self.admin_role_user)
        response = self.client.get('/api/orders/seller/orders/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'orders.admin.seller_orders_viewed')

    @patch('orders.views.audit_event')
    def test_admin_role_seller_order_detail_emits_audit_event(self, audit_mock):
        order = Order.objects.first()
        self.client.force_authenticate(user=self.admin_role_user)
        response = self.client.get(f'/api/orders/seller/orders/{order.order_number}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'orders.admin.seller_order_detail_viewed')


class AdminRefundAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email='refund-customer@example.com',
            password='TestPass123!',
            first_name='Refund',
            last_name='Customer',
            role='buyer',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            email='refund-admin@example.com',
            password='TestPass123!',
            first_name='Refund',
            last_name='Admin',
            role='admin',
            is_staff=True,
            is_verified=True,
        )
        self.role_admin = User.objects.create_user(
            email='refund-role-admin@example.com',
            password='TestPass123!',
            first_name='Role',
            last_name='Admin',
            role='admin',
            is_staff=False,
            is_verified=True,
        )

        self.order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('0.00'),
            shipping_fee=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('200.00'),
            payment_method='paystack',
            shipping_address='Campus road',
            shipping_city='Lagos',
            shipping_state='Lagos',
            shipping_country='Nigeria',
            shipping_phone='08000000000',
            shipping_email='refund-customer@example.com',
            status='processing',
            payment_status='paid',
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_method='paystack',
            amount=Decimal('200.00'),
            status='success',
            gateway_reference='ref-pay-001',
        )
        self.refund = Refund.objects.create(
            order=self.order,
            payment=self.payment,
            amount=Decimal('100.00'),
            reason='customer_request',
            description='Customer requested partial refund',
            status='pending',
        )

    @patch('orders.payment_views.audit_event')
    @patch('orders.payment_views.PaystackService.create_refund')
    def test_admin_refund_process_success_emits_audit(self, create_refund_mock, audit_mock):
        create_refund_mock.return_value = {'success': True, 'data': {'data': {'id': 'rf_12345'}}}
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(f'/api/payments/refunds/{self.refund.id}/process/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, 'processing')
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'orders.admin.refund.process_initiated')


    @patch('orders.payment_views.audit_event')
    @patch('orders.payment_views.PaystackService.create_refund')
    def test_role_admin_without_staff_can_process_refund(self, create_refund_mock, audit_mock):
        create_refund_mock.return_value = {'success': True, 'data': {'data': {'id': 'rf_role_admin'}}}
        self.client.force_authenticate(user=self.role_admin)

        response = self.client.post(f'/api/payments/refunds/{self.refund.id}/process/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, 'processing')
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'orders.admin.refund.process_initiated')

    @patch('orders.payment_views.audit_event')
    @patch('orders.payment_views.PaystackService.create_refund')
    def test_admin_refund_process_gateway_failure_emits_audit(self, create_refund_mock, audit_mock):
        create_refund_mock.return_value = {'success': False, 'error': 'gateway-down'}
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(f'/api/payments/refunds/{self.refund.id}/process/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'orders.admin.refund.process_failed')

    @patch('orders.payment_views.audit_event')
    def test_admin_refund_process_non_pending_emits_rejection_audit(self, audit_mock):
        self.refund.status = 'processing'
        self.refund.save(update_fields=['status'])
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(f'/api/payments/refunds/{self.refund.id}/process/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'orders.admin.refund.process_rejected')


class PaymentWebhookRefundFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email='webhook-customer@example.com',
            password='TestPass123!',
            role='buyer',
            is_verified=True,
        )
        self.order = Order.objects.create(
            customer=self.customer,
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('0.00'),
            shipping_fee=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('200.00'),
            payment_method='paystack',
            shipping_address='Campus road',
            shipping_city='Lagos',
            shipping_state='Lagos',
            shipping_country='Nigeria',
            shipping_phone='08000000000',
            shipping_email='webhook-customer@example.com',
            status='processing',
            payment_status='paid',
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_method='paystack',
            amount=Decimal('200.00'),
            status='success',
            gateway_reference='ref-pay-webhook-1',
        )

    @patch('orders.payment_views.PaystackService.verify_webhook_signature', return_value=True)
    def test_refund_processed_webhook_updates_processing_refund(self, _verify):
        refund = Refund.objects.create(
            order=self.order,
            payment=self.payment,
            amount=Decimal('100.00'),
            reason='customer_request',
            description='Refund in progress',
            status='processing',
        )
        payload = {
            'event': 'refund.processed',
            'data': {
                'transaction_reference': self.payment.gateway_reference,
                'id': 'rf_done_1',
            },
        }
        response = self.client.post(
            '/api/payments/webhook/paystack/',
            data=payload,
            format='json',
            HTTP_X_PAYSTACK_SIGNATURE='valid',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refund.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(refund.status, 'completed')
        self.assertEqual(self.order.status, 'refunded')
        self.assertEqual(self.order.payment_status, 'refunded')

    @patch('orders.payment_views.PaystackService.verify_webhook_signature', return_value=True)
    def test_refund_failed_webhook_updates_processing_refund(self, _verify):
        refund = Refund.objects.create(
            order=self.order,
            payment=self.payment,
            amount=Decimal('100.00'),
            reason='customer_request',
            description='Refund in progress',
            status='processing',
        )
        payload = {
            'event': 'refund.failed',
            'data': {'transaction_reference': self.payment.gateway_reference},
        }
        response = self.client.post(
            '/api/payments/webhook/paystack/',
            data=payload,
            format='json',
            HTTP_X_PAYSTACK_SIGNATURE='valid',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refund.refresh_from_db()
        self.assertEqual(refund.status, 'failed')


class InitializePaymentSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email='initpay-buyer@example.com',
            password='TestPass123!',
            role='buyer',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            email='initpay-seller@example.com',
            password='TestPass123!',
            role='seller',
            is_verified=True,
            seller_commerce_mode='managed',
        )
        category = Category.objects.create(name='InitPay Phones')
        product = Product.objects.create(
            seller=self.seller,
            title='Phone InitPay',
            description='Phone',
            category=category,
            price=Decimal('200.00'),
            quantity=5,
            status='active',
        )
        self.order = Order.objects.create(
            customer=self.buyer,
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('0.00'),
            shipping_fee=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            total_amount=Decimal('200.00'),
            payment_method='paystack',
            shipping_address='Campus road',
            shipping_city='Lagos',
            shipping_state='Lagos',
            shipping_country='Nigeria',
            shipping_phone='08000000000',
            shipping_email='initpay-buyer@example.com',
            status='pending',
            payment_status='unpaid',
        )
        OrderItem.objects.create(
            order=self.order,
            product=product,
            product_name=product.title,
            seller=self.seller,
            quantity=1,
            unit_price=Decimal('200.00'),
        )

    @patch('orders.payment_views.PaystackService.initialize_transaction')
    def test_rejects_external_callback_host(self, init_tx_mock):
        init_tx_mock.return_value = {'success': True, 'data': {'data': {'authorization_url': 'https://pay', 'access_code': 'code'}}}
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            f'/api/payments/initialize/{self.order.order_number}/',
            {'callback_url': 'https://evil.example/cb'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Callback host is not allowed', response.data['error'])


    @patch('orders.payment_views.PaystackService.initialize_transaction')
    @override_settings(PAYMENT_ALLOWED_CALLBACK_HOSTS=['trusted.example'])
    def test_allows_configured_callback_host_without_port_match(self, init_tx_mock):
        init_tx_mock.return_value = {'success': True, 'data': {'data': {'authorization_url': 'https://pay', 'access_code': 'code'}}}
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            f'/api/payments/initialize/{self.order.order_number}/',
            {'callback_url': 'https://trusted.example:8443/payment/verify/'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('orders.payment_views.PaystackService.initialize_transaction')
    @override_settings(DEBUG=False)
    def test_rejects_http_callback_when_debug_false(self, init_tx_mock):
        init_tx_mock.return_value = {'success': True, 'data': {'data': {'authorization_url': 'https://pay', 'access_code': 'code'}}}
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            f'/api/payments/initialize/{self.order.order_number}/',
            {'callback_url': 'http://testserver/payment/verify/'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('must use HTTPS', response.data['error'])

    @patch('orders.payment_views.PaystackService.initialize_transaction')
    def test_allows_same_host_callback(self, init_tx_mock):
        init_tx_mock.return_value = {'success': True, 'data': {'data': {'authorization_url': 'https://pay', 'access_code': 'code'}}}
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            f'/api/payments/initialize/{self.order.order_number}/',
            {'callback_url': 'http://testserver/payment/verify/'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
