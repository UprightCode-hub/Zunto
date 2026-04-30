from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import SellerProfile
from assistant.models import AIRecommendationFeedback, ConversationSession
from assistant.services.recommendation_evaluator import (
    HomepageRecoEvalCase,
    run_homepage_recommender_evaluation,
)
from market.models import Category, Location, Product


User = get_user_model()


class RecommendationFeedbackEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='feedback-buyer@example.com',
            password='pass1234',
            role='buyer',
        )
        self.seller = User.objects.create_user(
            email='feedback-seller@example.com',
            password='pass1234',
            role='seller',
            is_seller=True,
        )
        self.category = Category.objects.create(name='Phones')
        self.location = Location.objects.create(state='Lagos', city='Ikeja')
        SellerProfile.objects.create(
            user=self.seller,
            status=SellerProfile.STATUS_APPROVED,
            active_location=self.location,
        )
        self.product = Product.objects.create(
            seller=self.seller,
            title='Feedback iPhone 11',
            description='Feedback test phone',
            category=self.category,
            location=self.location,
            price=Decimal('180000.00'),
            quantity=2,
            condition='fair',
            status='active',
        )
        self.session = ConversationSession.objects.create(
            session_id='feedback-session-001',
            user=self.user,
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
        )

    def test_feedback_endpoint_stores_training_label(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/assistant/api/recommendations/feedback/',
            {
                'session_id': self.session.session_id,
                'product_id': str(self.product.id),
                'feedback_type': 'too_expensive',
                'prompt': 'iphone in lagos under 150k',
                'message': 'This is above my budget',
                'recommended_products': [
                    {'id': str(self.product.id), 'title': self.product.title, 'price': '180000.00'},
                ],
                'recommendation_metadata': {
                    'ranking': {'price_fit': 0.2},
                    'source': 'recommendation_results',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        feedback = AIRecommendationFeedback.objects.get()
        self.assertEqual(feedback.user_id, self.user.id)
        self.assertEqual(feedback.session_id, self.session.id)
        self.assertEqual(feedback.selected_product_id, self.product.id)
        self.assertEqual(feedback.feedback_type, 'too_expensive')
        self.assertEqual(feedback.recommended_products[0]['title'], self.product.title)
        self.assertEqual(feedback.recommendation_metadata['source'], 'recommendation_results')

    def test_feedback_endpoint_rejects_unknown_label(self):
        response = self.client.post(
            '/assistant/api/recommendations/feedback/',
            {
                'feedback_type': 'random_bad_label',
                'message': 'Nope',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(AIRecommendationFeedback.objects.exists())


class HomepageRecommendationEvaluationTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='eval-feedback-seller@example.com',
            password='pass1234',
            role='seller',
            is_seller=True,
            is_verified=True,
            is_verified_seller=True,
        )
        self.lagos = Location.objects.create(state='Lagos', city='Yaba')
        self.abuja = Location.objects.create(state='Abuja', city='Wuse')
        SellerProfile.objects.create(
            user=self.seller,
            status=SellerProfile.STATUS_APPROVED,
            is_verified_seller=True,
            verified=True,
            rating=4.7,
            total_reviews=20,
            active_location=self.lagos,
        )
        self.phones = Category.objects.create(name='Phones')
        self.shoes = Category.objects.create(name='Shoes')

        self.iphone = Product.objects.create(
            seller=self.seller,
            title='Eval iPhone 11 128GB Lagos',
            description='Affordable iPhone 11 with 128GB storage in Lagos',
            category=self.phones,
            location=self.lagos,
            price=Decimal('185000.00'),
            quantity=4,
            condition='fair',
            status='active',
            is_verified_product=True,
            search_tags=['iphone', '128gb', 'lagos'],
            attributes={'storage': '128GB'},
            attributes_verified=True,
        )
        self.expensive_iphone = Product.objects.create(
            seller=self.seller,
            title='Eval iPhone 15 Budget Trap',
            description='Expensive iPhone control for wrong-budget trap',
            category=self.phones,
            location=self.lagos,
            price=Decimal('1500000.00'),
            quantity=2,
            condition='new',
            status='active',
            search_tags=['iphone', 'premium'],
        )

    def test_eval_scores_relevance_and_budget(self):
        cases = [
            HomepageRecoEvalCase(
                name='phone_budget_eval',
                prompts=['I need iPhone in Lagos under 200k'],
                slots={
                    'category': 'Phones',
                    'product_type': 'iphone',
                    'raw_query': 'I need iPhone in Lagos under 200k',
                    'price_max': 200000,
                    'location': 'Lagos',
                },
                expected_family='iphone',
                expected_location='Lagos',
                price_max=200000,
                expected_terms=['iphone'],
            ),
            HomepageRecoEvalCase(
                name='wrong_budget_trap_eval',
                prompts=['iPhone in Lagos under 80k'],
                slots={
                    'category': 'Phones',
                    'product_type': 'iphone',
                    'raw_query': 'iPhone in Lagos under 80k',
                    'price_max': 80000,
                    'location': 'Lagos',
                },
                expected_family='iphone',
                expected_location='Lagos',
                price_max=80000,
                expect_no_result=True,
            ),
        ]

        with patch('assistant.services.recommendation_service.search_similar_products', return_value=[]):
            report = run_homepage_recommender_evaluation(cases=cases, top_k=3)

        self.assertEqual(report['total'], 2)
        self.assertEqual(report['passed'], 2)
        self.assertEqual(report['metrics']['price_adherence'], 1.0)
        self.assertEqual(report['metrics']['no_result_honesty'], 1.0)
        first = report['results'][0]['top_results'][0]
        self.assertEqual(first['title'], self.iphone.title)
        self.assertIn('price_fit', first['score_components'])
        self.assertTrue(first['match_reasons'])
