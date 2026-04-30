import json
from decimal import Decimal
from types import SimpleNamespace
from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import Mock, patch

from assistant.models import ConversationSession, RecommendationDemandGap, UserBehaviorProfile
from assistant.services.recommendation_service import RecommendationService
from assistant.services.slot_extractor import SlotExtractor
from assistant.tasks import aggregate_user_behavior_profiles_task
from cart.models import Cart, CartEvent
from market.models import Category, Location, Product


User = get_user_model()


class RecommendationArchitectureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='buyer@example.com',
            password='pass1234',
            first_name='Buyer',
            last_name='One',
            role='buyer',
        )
        self.seller = User.objects.create_user(
            email='seller@example.com',
            password='pass1234',
            first_name='Seller',
            last_name='One',
            role='seller',
        )
        self.cat_phone = Category.objects.create(name='Phones')
        self.cat_shoe = Category.objects.create(name='Shoes')
        self.cat_beauty = Category.objects.create(name='Beauty')
        self.cat_grocery = Category.objects.create(name='Groceries')
        self.location = Location.objects.create(state='Lagos', city='Ikeja')
        self.location_surulere = Location.objects.create(state='Lagos', city='Surulere')
        self.location_mainland = Location.objects.create(state='Lagos', city='Yaba')
        self.location_lekki = Location.objects.create(state='Lagos', city='Lekki')
        self.location_abuja = Location.objects.create(state='FCT', city='Abuja')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Samsung Galaxy A54',
            description='Good smartphone in black color',
            category=self.cat_phone,
            location=self.location,
            price=500000,
            quantity=3,
            condition='good',
            status='active',
        )
        self.iphone_low = Product.objects.create(
            seller=self.seller,
            title='iPhone XR Budget',
            description='Affordable iPhone 11 in fair condition',
            category=self.cat_phone,
            location=self.location_surulere,
            price=95000,
            quantity=2,
            condition='fair',
            status='active',
        )
        self.iphone_mid = Product.objects.create(
            seller=self.seller,
            title='iPhone 11 Mainland',
            description='iPhone 11 128GB available in Yaba',
            category=self.cat_phone,
            location=self.location_mainland,
            price=130000,
            quantity=2,
            condition='fair',
            status='active',
        )
        self.iphone_high = Product.objects.create(
            seller=self.seller,
            title='iPhone 11 Premium',
            description='Premium iPhone 11 option',
            category=self.cat_phone,
            location=self.location,
            price=180000,
            quantity=2,
            condition='fair',
            status='active',
        )
        self.iphone_new = Product.objects.create(
            seller=self.seller,
            title='iPhone 11 128GB New',
            description='Brand new iPhone 11 128GB',
            category=self.cat_phone,
            location=self.location_lekki,
            price=110000,
            quantity=2,
            condition='new',
            status='active',
        )
        self.iphone_abuja = Product.objects.create(
            seller=self.seller,
            title='iPhone 11 Abuja',
            description='Affordable iPhone 11 in Abuja only',
            category=self.cat_phone,
            location=self.location_abuja,
            price=100000,
            quantity=2,
            condition='fair',
            status='active',
        )
        self.sunscreen_spf50 = Product.objects.create(
            seller=self.seller,
            title='SPF 50 Sunscreen Lotion',
            description='Broad spectrum sunscreen for face and body',
            category=self.cat_beauty,
            location=self.location,
            price=12000,
            quantity=5,
            condition='new',
            status='active',
            attributes={'spf': '50'},
            attributes_verified=True,
        )
        self.rice_basmati = Product.objects.create(
            seller=self.seller,
            title='Basmati Rice 5kg',
            description='Long grain basmati rice for home cooking',
            category=self.cat_grocery,
            location=self.location_surulere,
            price=18000,
            quantity=8,
            condition='new',
            status='active',
            attributes={'variety': 'basmati'},
            attributes_verified=True,
        )
        self.nike_shoe = Product.objects.create(
            seller=self.seller,
            title='Nike Running Sneaker Size 42',
            description='Comfortable running shoe for daily training',
            category=self.cat_shoe,
            location=self.location_abuja,
            price=58000,
            quantity=4,
            condition='new',
            status='active',
            brand='Nike',
            attributes={'size': '42'},
            attributes_verified=True,
        )

    def _new_session(self):
        return ConversationSession.objects.create(
            session_id='sess-0001',
            user=self.user,
            user_name='Buyer One',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
        )

    def _new_guest_session(self):
        return ConversationSession.objects.create(
            session_id='guest-sess',
            user=None,
            user_name='Guest',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
        )

    def _semantic_results(self, query, qs, candidate_limit=250, top_k=80):
        ids = list(qs.order_by('price', 'id').values_list('id', flat=True)[:top_k])
        return [(product_id, 0.99) for product_id in ids]

    def _post_chat(self, payload, *, user=None):
        if user is not None:
            self.client.force_login(user)
        return self.client.post(
            '/assistant/api/chat/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_slot_extractor_is_structured(self):
        extracted = SlotExtractor.extract('I need samsung phone under 600k in lagos fairly used black')
        self.assertEqual(extracted['location'], 'Lagos')
        self.assertEqual(extracted['brand'], 'Samsung')
        self.assertEqual(extracted['price_max'], 600000.0)
        self.assertIn(extracted['condition'], ['fair', 'used'])

    def test_slot_extractor_treats_size_as_attribute_not_budget(self):
        extracted = SlotExtractor.extract('affordable sneakers size 42 in Abuja', {})
        self.assertIsNone(extracted.get('price_max'))
        self.assertEqual(extracted.get('attributes', {}).get('size'), '42')
        self.assertIsNone(extracted.get('brand'))
        self.assertIn((extracted.get('location') or '').lower(), {'abuja', ''})

    def test_slot_extractor_preserves_whole_word_brand_matching(self):
        extracted = SlotExtractor.extract('ford ranger under 500k', {})
        self.assertEqual((extracted.get('brand') or '').lower(), 'ford')
        self.assertEqual(extracted.get('price_max'), 500000.0)

    def test_slot_extractor_affordable_does_not_invent_ford_brand(self):
        extracted = SlotExtractor.extract('I want affordable Nike sneakers', {})
        self.assertEqual((extracted.get('brand') or '').lower(), 'nike')
        self.assertNotEqual((extracted.get('brand') or '').lower(), 'ford')

    def test_slot_extractor_storage_number_does_not_become_price(self):
        extracted = SlotExtractor.extract(
            'I want the 128GB one',
            {'_last_clarification_key': 'storage'},
        )
        self.assertIsNone(extracted.get('price_max'))

    def test_slot_extractor_does_not_read_phone_as_ph_location(self):
        extracted = SlotExtractor.extract('128GB phone', {})
        self.assertEqual(extracted.get('product_type'), 'phone')
        self.assertIsNone(extracted.get('location'))

    def test_slot_extractor_does_not_read_black_as_ac_product(self):
        extracted = SlotExtractor.extract('black', {})
        self.assertIsNone(extracted.get('product_type'))
        self.assertEqual(extracted.get('color'), 'black')

    def test_slot_extractor_recognizes_live_catalog_product_families(self):
        sunscreen = SlotExtractor.extract('I need sunscreen around 25000 naira', {})
        self.assertEqual(sunscreen.get('product_type'), 'sunscreen')
        self.assertEqual(sunscreen.get('price_max'), 25000.0)

        rice = SlotExtractor.extract('I want 50kg premium basmati rice', {})
        self.assertEqual(rice.get('product_type'), 'basmati rice')
        self.assertIsNone(rice.get('price_max'))
        self.assertEqual(rice.get('price_intent'), 'premium')

    def test_context_drift_requires_confirmation_and_creates_new_session(self):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Phones',
            'product_type': 'phone',
            'price_max': 600000,
            'condition': 'used',
        }
        session.intent_state = {
            'clarification_count': 0,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        session.refresh_from_db()
        self.assertEqual(session.constraint_state.get('category'), 'Phones')

        drift = RecommendationService.evaluate_recommendation_message(session, 'Now I want shoes')
        self.assertTrue(drift['drift_detected'])

        switched = RecommendationService.evaluate_recommendation_message(session, 'yes')
        self.assertIsNotNone(switched['new_session_id'])
        self.assertNotEqual(switched['new_session_id'], session.session_id)
        session.refresh_from_db()
        self.assertIsNotNone(session.completed_at)

    def _assert_product_switch_branches_without_stale_slots(
        self,
        *,
        prior_slots,
        message,
        expected_family,
        stale_keys,
    ):
        session = self._new_session()
        session.constraint_state = prior_slots
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_context_shift_llm', return_value=None), \
             patch.object(RecommendationService, '_detect_rejection_llm', side_effect=AssertionError('new product switch must not run rejection detection')):
            drift = RecommendationService.evaluate_recommendation_message(session, message)

        self.assertEqual(drift['source'], 'recommendation_drift_detected')
        self.assertTrue(drift['drift_detected'])
        self.assertEqual(drift['metadata']['context_shift_action'], 'branch')
        self.assertEqual(drift['metadata']['context_shift_source'], 'fallback')

        session.refresh_from_db()
        pending = session.intent_state.get('pending_category_switch') or {}
        family = (
            str(pending.get('product_type') or pending.get('category') or '')
            .strip()
            .lower()
        )
        self.assertIn(expected_family, family)
        for key, stale_value in stale_keys.items():
            self.assertNotEqual(pending.get(key), stale_value)
        self.assertNotIn('_shown_product_ids', pending)
        self.assertFalse(pending.get('_last_clarification_key'))

        switched = RecommendationService.evaluate_recommendation_message(session, 'yes')
        self.assertIsNotNone(switched['new_session_id'])
        new_session = ConversationSession.objects.get(session_id=switched['new_session_id'])
        self.assertIn(
            expected_family,
            str(
                new_session.constraint_state.get('product_type')
                or new_session.constraint_state.get('category')
                or ''
            ).lower(),
        )
        for key, stale_value in stale_keys.items():
            self.assertNotEqual(new_session.constraint_state.get(key), stale_value)
        return new_session

    def test_context_drift_phone_to_sunscreen_branches_without_old_phone_slots(self):
        new_session = self._assert_product_switch_branches_without_stale_slots(
            prior_slots={
                'category': 'Phones',
                'product_type': 'phone',
                'price_max': 600000,
                'condition': 'fair',
                'location': 'Lagos',
                '_shown_product_ids': [self.iphone_high.id],
                '_last_clarification_key': 'storage',
            },
            message='now I need SPF 50 sunscreen in Lagos under 25k',
            expected_family='sunscreen',
            stale_keys={'price_max': 600000, 'condition': 'fair'},
        )
        self.assertEqual(new_session.constraint_state.get('price_max'), 25000.0)
        self.assertNotEqual(new_session.constraint_state.get('condition'), 'fair')

    def test_context_drift_phone_to_rice_branches_without_old_phone_slots(self):
        new_session = self._assert_product_switch_branches_without_stale_slots(
            prior_slots={
                'category': 'Phones',
                'product_type': 'phone',
                'price_max': 600000,
                'condition': 'fair',
                'location': 'Lagos',
                '_shown_product_ids': [self.product.id],
            },
            message='actually show me premium basmati rice 5kg in Lagos',
            expected_family='basmati rice',
            stale_keys={'price_max': 600000, 'condition': 'fair'},
        )
        self.assertEqual(new_session.constraint_state.get('price_intent'), 'premium')
        self.assertNotEqual(new_session.constraint_state.get('product_type'), 'phone')

    def test_context_drift_phone_to_shoes_branches_without_old_phone_slots(self):
        new_session = self._assert_product_switch_branches_without_stale_slots(
            prior_slots={
                'category': 'Phones',
                'product_type': 'phone',
                'price_max': 600000,
                'condition': 'fair',
                'location': 'Lagos',
                '_shown_product_ids': [self.product.id],
            },
            message='switch to Nike shoes size 42 in Abuja',
            expected_family='shoe',
            stale_keys={'price_max': 600000, 'location': 'Lagos'},
        )
        self.assertEqual(new_session.constraint_state.get('brand'), 'Nike')
        self.assertEqual(new_session.constraint_state.get('attributes', {}).get('size'), '42')

    def test_context_drift_shoes_back_to_phone_branches_without_old_shoe_slots(self):
        new_session = self._assert_product_switch_branches_without_stale_slots(
            prior_slots={
                'category': 'Shoes',
                'product_type': 'shoe',
                'brand': 'Nike',
                'location': 'Abuja',
                'attributes': {'size': '42'},
                '_shown_product_ids': [self.nike_shoe.id],
            },
            message='go back to iPhone under 200k in Lagos',
            expected_family='phone',
            stale_keys={'brand': 'Nike', 'location': 'Abuja'},
        )
        self.assertEqual((new_session.constraint_state.get('brand') or '').lower(), 'iphone')
        self.assertEqual(new_session.constraint_state.get('price_max'), 200000.0)

    def test_llm_context_shift_can_branch_for_catalog_product_not_in_static_terms(self):
        cat_bottle = Category.objects.create(name='Bottles')
        Product.objects.create(
            seller=self.seller,
            title='Insulated Water Bottle 1L',
            description='Reusable bottle for hot and cold drinks',
            category=cat_bottle,
            location=self.location,
            price=9000,
            quantity=6,
            condition='new',
            status='active',
        )
        session = self._new_session()
        session.constraint_state = {
            'category': 'Phones',
            'product_type': 'phone',
            'price_max': 600000,
            '_shown_product_ids': [self.product.id],
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={
            'product_type': 'water bottle',
            'category': 'Bottles',
        }), \
             patch.object(RecommendationService, '_detect_context_shift_llm', return_value=None), \
             patch.object(RecommendationService, '_detect_rejection_llm', side_effect=AssertionError('new product switch must not run rejection detection')):
            drift = RecommendationService.evaluate_recommendation_message(
                session,
                'actually I need an insulated water bottle',
            )

        self.assertEqual(drift['source'], 'recommendation_drift_detected')
        session.refresh_from_db()
        pending = session.intent_state.get('pending_category_switch') or {}
        self.assertEqual(pending.get('product_type'), 'water bottle')
        self.assertEqual(pending.get('category'), 'Bottles')
        self.assertNotEqual(pending.get('price_max'), 600000)

    def test_llm_context_shift_classifier_json_can_drive_reset_or_branch(self):
        adapter = Mock()
        adapter.is_available.return_value = True
        adapter.generate.return_value = {
            'response': json.dumps({
                'action': 'branch',
                'reason': 'new product family',
                'confidence': 0.91,
            })
        }

        with patch('assistant.services.recommendation_service.LocalModelAdapter.get_instance', return_value=adapter):
            decision = RecommendationService._detect_context_shift_llm(
                message='actually I need sunscreen now',
                prior_slots={'product_type': 'phone', 'price_max': 600000},
                raw_slots={'product_type': 'sunscreen'},
                slots={'product_type': 'sunscreen'},
            )

        self.assertEqual(decision.action, 'branch')
        self.assertEqual(decision.source, 'llm')
        self.assertGreaterEqual(decision.confidence, 0.9)
        self.assertIn('Current search slots', adapter.generate.call_args.kwargs['prompt'])

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_brand_only_new_product_request_escapes_pending_clarification_context(self, clarification_mock):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'location': 'Lagos',
            '_last_clarification_key': 'condition',
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_context_shift_llm', return_value=None), \
             patch.object(RecommendationService, '_detect_rejection_llm', side_effect=AssertionError('product switch should not run rejection detection')), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'I need an iPhone in Lagos under 80k',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_drift_detected')
        self.assertTrue(result['drift_detected'])
        self.assertEqual(session.constraint_state.get('product_type'), 'sunscreen')
        pending = session.intent_state.get('pending_category_switch') or {}
        self.assertEqual(pending.get('product_type'), 'phone')
        self.assertEqual((pending.get('brand') or '').lower(), 'iphone')
        self.assertEqual(pending.get('price_max'), 80000.0)
        self.assertFalse(pending.get('_last_clarification_key'))

    def test_demand_gap_logging_increments_frequency(self):
        session = self._new_session()
        constraints = {'category': 'Tractors', 'brand': 'X', 'location': 'Abuja'}
        RecommendationService.log_demand_gap(session, constraints)
        RecommendationService.log_demand_gap(session, constraints)

        gap = RecommendationDemandGap.objects.get(user=self.user, requested_category='Tractors')
        self.assertEqual(gap.frequency, 2)

    def test_behavior_aggregation_creates_profile_and_high_intent_flag(self):
        session = self._new_session()
        session.context_type = ConversationSession.CONTEXT_TYPE_RECOMMENDATION
        session.constraint_state = {'category': 'Phones', 'budget_range': {'min': 100000, 'max': 700000}}
        session.save()

        cart = Cart.objects.create(user=self.user)
        for _ in range(3):
            CartEvent.objects.create(
                event_type='cart_item_added',
                user=self.user,
                cart_id=cart.id,
                data={'source': 'ai'},
            )

        aggregate_user_behavior_profiles_task()

        profile = UserBehaviorProfile.objects.get(user=self.user)
        self.assertGreaterEqual(profile.ai_search_count, 1)
        self.assertTrue(profile.ai_high_intent_no_conversion)

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_confirmation_then_search_flow(self, clarification_mock):
        session = self._new_session()
        clarification_mock.side_effect = [
            {'action': 'clarify', 'question': 'Phone model or brand - any preference?', 'reasoning': 'Need product family detail'},
            {'action': 'clarify', 'question': 'New or fairly used?', 'reasoning': 'Need condition'},
            {'action': 'search', 'reasoning': 'Enough detail to search'},
        ]

        with patch.object(RecommendationService, '_detect_rejection_llm', return_value={
            'is_rejection': False,
            'constraint_update': {},
            'acknowledgement': '',
        }):
            first = RecommendationService.evaluate_recommendation_message(session, 'I need phone in lagos')
            self.assertIn('model', first['reply'].lower())

            second = RecommendationService.evaluate_recommendation_message(session, 'under 600k')
            self.assertIn('new or fairly used', second['reply'].lower())

            third = RecommendationService.evaluate_recommendation_message(session, 'used')
            self.assertIn(third['source'], {'recommendation_results', 'recommendation_results_alternatives'})
            self.assertNotEqual(third['source'], 'recommendation_confirmation')
            self.assertNotIn('shall i', third['reply'].lower())
            self.assertNotIn('should i', third['reply'].lower())

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_direct_search_skips_confirmation_gate(self, clarification_mock):
        session = self._new_session()
        clarification_mock.return_value = {'action': 'search', 'reasoning': 'Enough info to search now'}

        result = RecommendationService.evaluate_recommendation_message(session, 'I need Samsung phone in Lagos')

        self.assertEqual(result['source'], 'recommendation_results')
        self.assertNotIn('shall i', result['reply'].lower())
        self.assertNotIn('should i', result['reply'].lower())
        self.assertNotIn('proceed', result['reply'].lower())
        self.assertEqual(result['metadata']['knowledge_lane'], 'homepage_reco_catalog')
        self.assertEqual(result['metadata']['retrieval_system'], 'catalog_semantic_search')
        self.assertTrue(result['metadata']['exact_match_found'])
        self.assertFalse(result['metadata']['no_exact_match'])
        self.assertEqual(result['metadata']['match_contract'], 'exact_matches_only')
        self.assertGreaterEqual(result['metadata']['suggested_product_count'], 1)
        self.assertEqual(
            result['metadata']['suggested_products'][0]['product_url'],
            f"/product/{self.product.slug}",
        )

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_first_clarification_turn_returns_interleaved_results(self, clarification_mock):
        session = self._new_session()
        clarification_mock.return_value = {
            'action': 'clarify',
            'question': '128GB or 256GB?',
            'attribute_key': 'storage',
            'reasoning': 'Need storage preference',
        }

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_find_products_broad', return_value=[
                 self.iphone_low,
                 self.iphone_mid,
                 self.iphone_high,
             ]):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'I want an iPhone in Lagos',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_interleaved')
        self.assertIn('128GB or 256GB?', result['reply'])
        self.assertIn(self.iphone_low.title, result['reply'])
        self.assertIn('🥇', result['reply'])
        self.assertTrue(session.constraint_state.get('_shown_product_ids'))
        self.assertEqual(session.constraint_state.get('_last_clarification_key'), 'storage')

    def test_interleaved_sunscreen_results_keep_explicit_hard_filters(self):
        slots = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'raw_query': 'I want sunscreen in Lagos',
            'price_max': 5000,
            'location': 'Abuja',
            'condition': 'fair',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            products = RecommendationService._find_products_broad(slots, top_k=5)

        self.assertEqual(products, [])

    def test_broad_rice_results_do_not_surface_unrelated_categories(self):
        slots = {
            'category': 'Groceries',
            'product_type': 'rice',
            'raw_query': 'show me rice',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            products = RecommendationService._find_products_broad(slots, top_k=5)

        self.assertEqual([product.id for product in products], [self.rice_basmati.id])
        self.assertTrue(all(product.category_id == self.cat_grocery.id for product in products))

    def test_broad_retrieval_keeps_family_when_constraints_are_missing(self):
        slots = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'raw_query': 'show me sunscreen',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            products = RecommendationService._find_products_broad(slots, top_k=3)

        self.assertEqual([product.id for product in products], [self.sunscreen_spf50.id])

    def test_budget_search_keeps_price_hard_and_orders_cheapest_valid(self):
        slots = {
            'category': 'Phones',
            'product_type': 'phone',
            'brand': 'Iphone',
            'raw_query': 'budget iphone in lagos under 150k',
            'price_max': 150000,
            'location': 'Lagos',
            'condition': 'fair',
        }

        def semantic_prefers_expensive(query, qs, candidate_limit=250, top_k=80):
            ids = list(qs.order_by('-price', 'id').values_list('id', flat=True)[:top_k])
            return [(product_id, 0.99 - index * 0.01) for index, product_id in enumerate(ids)]

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=semantic_prefers_expensive):
            products = RecommendationService._find_products(slots, top_k=5)

        self.assertEqual([product.id for product in products], [self.iphone_low.id, self.iphone_mid.id])
        self.assertTrue(all(product.price <= 150000 for product in products))

    def test_premium_intent_ranks_premium_products_above_budget_products(self):
        slots = {
            'category': 'Phones',
            'product_type': 'phone',
            'brand': 'Iphone',
            'raw_query': 'premium iphone in lagos',
            'location': 'Lagos',
            'price_intent': 'premium',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            products = RecommendationService._find_products(slots, top_k=4)

        self.assertEqual(products[0].id, self.iphone_high.id)
        self.assertGreater(products[0].price, self.iphone_low.price)

    def test_no_exact_match_response_labels_alternatives(self):
        session = self._new_session()

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, 'generate_clarification_question', return_value={
                 'action': 'search',
                 'reasoning': 'Specific enough to search',
             }), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'I need an iPhone in Lagos under 80k',
            )

        self.assertEqual(result['source'], 'recommendation_results_alternatives')
        self.assertIn('No exact match', result['reply'])
        self.assertIn('Alternatives (not exact matches)', result['reply'])
        self.assertFalse(result['metadata']['exact_match_found'])
        self.assertTrue(result['metadata']['no_exact_match'])
        self.assertEqual(
            result['metadata']['match_contract'],
            'no_exact_match_then_labeled_alternatives',
        )
        self.assertEqual(
            result['metadata']['no_exact_match_reason'],
            'hard_constraints_no_exact_match',
        )
        self.assertTrue(result['metadata']['alternatives_labeled'])
        self.assertEqual(
            result['metadata']['hard_constraints']['price_max'],
            80000.0,
        )
        self.assertEqual(result['metadata']['suggestion_match_type'], 'alternative')
        self.assertTrue(result['metadata']['suggested_products'])
        self.assertTrue(all(
            item['match_type'] == 'alternative'
            for item in result['metadata']['suggested_products']
        ))
        prices = [
            float(item['price'])
            for item in result['metadata']['suggested_products']
        ]
        self.assertEqual(prices, sorted(prices))

    def test_iphone_under_200k_no_exact_contract_never_marks_expensive_as_match(self):
        session = self._new_session()
        Product.objects.filter(
            id__in=[
                self.iphone_low.id,
                self.iphone_mid.id,
                self.iphone_high.id,
                self.iphone_new.id,
                self.iphone_abuja.id,
            ],
        ).update(price=Decimal('450000.00'))

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, 'generate_clarification_question', return_value={
                 'action': 'search',
                 'reasoning': 'Specific enough to search',
             }), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'iPhone under 200k',
            )

        self.assertEqual(result['source'], 'recommendation_results_alternatives')
        self.assertIn('No exact match', result['reply'])
        self.assertFalse(result['metadata']['exact_match_found'])
        self.assertTrue(result['metadata']['no_exact_match'])
        self.assertEqual(
            result['metadata']['match_contract'],
            'no_exact_match_then_labeled_alternatives',
        )
        self.assertEqual(
            result['metadata']['hard_constraints']['price_max'],
            200000.0,
        )
        self.assertEqual(result['metadata']['suggestion_match_type'], 'alternative')
        self.assertTrue(result['metadata']['suggested_products'])
        self.assertTrue(all(
            item['match_type'] == 'alternative'
            for item in result['metadata']['suggested_products']
        ))
        self.assertFalse(any(
            item['match_type'] == 'match' and float(item['price']) > 200000
            for item in result['metadata']['suggested_products']
        ))
        self.assertTrue(all(
            float(item['price']) > 200000
            for item in result['metadata']['suggested_products']
        ))

    def test_clarification_path_returns_no_exact_when_hard_filters_have_no_candidates(self):
        session = self._new_session()

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, 'generate_clarification_question', return_value={
                 'action': 'clarify',
                 'question': 'New or fairly used?',
                 'reasoning': 'Need condition',
             }), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'I need an iPhone in Lagos under 80k',
            )

        self.assertEqual(result['source'], 'recommendation_results_alternatives')
        self.assertIn('No exact match', result['reply'])
        self.assertIn('Alternatives (not exact matches)', result['reply'])
        self.assertFalse(result['metadata']['exact_match_found'])
        self.assertTrue(result['metadata']['no_exact_match'])
        self.assertEqual(
            result['metadata']['no_exact_match_reason'],
            'clarification_hard_constraints_no_exact_match',
        )
        self.assertNotIn('New or fairly used?', result['reply'])

    def test_location_is_a_hard_filter_for_exact_matches(self):
        slots = {
            'category': 'Phones',
            'product_type': 'phone',
            'brand': 'Iphone',
            'raw_query': 'iphone in abuja under 150k',
            'price_max': 150000,
            'location': 'Abuja',
            'condition': 'fair',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            products = RecommendationService._find_products(slots, top_k=5)

        self.assertEqual([product.id for product in products], [self.iphone_abuja.id])
        self.assertTrue(all(product.location_id == self.location_abuja.id for product in products))

    def test_brand_is_a_hard_filter_for_exact_matches(self):
        slots = {
            'category': 'Phones',
            'product_type': 'phone',
            'brand': 'Samsung',
            'raw_query': 'samsung phone in lagos under 600k',
            'price_max': 600000,
            'location': 'Lagos',
            'condition': 'good',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            products = RecommendationService._find_products(slots, top_k=5)

        self.assertEqual([product.id for product in products], [self.product.id])
        self.assertTrue(all('samsung' in product.title.lower() for product in products))

    def test_product_family_is_a_hard_filter_for_exact_matches(self):
        slots = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'raw_query': 'sunscreen in lagos under 20k',
            'price_max': 20000,
            'location': 'Lagos',
            'condition': 'new',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            products = RecommendationService._find_products(slots, top_k=5)

        self.assertEqual([product.id for product in products], [self.sunscreen_spf50.id])
        self.assertTrue(all('sunscreen' in product.title.lower() for product in products))

    def test_full_results_semantic_ranking_stays_within_constrained_candidates(self):
        slots = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'raw_query': 'spf 50 sunscreen',
        }

        with patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results) as semantic_mock:
            products = RecommendationService._find_products(slots, top_k=5)

        self.assertEqual([product.id for product in products], [self.sunscreen_spf50.id])
        semantic_mock.assert_called_once()
        candidate_queryset = semantic_mock.call_args.args[1]
        candidate_ids = set(candidate_queryset.values_list('id', flat=True))
        self.assertEqual(candidate_ids, {self.sunscreen_spf50.id})

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_live_sunscreen_query_extraction_constrains_interleaved_candidates(self, clarification_mock):
        session = self._new_session()
        clarification_mock.return_value = {
            'action': 'clarify',
            'question': 'SPF 30 or SPF 50?',
            'attribute_key': 'spf',
            'reasoning': 'Need sunscreen SPF detail',
        }
        candidate_sets = []

        def semantic_results(query, qs, candidate_limit=250, top_k=80):
            candidate_sets.append(set(qs.values_list('id', flat=True)))
            return self._semantic_results(query, qs, candidate_limit, top_k)

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=semantic_results):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'I need sunscreen around 25000 naira',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_interleaved')
        self.assertEqual(session.constraint_state.get('product_type'), 'sunscreen')
        self.assertIn(self.sunscreen_spf50.title, result['reply'])
        self.assertNotIn(self.product.title, result['reply'])
        self.assertTrue(candidate_sets)
        self.assertEqual(candidate_sets[0], {self.sunscreen_spf50.id})

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_live_basmati_rice_query_extraction_constrains_full_results(self, clarification_mock):
        session = self._new_session()
        clarification_mock.return_value = {
            'action': 'search',
            'reasoning': 'Basmati rice query is specific enough',
        }
        candidate_sets = []

        def semantic_results(query, qs, candidate_limit=250, top_k=80):
            candidate_sets.append(set(qs.values_list('id', flat=True)))
            return self._semantic_results(query, qs, candidate_limit, top_k)

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=semantic_results):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'I want 50kg premium basmati rice',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_results')
        self.assertEqual(session.constraint_state.get('product_type'), 'basmati rice')
        self.assertIsNone(session.constraint_state.get('price_max'))
        self.assertIn(self.rice_basmati.title, result['reply'])
        self.assertNotIn(self.sunscreen_spf50.title, result['reply'])
        self.assertTrue(candidate_sets)
        self.assertEqual(candidate_sets[0], {self.rice_basmati.id})

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_refined_results_do_not_repeat_interleaved_products(self, clarification_mock):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Phones',
            'product_type': 'iphone',
            'location': 'Lagos',
            '_shown_product_ids': [self.iphone_low.id, self.iphone_mid.id],
            '_last_clarification_key': 'storage',
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])
        clarification_mock.return_value = {
            'action': 'search',
            'reasoning': 'Enough info now',
        }

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': False,
                 'constraint_update': {},
                 'acknowledgement': '',
             }), \
             patch.object(RecommendationService, '_find_products', return_value=[
                 self.iphone_low,
                 self.iphone_mid,
                 self.iphone_new,
             ]):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                '128GB',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_results')
        self.assertEqual(result['metadata']['turn_type'], 'clarification_answer')
        self.assertEqual(result['metadata']['turn_outcome'], 'results')
        self.assertNotIn(self.iphone_low.title, result['reply'])
        self.assertNotIn(self.iphone_mid.title, result['reply'])
        self.assertIn(self.iphone_new.title, result['reply'])
        self.assertEqual(session.intent_state.get('last_turn_type'), 'clarification_answer')
        self.assertIn(str(self.iphone_new.id), session.constraint_state.get('_shown_product_ids', []))
        self.assertEqual(
            session.constraint_state.get('attributes', {}).get('storage'),
            '128GB',
        )

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_basmati_resolves_against_active_rice_clarification(self, clarification_mock):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Groceries',
            'product_type': 'rice',
            'location': 'Lagos',
            '_last_clarification_key': 'variety',
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])
        clarification_mock.return_value = {
            'action': 'search',
            'reasoning': 'Enough detail now',
        }

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': False,
                 'constraint_update': {},
                 'acknowledgement': '',
             }), \
             patch.object(RecommendationService, '_find_products', return_value=[self.product]):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'basmati',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_results')
        self.assertEqual(result['metadata']['turn_type'], 'clarification_answer')
        self.assertEqual(result['metadata']['turn_outcome'], 'results')
        self.assertEqual(session.intent_state.get('last_turn_type'), 'clarification_answer')
        self.assertEqual(
            session.constraint_state.get('attributes', {}).get('variety'),
            'basmati',
        )

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_spf_50_resolves_against_active_sunscreen_clarification(self, clarification_mock):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'location': 'Lagos',
            '_last_clarification_key': 'spf',
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])
        clarification_mock.return_value = {
            'action': 'search',
            'reasoning': 'Enough detail now',
        }

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': False,
                 'constraint_update': {},
                 'acknowledgement': '',
             }), \
             patch.object(RecommendationService, '_find_products', return_value=[self.product]):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'SPF 50',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_results')
        self.assertEqual(result['metadata']['turn_type'], 'clarification_answer')
        self.assertEqual(result['metadata']['turn_outcome'], 'results')
        self.assertEqual(session.intent_state.get('last_turn_type'), 'clarification_answer')
        self.assertEqual(
            session.constraint_state.get('attributes', {}).get('spf'),
            'SPF 50',
        )

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_clarification_answer_stays_in_thread_and_skips_stray_reply(self, clarification_mock):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Phones',
            'product_type': 'phone',
            'location': 'Lagos',
            '_last_clarification_key': 'color',
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])
        clarification_mock.return_value = {
            'action': 'search',
            'reasoning': 'Enough detail now',
        }

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': False,
                 'constraint_update': {},
                 'acknowledgement': '',
             }), \
             patch.object(RecommendationService, '_stray_reply', side_effect=AssertionError('stray should not run')), \
             patch.object(RecommendationService, '_find_products', return_value=[self.product]):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'black',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_results')
        self.assertEqual(result['metadata']['turn_type'], 'clarification_answer')
        self.assertEqual(session.intent_state.get('last_turn_type'), 'clarification_answer')
        self.assertNotEqual(result['source'], 'recommendation_stray')
        self.assertEqual(
            session.constraint_state.get('attributes', {}).get('color'),
            'black',
        )

    @patch.object(RecommendationService, 'generate_clarification_question')
    def test_interleaved_clarification_returns_no_exact_when_broad_empty_with_constraints(self, clarification_mock):
        session = self._new_session()
        clarification_mock.return_value = {
            'action': 'clarify',
            'question': '128GB or 256GB?',
            'attribute_key': 'storage',
            'reasoning': 'Need storage preference',
        }

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_find_products_broad', return_value=[]):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'I want an iPhone in Lagos',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_results_alternatives')
        self.assertIn('No exact match', result['reply'])
        self.assertNotIn('128GB or 256GB?', result['reply'])

    def test_friendly_redirect_for_non_product_message(self):
        session = self._new_session()
        result = RecommendationService.evaluate_recommendation_message(session, 'How do I get a refund?')
        self.assertIn('product recommendations only', result['reply'])

    def test_detect_rejection_llm_english_price_high(self):
        adapter = Mock()
        adapter.is_available.return_value = True
        adapter.generate.return_value = {
            'response': (
                '{"is_rejection": true, "rejection_type": "price_high", '
                '"acknowledgement": "Got it - let me go lower.", '
                '"reasoning": "User says results are too expensive"}'
            )
        }

        with patch('assistant.services.recommendation_service.LocalModelAdapter.get_instance', return_value=adapter):
            result = RecommendationService._detect_rejection_llm(
                'these are too expensive',
                {'product_type': 'iphone', 'price_max': 200000},
            )

        self.assertTrue(result['is_rejection'])
        self.assertLessEqual(result['constraint_update']['price_max'], 140000)
        self.assertEqual(adapter.generate.call_args.kwargs['max_tokens'], 120)
        self.assertEqual(adapter.generate.call_args.kwargs['temperature'], 0.1)

    def test_detect_rejection_llm_pidgin_price_high(self):
        adapter = Mock()
        adapter.is_available.return_value = True
        adapter.generate.return_value = {
            'response': (
                '{"is_rejection": true, "rejection_type": "price_high", '
                '"acknowledgement": "Abeg make we reduce am small.", '
                '"reasoning": "Pidgin complaint about high price"}'
            )
        }

        with patch('assistant.services.recommendation_service.LocalModelAdapter.get_instance', return_value=adapter):
            result = RecommendationService._detect_rejection_llm(
                'e don too cost abeg',
                {'product_type': 'iphone', 'price_max': 200000},
            )

        self.assertTrue(result['is_rejection'])
        self.assertLessEqual(result['constraint_update']['price_max'], 140000)
        self.assertIn('reduce', result['acknowledgement'].lower())

    def test_detect_rejection_llm_pidgin_general_rejection(self):
        adapter = Mock()
        adapter.is_available.return_value = True
        adapter.generate.return_value = {
            'response': (
                '{"is_rejection": true, "rejection_type": "general", '
                '"acknowledgement": "No wahala, make I show another one.", '
                '"reasoning": "User rejects current options generally"}'
            )
        }

        with patch('assistant.services.recommendation_service.LocalModelAdapter.get_instance', return_value=adapter):
            result = RecommendationService._detect_rejection_llm(
                'this no be wetin i want',
                {'product_type': 'iphone', 'price_max': 200000},
            )

        self.assertTrue(result['is_rejection'])
        self.assertEqual(result['constraint_update']['_shown_product_ids'], [])

    def test_detect_rejection_llm_non_rejection_returns_false(self):
        adapter = Mock()
        adapter.is_available.return_value = True
        adapter.generate.return_value = {
            'response': (
                '{"is_rejection": false, "rejection_type": "none", '
                '"acknowledgement": "", "reasoning": "Fresh search request"}'
            )
        }

        with patch('assistant.services.recommendation_service.LocalModelAdapter.get_instance', return_value=adapter):
            result = RecommendationService._detect_rejection_llm(
                'show me iPhone in Lagos',
                {'product_type': 'iphone', 'price_max': 200000},
            )

        self.assertFalse(result['is_rejection'])
        self.assertEqual(result['constraint_update'], {})
        self.assertEqual(result['acknowledgement'], '')

    def test_detect_rejection_llm_falls_back_when_unavailable(self):
        adapter = Mock()
        adapter.is_available.return_value = False

        with patch('assistant.services.recommendation_service.LocalModelAdapter.get_instance', return_value=adapter):
            result = RecommendationService._detect_rejection_llm(
                'these are too expensive',
                {'product_type': 'iphone', 'price_max': 200000},
            )

        self.assertTrue(result['is_rejection'])
        self.assertLessEqual(result['constraint_update']['price_max'], 140000)

    def test_show_me_something_cheaper_refines_active_product_family(self):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Phones',
            'product_type': 'iphone',
            'price_max': 200000,
            'location': 'Lagos',
            '_shown_product_ids': [self.iphone_high.id],
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': True,
                 'constraint_update': {'price_max': 140000},
                 'acknowledgement': 'LLM rejection ack.',
             }), \
             patch.object(RecommendationService, 'generate_clarification_question', side_effect=AssertionError('clarification should not run')):
            result = RecommendationService.evaluate_recommendation_message(session, 'show me something cheaper')

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_rejection_refined')
        self.assertTrue(result['reply'].startswith('LLM rejection ack.'))
        self.assertEqual(result['metadata']['active_product_family'], 'iphone')
        self.assertEqual(session.constraint_state['product_type'], 'iphone')
        self.assertEqual(session.constraint_state['category'], 'Phones')
        self.assertLessEqual(session.constraint_state['price_max'], 140000)
        self.assertTrue(session.constraint_state['_shown_product_ids'])
        self.assertIn(self.iphone_low.title, result['reply'])
        self.assertIn(self.iphone_mid.title, result['reply'])
        self.assertNotIn(self.iphone_high.title, result['reply'])
        self.assertNotIn(self.product.title, result['reply'])

    def test_different_options_refreshes_without_losing_category(self):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Phones',
            'product_type': 'iphone',
            'price_max': 200000,
            'location': 'Lagos',
            '_shown_product_ids': [self.iphone_low.id, self.iphone_mid.id],
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': True,
                 'constraint_update': {'_shown_product_ids': []},
                 'acknowledgement': 'Different set coming up.',
             }):
            result = RecommendationService.evaluate_recommendation_message(
                session,
                'not what I wanted, show me something else',
            )

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_rejection_refined')
        self.assertEqual(session.constraint_state['product_type'], 'iphone')
        self.assertEqual(session.constraint_state['category'], 'Phones')
        self.assertIn(str(self.iphone_low.id), session.constraint_state['_shown_product_ids'])
        self.assertIn(str(self.iphone_mid.id), session.constraint_state['_shown_product_ids'])
        self.assertNotIn(self.iphone_low.title, result['reply'])
        self.assertNotIn(self.iphone_mid.title, result['reply'])
        self.assertNotIn(self.product.title, result['reply'])

    def test_condition_rejection_sets_new_and_filters_results(self):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Phones',
            'product_type': 'iphone',
            'price_max': 200000,
            'condition': 'fair',
            'location': 'Lagos',
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': True,
                 'constraint_update': {'condition': 'new'},
                 'acknowledgement': 'Brand new only, no problem.',
             }), \
             patch.object(RecommendationService, 'generate_clarification_question', side_effect=AssertionError('clarification should not run')):
            result = RecommendationService.evaluate_recommendation_message(session, 'I only want brand new')

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_rejection_refined')
        self.assertEqual(session.constraint_state['condition'], 'new')
        self.assertEqual(session.constraint_state['product_type'], 'iphone')
        self.assertEqual(result['metadata']['active_product_family'], 'iphone')
        self.assertIn(self.iphone_new.title, result['reply'])
        self.assertNotIn(self.iphone_low.title, result['reply'])
        self.assertNotIn(self.iphone_mid.title, result['reply'])

    def test_no_result_refinement_fallback_keeps_active_search_intent(self):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'location': 'Lagos',
            '_shown_product_ids': [],
        }
        session.intent_state = {
            'clarification_count': 1,
            'last_intent': 'product_search',
        }
        session.save(update_fields=['constraint_state', 'intent_state', 'updated_at'])

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results), \
             patch.object(RecommendationService, '_detect_rejection_llm', return_value={
                 'is_rejection': True,
                 'constraint_update': {'condition': 'fair'},
                 'acknowledgement': 'Fairly used only, got it.',
             }), \
             patch.object(RecommendationService, 'generate_clarification_question', side_effect=AssertionError('clarification should not run')):
            result = RecommendationService.evaluate_recommendation_message(session, 'fairly used is fine')

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_rejection_no_results')
        self.assertEqual(result['metadata']['active_product_family'], 'sunscreen')
        self.assertFalse(result['metadata']['exact_match_found'])
        self.assertTrue(result['metadata']['no_exact_match'])
        self.assertEqual(
            result['metadata']['no_exact_match_reason'],
            'refinement_hard_constraints_no_exact_match',
        )
        self.assertEqual(result['metadata']['suggestion_match_type'], 'alternative')
        self.assertEqual(session.constraint_state['product_type'], 'sunscreen')
        self.assertIn('sunscreen', result['reply'].lower())
        self.assertNotIn('what are you looking for', result['reply'].lower())

    def test_rejection_without_prior_context_is_not_treated_as_research(self):
        session = self._new_session()

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_rejection_llm', side_effect=AssertionError('rejection detector should not run')), \
             patch.object(SlotExtractor, 'has_product_intent', return_value=False), \
             patch.object(RecommendationService, '_stray_reply', return_value='stray handled'):
            result = RecommendationService.evaluate_recommendation_message(session, 'these are too expensive')

        self.assertNotEqual(result['source'], 'recommendation_rejection_refined')
        self.assertEqual(result['source'], 'recommendation_stray')

    def test_buyer_memory_greeting_uses_prior_homepage_reco_session(self):
        ConversationSession.objects.create(
            session_id='prior-homepage-reco',
            user=self.user,
            user_name='Buyer One',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
            constraint_state={
                'category': 'Phones',
                'product_type': 'iphone',
                'price_max': 200000,
                'location': 'lagos',
                'condition': 'new',
                '_shown_product_ids': [self.iphone_high.id],
            },
        )
        session = self._new_session()

        with patch('assistant.services.recommendation_service.enrich_slots', side_effect=AssertionError('memory greeting should return before enrichment')):
            result = RecommendationService.evaluate_recommendation_message(session, 'hello')

        session.refresh_from_db()
        self.assertEqual(result['source'], 'buyer_memory_greeting')
        self.assertIn('iphone', result['reply'].lower())
        self.assertTrue(session.context_data.get('memory_greeting_sent'))
        self.assertEqual(
            session.context_data.get('pending_memory_resume', {}).get('product_type'),
            'iphone',
        )
        self.assertNotIn('_shown_product_ids', session.context_data.get('pending_memory_resume', {}))

    def test_memory_greeting_yes_resumes_prior_search(self):
        prior_slots = {
            'category': 'Phones',
            'product_type': 'iphone',
            'price_max': 200000,
            'location': 'Lagos',
            'condition': 'fair',
        }
        ConversationSession.objects.create(
            session_id='prior-resume',
            user=self.user,
            user_name='Buyer One',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
            constraint_state=prior_slots,
        )
        session = self._new_session()

        first = RecommendationService.evaluate_recommendation_message(session, 'hi')
        self.assertEqual(first['source'], 'buyer_memory_greeting')

        with patch('assistant.services.recommendation_service.enrich_slots', side_effect=AssertionError('resume should return before enrichment')), \
             patch('assistant.services.recommendation_service.search_similar_products', side_effect=self._semantic_results):
            result = RecommendationService.evaluate_recommendation_message(session, 'yes')

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_memory_resume')
        self.assertEqual(session.constraint_state.get('product_type'), 'iphone')
        self.assertIsNone(session.context_data.get('pending_memory_resume'))
        self.assertIn(self.iphone_low.title, result['reply'])

    def test_memory_greeting_no_starts_fresh(self):
        ConversationSession.objects.create(
            session_id='prior-decline',
            user=self.user,
            user_name='Buyer One',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
            constraint_state={
                'category': 'Phones',
                'product_type': 'iphone',
                'price_max': 200000,
            },
        )
        session = self._new_session()

        first = RecommendationService.evaluate_recommendation_message(session, 'hey')
        self.assertEqual(first['source'], 'buyer_memory_greeting')

        with patch('assistant.services.recommendation_service.enrich_slots', side_effect=AssertionError('decline should return before enrichment')):
            result = RecommendationService.evaluate_recommendation_message(session, 'no')

        session.refresh_from_db()
        self.assertEqual(result['source'], 'recommendation_fresh_start')
        self.assertEqual(session.constraint_state, {})
        self.assertIsNone(session.context_data.get('pending_memory_resume'))
        self.assertTrue(session.context_data.get('memory_greeting_sent'))

    def test_memory_greeting_skips_when_no_prior_session_exists(self):
        session = self._new_session()

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_rejection_llm', side_effect=AssertionError('rejection detector should not run')), \
             patch.object(SlotExtractor, 'has_product_intent', return_value=False), \
             patch.object(RecommendationService, '_stray_reply', return_value='stray handled'):
            result = RecommendationService.evaluate_recommendation_message(session, 'hello there')

        self.assertNotEqual(result['source'], 'buyer_memory_greeting')
        self.assertEqual(result['source'], 'recommendation_stray')

    def test_memory_greeting_skips_for_guest_user(self):
        ConversationSession.objects.create(
            session_id='prior-user-memory',
            user=self.user,
            user_name='Buyer One',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
            constraint_state={
                'category': 'Phones',
                'product_type': 'iphone',
                'price_max': 200000,
            },
        )
        session = self._new_guest_session()

        with patch('assistant.services.recommendation_service.enrich_slots', return_value={}), \
             patch.object(RecommendationService, '_detect_rejection_llm', side_effect=AssertionError('rejection detector should not run')), \
             patch.object(SlotExtractor, 'has_product_intent', return_value=False), \
             patch.object(RecommendationService, '_stray_reply', return_value='stray handled'):
            result = RecommendationService.evaluate_recommendation_message(session, 'hello there')

        self.assertNotEqual(result['source'], 'buyer_memory_greeting')
        self.assertEqual(result['source'], 'recommendation_stray')

    def test_homepage_reco_endpoint_follow_up_cheaper_routes_to_recommendation_first(self):
        session = self._new_session()

        with patch('assistant.processors.conversation_manager.QueryProcessor'), \
             patch('assistant.processors.conversation_manager.LocalModelAdapter.get_instance', return_value=Mock()), \
             patch(
                 'assistant.processors.conversation_manager.RecommendationService.evaluate_recommendation_message',
                 return_value={
                     'reply': 'Cheaper options coming right up.',
                     'source': 'recommendation_rejection_refined',
                     'confidence': 0.88,
                     'metadata': {'intent': 'product_search'},
                     'drift_detected': False,
                     'new_session_id': None,
                 },
             ) as recommendation_mock:
            response = self._post_chat(
                {
                    'message': 'show me something cheaper',
                    'session_id': session.session_id,
                    'assistant_mode': 'homepage_reco',
                },
                user=self.user,
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['reply'], 'Cheaper options coming right up.')
        self.assertEqual(payload['state'], 'chat_mode')
        recommendation_mock.assert_called_once()

    def test_guest_homepage_reco_endpoint_valid_query_returns_preview_not_login_wall(self):
        with patch(
            'assistant.views.RecommendationService.evaluate_recommendation_message',
            return_value={
                'reply': 'Preview results ready.',
                'source': 'recommendation_results',
                'confidence': 0.87,
                'metadata': {'intent': 'product_search'},
                'drift_detected': False,
                'new_session_id': None,
            },
        ) as recommendation_mock:
            response = self._post_chat(
                {
                    'message': 'show me iphone in lagos',
                    'assistant_mode': 'homepage_reco',
                }
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['reply'], 'Preview results ready.')
        self.assertEqual(payload['state'], 'chat_mode')
        self.assertEqual(payload['source'], 'recommendation_results')
        self.assertFalse(payload.get('login_required', False))
        self.assertEqual(payload['metadata']['persistence'], 'temporary')
        self.assertTrue(payload['metadata']['guest_preview'])
        self.assertTrue(payload.get('session_id'))
        guest_session = ConversationSession.objects.get(session_id=payload['session_id'])
        self.assertIsNone(guest_session.user_id)
        self.assertFalse(guest_session.is_persistent)
        recommendation_mock.assert_called_once()

    def test_guest_homepage_reco_endpoint_can_return_interleaved_preview(self):
        with patch(
            'assistant.views.RecommendationService.evaluate_recommendation_message',
            return_value={
                'reply': '128GB or 256GB?\n\n🥇 iPhone 11 — ₦110,000',
                'source': 'recommendation_interleaved',
                'confidence': 0.85,
                'metadata': {'intent': 'product_search'},
                'drift_detected': False,
                'new_session_id': None,
            },
        ) as recommendation_mock:
            response = self._post_chat(
                {
                    'message': 'I want an iPhone in Lagos',
                    'assistant_mode': 'homepage_reco',
                }
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['state'], 'chat_mode')
        self.assertEqual(payload['source'], 'recommendation_interleaved')
        self.assertIn('128GB or 256GB?', payload['reply'])
        self.assertFalse(payload.get('login_required', False))
        recommendation_mock.assert_called_once()

    def test_homepage_reco_endpoint_follow_up_different_options_stays_in_recommendation_flow(self):
        session = self._new_session()

        with patch('assistant.processors.conversation_manager.QueryProcessor'), \
             patch('assistant.processors.conversation_manager.LocalModelAdapter.get_instance', return_value=Mock()), \
             patch(
                 'assistant.processors.conversation_manager.RecommendationService.evaluate_recommendation_message',
                 return_value={
                     'reply': 'Here are different options for you.',
                     'source': 'recommendation_rejection_refined',
                     'confidence': 0.84,
                     'metadata': {'intent': 'product_search'},
                     'drift_detected': False,
                     'new_session_id': None,
                 },
             ) as recommendation_mock:
            response = self._post_chat(
                {
                    'message': 'different options',
                    'session_id': session.session_id,
                    'assistant_mode': 'homepage_reco',
                },
                user=self.user,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reply'], 'Here are different options for you.')
        recommendation_mock.assert_called_once()

    def test_homepage_reco_endpoint_clarification_turn_bypasses_generic_gates(self):
        session = self._new_session()
        session.constraint_state = {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            '_last_clarification_key': 'spf',
        }
        session.save(update_fields=['constraint_state', 'updated_at'])

        with patch('assistant.processors.conversation_manager.QueryProcessor'), \
             patch('assistant.processors.conversation_manager.LocalModelAdapter.get_instance', return_value=Mock()), \
             patch(
                 'assistant.processors.conversation_manager.RecommendationService.evaluate_recommendation_message',
                 return_value={
                     'reply': 'SPF 50 noted. Narrowing the results now.',
                     'source': 'recommendation_results',
                     'confidence': 0.91,
                     'metadata': {'intent': 'product_search'},
                     'drift_detected': False,
                     'new_session_id': None,
                 },
             ) as recommendation_mock:
            response = self._post_chat(
                {
                    'message': 'SPF 50',
                    'session_id': session.session_id,
                    'assistant_mode': 'homepage_reco',
                },
                user=self.user,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reply'], 'SPF 50 noted. Narrowing the results now.')
        recommendation_mock.assert_called_once()

    def test_authenticated_homepage_reco_promotes_guest_preview_session_to_persistent(self):
        session = ConversationSession.objects.create(
            session_id='guest-preview-001',
            user=None,
            user_name='Guest',
            assistant_lane='inbox',
            assistant_mode='homepage_reco',
            is_persistent=False,
            current_state='chat_mode',
            context={},
        )

        with patch('assistant.processors.conversation_manager.QueryProcessor'), \
             patch('assistant.processors.conversation_manager.LocalModelAdapter.get_instance', return_value=Mock()), \
             patch(
                 'assistant.processors.conversation_manager.RecommendationService.evaluate_recommendation_message',
                 return_value={
                     'reply': 'Persistent session attached.',
                     'source': 'recommendation_results',
                     'confidence': 0.9,
                     'metadata': {'intent': 'product_search'},
                     'drift_detected': False,
                     'new_session_id': None,
                 },
             ):
            response = self._post_chat(
                {
                    'message': 'show me phones',
                    'session_id': session.session_id,
                    'assistant_mode': 'homepage_reco',
                },
                user=self.user,
            )

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.user_id, self.user.id)
        self.assertTrue(session.is_persistent)

    def test_anonymous_inbox_general_behavior_is_not_broken(self):
        with patch('assistant.processors.query_processor.QueryProcessor') as query_processor_cls:
            query_processor_cls.return_value.process.return_value = {
                'reply': 'Generic inbox response.',
                'source': 'query_processor',
                'confidence': 0.73,
                'metadata': {'intent': 'general_support'},
            }
            response = self._post_chat(
                {
                    'message': 'How do I reset my password?',
                    'assistant_mode': 'inbox_general',
                }
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['reply'], 'Generic inbox response.')
        self.assertEqual(payload['source'], 'query_processor')
        self.assertEqual(payload['state'], 'chat_mode')

    def test_inbox_general_dispute_routing_still_redirects_to_customer_service(self):
        dispute_intent = SimpleNamespace(value='issue')

        with patch('assistant.processors.conversation_manager.QueryProcessor'), \
             patch('assistant.processors.conversation_manager.LocalModelAdapter.get_instance', return_value=Mock()), \
             patch(
                 'assistant.processors.conversation_manager.ConversationManager._get_or_classify_intent',
                 return_value=(dispute_intent, 0.9, {'emotion': 'neutral'}),
             ):
            response = self._post_chat(
                {
                    'message': 'I need a refund for my order',
                    'assistant_mode': 'inbox_general',
                },
                user=self.user,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Customer Service', response.json()['reply'])

    def test_customer_service_mode_still_routes_dispute_messages(self):
        dispute_intent = SimpleNamespace(value='dispute')

        with patch('assistant.processors.conversation_manager.QueryProcessor'), \
             patch('assistant.processors.conversation_manager.LocalModelAdapter.get_instance', return_value=Mock()), \
             patch(
                 'assistant.processors.conversation_manager.ConversationManager._get_or_classify_intent',
                 return_value=(dispute_intent, 0.95, {'emotion': 'neutral'}),
             ), \
             patch(
                 'assistant.processors.conversation_manager.DisputeFlow.handle_dispute_message',
                 return_value=('Dispute flow response.', {'complete': False}),
             ):
            response = self._post_chat(
                {
                    'message': 'My order was not delivered',
                    'assistant_mode': 'customer_service',
                },
                user=self.user,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Dispute flow response.', response.json()['reply'])
