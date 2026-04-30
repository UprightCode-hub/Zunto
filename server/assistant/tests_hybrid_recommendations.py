from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import SellerProfile
from assistant.models import ConversationSession
from assistant.services.recommendation_service import RecommendationService
from market.models import Category, Location, Product


User = get_user_model()


class HybridRecommendationRetrievalTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            email='hybrid-buyer@example.com',
            password='pass1234',
            role='buyer',
        )
        self.trusted_seller = User.objects.create_user(
            email='trusted-hybrid-seller@example.com',
            password='pass1234',
            role='seller',
            is_seller=True,
            is_verified=True,
            is_verified_seller=True,
        )
        self.weak_seller = User.objects.create_user(
            email='weak-hybrid-seller@example.com',
            password='pass1234',
            role='seller',
            is_seller=True,
        )
        self.lagos = Location.objects.create(state='Lagos', city='Ikeja')
        self.abuja = Location.objects.create(state='FCT', city='Abuja')

        SellerProfile.objects.create(
            user=self.trusted_seller,
            status=SellerProfile.STATUS_APPROVED,
            is_verified_seller=True,
            verified=True,
            rating=4.8,
            total_reviews=32,
            active_location=self.lagos,
        )
        SellerProfile.objects.create(
            user=self.weak_seller,
            status=SellerProfile.STATUS_APPROVED,
            is_verified_seller=False,
            verified=False,
            rating=2.5,
            total_reviews=1,
            active_location=self.lagos,
        )

        self.category = Category.objects.create(name='Phones')

        self.best_match = Product.objects.create(
            seller=self.trusted_seller,
            title='iPhone 11 128GB Lagos Clean',
            description='Clean tokunbo iPhone 11 with 128GB storage and strong battery.',
            category=self.category,
            location=self.lagos,
            price=Decimal('150000.00'),
            quantity=8,
            condition='fair',
            status='active',
            is_verified=True,
            is_verified_product=True,
            views_count=45,
            favorites_count=9,
            search_tags=['iphone', 'iphone 11', '128gb', 'lagos', 'tokunbo'],
            attributes={'storage': '128GB', 'battery': 'strong'},
            attributes_verified=True,
        )
        self.weaker_match = Product.objects.create(
            seller=self.weak_seller,
            title='iPhone 11 Lagos',
            description='Used iPhone available in Lagos.',
            category=self.category,
            location=self.lagos,
            price=Decimal('145000.00'),
            quantity=1,
            condition='fair',
            status='active',
            views_count=2,
            favorites_count=0,
            search_tags=['iphone'],
        )
        self.over_budget = Product.objects.create(
            seller=self.trusted_seller,
            title='iPhone 11 128GB Lagos Premium',
            description='A stronger iPhone option but above the requested budget.',
            category=self.category,
            location=self.lagos,
            price=Decimal('260000.00'),
            quantity=4,
            condition='fair',
            status='active',
            is_verified=True,
            is_verified_product=True,
            search_tags=['iphone', '128gb', 'lagos'],
        )

        self.slots = {
            'category': 'Phones',
            'product_type': 'iphone',
            'raw_query': 'iphone 128gb under 200k in lagos',
            'price_max': 200000,
            'location': 'Lagos',
            'condition': 'fair',
        }

    def _new_session(self):
        return ConversationSession.objects.create(
            session_id='hybrid-reco-session',
            user=self.buyer,
            user_name='Hybrid Buyer',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
        )

    def test_hybrid_ranking_beats_dense_vector_noise(self):
        def dense_prefers_weaker_product(query, qs, candidate_limit=1000, top_k=1000):
            return [
                (self.weaker_match.id, 0.99),
                (self.best_match.id, 0.45),
            ]

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=dense_prefers_weaker_product):
            products = RecommendationService._find_products(self.slots, top_k=3)

        self.assertEqual(products[0].id, self.best_match.id)
        self.assertNotIn(self.over_budget.id, [product.id for product in products])
        self.assertTrue(all(product.price <= Decimal('200000.00') for product in products))
        self.assertGreater(
            products[0].recommendation_score_components['keyword_match'],
            products[1].recommendation_score_components['keyword_match'],
        )
        self.assertGreater(
            products[0].recommendation_score_components['seller_trust'],
            products[1].recommendation_score_components['seller_trust'],
        )

    def test_keyword_fallback_returns_relevant_products_without_dense_results(self):
        with patch('assistant.services.recommendation_service.search_similar_products', return_value=[]):
            products = RecommendationService._find_products(self.slots, top_k=3)

        self.assertEqual(products[0].id, self.best_match.id)
        self.assertEqual(products[0].recommendation_score_components['dense_similarity'], 0.0)
        self.assertGreater(products[0].recommendation_score_components['keyword_match'], 0.0)
        self.assertIn('shares important query keywords', products[0].recommendation_match_reasons)

    def test_recommendation_metadata_explains_each_ranked_product(self):
        with patch('assistant.services.recommendation_service.search_similar_products', return_value=[]):
            products = RecommendationService._find_products(self.slots, top_k=2)

        metadata = RecommendationService._exact_match_metadata(products, self.slots)
        first = metadata['suggested_products'][0]

        self.assertEqual(first['id'], str(self.best_match.id))
        self.assertGreater(first['ranking']['total_score'], 0)
        self.assertIn('price_fit', first['ranking']['components'])
        self.assertIn('location_fit', first['ranking']['components'])
        self.assertIn('seller_trust', first['ranking']['components'])
        self.assertIn('verified_product', first['ranking']['components'])
        self.assertIn('matches requested product family', first['match_reasons'])
