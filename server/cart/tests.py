#server/cart/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Cart, CartAbandonment, CartEvent
from .scoring import calculate_all_scores, calculate_composite_score


User = get_user_model()


class CartApiPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_anonymous_cart_api_requires_authentication(self):
        item_id = '00000000-0000-0000-0000-000000000000'
        requests = [
            ('get', '/api/cart/', None),
            ('post', '/api/cart/add/', {}),
            ('patch', f'/api/cart/update/{item_id}/', {'quantity': 1}),
            ('delete', f'/api/cart/remove/{item_id}/', None),
            ('post', '/api/cart/clear/', {}),
        ]

        for method, endpoint, payload in requests:
            with self.subTest(method=method, endpoint=endpoint):
                client_method = getattr(self.client, method)
                if payload is None:
                    response = client_method(endpoint)
                else:
                    response = client_method(endpoint, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CartScoringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='scoring@example.com',
            password='testpass123',
        )

    def test_calculate_all_scores_returns_expected_keys(self):
        scores = calculate_all_scores(self.user)

        self.assertSetEqual(
            set(scores.keys()),
            {
                'abandonment_score',
                'value_score',
                'conversion_score',
                'hesitation_score',
                'price_sensitivity_score',
                'composite_score',
            },
        )

    def test_default_scores_are_within_bounds_for_new_user(self):
        scores = calculate_all_scores(self.user)
        for value in scores.values():
            self.assertGreaterEqual(value, Decimal('0.00'))
            self.assertLessEqual(value, Decimal('100.00'))

    def test_composite_score_is_clamped_when_abandonments_exceed_cart_count(self):
        cart = Cart.objects.create(user=self.user)
        for _ in range(4):
            CartAbandonment.objects.create(
                cart=cart,
                user=self.user,
                total_items=1,
                total_value=Decimal('10000.00'),
                recovered=False,
            )

        CartEvent.objects.create(
            event_type='cart_item_added',
            user=self.user,
            cart_id=cart.id,
            data={'quantity': 1},
        )

        score = calculate_composite_score(self.user)
        self.assertGreaterEqual(score, Decimal('0.00'))
        self.assertLessEqual(score, Decimal('100.00'))
