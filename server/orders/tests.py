#server/orders/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from market.models import Category, Product
from .models import Order, OrderItem


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
