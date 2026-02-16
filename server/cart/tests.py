#server/cart/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Cart, CartAbandonment, CartEvent
from .scoring import calculate_all_scores, calculate_composite_score


User = get_user_model()


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
