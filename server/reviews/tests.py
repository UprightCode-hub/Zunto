#server/reviews/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from market.models import Category, Product
from reviews.models import ReviewFlag, ProductReview


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


class ReviewFlagModerationTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='flag-seller@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='User',
            role='seller',
            is_verified=True,
        )
        self.buyer = User.objects.create_user(
            email='flag-buyer@example.com',
            password='TestPass123!',
            first_name='Buyer',
            last_name='User',
            role='buyer',
            is_verified=True,
        )
        self.admin = User.objects.create_user(
            email='flag-admin@example.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_verified=True,
        )

        category = Category.objects.create(name='Electronics')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Camera',
            description='Camera desc',
            category=category,
            price=Decimal('250.00'),
            quantity=4,
            status='active',
        )
        self.review = ProductReview.objects.create(
            product=self.product,
            reviewer=self.buyer,
            rating=4,
            title='Solid',
            comment='Nice quality',
            is_approved=True,
            is_verified_purchase=False,
        )
        self.flag = ReviewFlag.objects.create(
            product_review=self.review,
            flagger=self.buyer,
            reason='spam',
            description='Looks spammy',
        )

    def test_non_admin_cannot_access_review_flag_moderation_queue(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get('/api/reviews/reviews/flags/moderation/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('reviews.views.audit_event')
    def test_admin_can_view_review_flag_moderation_queue_and_emits_audit(self, audit_mock):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/reviews/reviews/flags/moderation/?status=pending')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertTrue(any(item['id'] == str(self.flag.id) for item in response.data))
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'reviews.flag.moderation_queue_viewed')

    def test_admin_can_moderate_review_flag(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/reviews/reviews/flags/moderation/{self.flag.id}/',
            {'status': 'reviewing', 'admin_notes': 'Investigating now'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.flag.refresh_from_db()
        self.assertEqual(self.flag.status, 'reviewing')
        self.assertEqual(self.flag.admin_notes, 'Investigating now')
        self.assertIsNone(self.flag.resolved_at)

    def test_invalid_review_flag_transition_is_rejected(self):
        self.flag.status = 'resolved'
        self.flag.save(update_fields=['status'])

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/reviews/reviews/flags/moderation/{self.flag.id}/',
            {'status': 'reviewing'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('reviews.views.audit_event')
    def test_review_flag_moderation_emits_audit_event(self, audit_mock):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/reviews/reviews/flags/moderation/{self.flag.id}/',
            {'status': 'resolved', 'admin_notes': 'Resolved as valid flag'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'reviews.flag.moderated')
