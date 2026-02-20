#server/market/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Category, Product, ProductReport


User = get_user_model()


class SellerPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email='buyer-market@example.com',
            password='TestPass123!',
            first_name='Buyer',
            last_name='User',
            role='buyer',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            email='seller-market@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='User',
            role='seller',
            is_verified=True,
        )
        self.admin_role_user = User.objects.create_user(
            email='admin-role-market@example.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='Role',
            role='admin',
            is_verified=True,
        )
        self.category = Category.objects.create(name='Accessories')

    def test_buyer_cannot_create_product_listing(self):
        self.client.force_authenticate(user=self.buyer)
        payload = {
            'title': 'Restricted listing',
            'description': 'Only sellers should create this',
            'listing_type': 'product',
            'price': '15.00',
            'quantity': 2,
            'condition': 'new',
            'status': 'active',
            'category': str(self.category.id),
        }
        response = self.client.post('/api/market/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_can_create_product_listing(self):
        self.client.force_authenticate(user=self.seller)
        payload = {
            'title': 'Seller listing',
            'description': 'Valid seller listing',
            'listing_type': 'product',
            'price': '25.00',
            'quantity': 3,
            'condition': 'new',
            'status': 'active',
            'category': str(self.category.id),
        }
        response = self.client.post('/api/market/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(title='Seller listing', seller=self.seller).exists())


    def test_admin_role_can_create_product_listing(self):
        self.client.force_authenticate(user=self.admin_role_user)
        payload = {
            'title': 'Admin created listing',
            'description': 'Admin override listing',
            'listing_type': 'product',
            'price': '45.00',
            'quantity': 1,
            'condition': 'new',
            'status': 'active',
            'category': str(self.category.id),
        }
        response = self.client.post('/api/market/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_product_view_deduplicates_within_window(self):
        product = Product.objects.create(
            seller=self.seller,
            title='View-tracked product',
            description='View dedupe check',
            listing_type='product',
            price=Decimal('55.00'),
            quantity=2,
            condition='new',
            status='active',
            category=self.category,
        )

        self.client.force_authenticate(user=self.buyer)
        detail_url = f'/api/market/products/{product.slug}/'

        first = self.client.get(detail_url)
        second = self.client.get(detail_url)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)

        product.refresh_from_db()
        self.assertEqual(product.views_count, 1)


    def test_favorite_toggle_updates_counter_atomically(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Favorite tracked product',
            description='Favorite counter check',
            listing_type='product',
            price=Decimal('35.00'),
            quantity=2,
            condition='new',
            status='active',
            category=self.category,
        )

        self.client.force_authenticate(user=self.buyer)
        toggle_url = f'/api/market/products/{product.slug}/favorite/'

        first = self.client.post(toggle_url)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data.get('favorites_count'), 1)

        second = self.client.post(toggle_url)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data.get('favorites_count'), 0)

        product.refresh_from_db()
        self.assertEqual(product.favorites_count, 0)


    def test_product_stats_cache_invalidated_after_favorite_toggle(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Stats cache product',
            description='Stats invalidation check',
            listing_type='product',
            price=Decimal('65.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )

        self.client.force_authenticate(user=self.seller)
        stats_url = f'/api/market/products/{product.slug}/stats/'
        initial = self.client.get(stats_url)
        self.assertEqual(initial.status_code, status.HTTP_200_OK)
        self.assertEqual(initial.data.get('favorites_count'), 0)

        self.client.force_authenticate(user=self.buyer)
        toggle_url = f'/api/market/products/{product.slug}/favorite/'
        toggle = self.client.post(toggle_url)
        self.assertEqual(toggle.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.seller)
        refreshed = self.client.get(stats_url)
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertEqual(refreshed.data.get('favorites_count'), 1)


    def test_admin_role_can_moderate_product_report(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Reported product',
            description='Needs moderation',
            listing_type='product',
            price=Decimal('80.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )
        report = ProductReport.objects.create(
            product=product,
            reporter=self.buyer,
            reason='spam',
            description='Spam listing',
            status='pending',
        )

        self.client.force_authenticate(user=self.admin_role_user)
        response = self.client.patch(
            f'/api/market/reports/moderation/{report.id}/',
            {'status': 'reviewing', 'admin_notes': 'Investigating'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, 'reviewing')
        self.assertEqual(report.admin_notes, 'Investigating')
        self.assertEqual(report.moderated_by, self.admin_role_user)

    def test_buyer_cannot_access_report_moderation(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get('/api/market/reports/moderation/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_report_status_transition_is_rejected(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Report transition product',
            description='Transition guard',
            listing_type='product',
            price=Decimal('70.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )
        report = ProductReport.objects.create(
            product=product,
            reporter=self.buyer,
            reason='fraud',
            description='Suspicious listing',
            status='pending',
        )

        self.client.force_authenticate(user=self.admin_role_user)
        first = self.client.patch(
            f'/api/market/reports/moderation/{report.id}/',
            {'status': 'resolved'},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.patch(
            f'/api/market/reports/moderation/{report.id}/',
            {'status': 'reviewing'},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
