#server/reviews/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from market.models import Category, Product


User = get_user_model()


class ReviewStatsEndpointTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='review-seller@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='User',
            role='seller',
            is_verified=True,
        )
        self.buyer = User.objects.create_user(
            email='review-buyer@example.com',
            password='TestPass123!',
            first_name='Buyer',
            last_name='User',
            role='buyer',
            is_verified=True,
        )
        category = Category.objects.create(name='Books')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Book',
            description='Book desc',
            category=category,
            price=Decimal('30.00'),
            quantity=5,
            status='active',
        )

    def test_product_review_stats_empty_payload_shape(self):
        response = self.client.get(f'/api/reviews/products/{self.product.slug}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_reviews'], 0)
        self.assertIn('rating_distribution', response.data)

    def test_seller_review_stats_empty_payload_shape(self):
        response = self.client.get(f'/api/reviews/sellers/{self.seller.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_reviews'], 0)
        self.assertIn('verified_transactions', response.data)


    @override_settings(REST_FRAMEWORK={'DEFAULT_THROTTLE_RATES': {'public_review_stats': '1/min'}})
    def test_product_review_stats_throttled_for_anon(self):
        url = f'/api/reviews/products/{self.product.slug}/stats/'
        first = self.client.get(url)
        second = self.client.get(url)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
