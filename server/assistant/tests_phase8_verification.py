from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import SellerProfile
from assistant.models import ConversationSession
from assistant.processors.query_processor import QueryProcessor
from assistant.services.recommendation_service import RecommendationService
from assistant.services.seller_memory_service import SellerMemoryService
from assistant.views import _handle_ephemeral_chat
from market.models import Category, Location, Product


User = get_user_model()


class Phase8VerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='phase8-buyer@example.com',
            password='pass1234',
            first_name='Phase',
            last_name='Buyer',
            role='buyer',
        )
        self.seller = User.objects.create_user(
            email='phase8-seller@example.com',
            password='pass1234',
            first_name='Phase',
            last_name='Seller',
            role='seller',
            is_seller=True,
        )
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller,
            status=SellerProfile.STATUS_APPROVED,
            is_verified_seller=True,
        )
        self.category = Category.objects.create(name='Gifts')
        self.location = Location.objects.create(state='Lagos', city='Ikeja')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Birthday Gift Box',
            description='Lovely gift package',
            category=self.category,
            location=self.location,
            price=50000,
            quantity=5,
            condition='new',
            status='active',
        )

    def _reco_session(self):
        return ConversationSession.objects.create(
            session_id='phase8-reco-session',
            user=self.user,
            user_name='Phase Buyer',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
        )

    def test_scenario_1_smalltalk_interception(self):
        processor = QueryProcessor()
        result = processor.process('how are you doing', assistant_mode='inbox_general')
        self.assertEqual(result['source'], 'intent_smalltalk')
        self.assertLessEqual(len([s for s in result['reply'].split('.') if s.strip()]), 2)

    def test_scenario_2_faq_hit(self):
        processor = QueryProcessor()
        result = processor.process('How do I track my order?', assistant_mode='inbox_general')
        self.assertIsNotNone(result.get('faq_hit'))
        self.assertGreaterEqual(result.get('faq_hit', {}).get('score', 0.0), 0.5)
        self.assertTrue(all(v is not None for v in result['faq_hit'].values()))

    @patch('assistant.services.recommendation_service.enrich_slots')
    @patch.object(RecommendationService, '_find_products')
    def test_scenario_3_natural_language_recommendation(self, find_products_mock, enrich_mock):
        session = self._reco_session()
        enrich_mock.return_value = {
            'occasion': 'birthday',
            'recipient': 'wife',
            'price_max': 50000,
            'condition': 'new',
        }
        find_products_mock.return_value = [self.product]

        result = RecommendationService.evaluate_recommendation_message(
            session,
            "something for my wife's birthday under 50k",
        )
        if result.get('source') == 'recommendation_confirmation':
            result = RecommendationService.evaluate_recommendation_message(session, 'yes')
        session.refresh_from_db()
        self.assertIn(result['source'], {'recommendation_results', 'recommendation_results_alternatives'})
        self.assertEqual(session.context_data.get('last_llm_enrichment', {}).get('occasion'), 'birthday')
        self.assertEqual(session.constraint_state.get('price_max'), 50000.0)

    @patch.object(RecommendationService, '_find_products')
    def test_scenario_4_forced_search(self, find_products_mock):
        session = self._reco_session()
        find_products_mock.return_value = [self.product]
        result = RecommendationService.evaluate_recommendation_message(session, 'just show me anything')
        self.assertIn("throwing darts in the dark", result['reply'])
        self.assertIn(result['source'], {'recommendation_results', 'recommendation_results_alternatives'})

    def test_scenario_5_login_gate_logged_out(self):
        payload = _handle_ephemeral_chat('i need a phone under 200k', 'homepage_reco', 'inbox')
        self.assertEqual(payload.get('state'), 'login_required')
        self.assertTrue(payload.get('login_required'))
        self.assertNotIn('Here are top', payload.get('reply', ''))

    def test_scenario_7_seller_memory(self):
        ok = SellerMemoryService.update_from_conversation(
            self.seller,
            'abeg help me write better product descriptions',
            'sure',
        )
        self.assertTrue(ok)
        self.seller_profile.refresh_from_db()
        self.assertEqual(self.seller_profile.ai_memory.get('tone_preference'), 'casual')
        self.assertEqual(self.seller_profile.ai_memory.get('preferred_language'), 'pidgin')

    @patch('assistant.processors.query_processor.QueryProcessor._check_rules')
    @patch('assistant.processors.query_processor.LocalModelAdapter.get_instance')
    def test_scenario_8_llm_failure_fallback(self, adapter_get_instance_mock, check_rules_mock):
        check_rules_mock.return_value = {'matched': False}

        class StubAdapter:
            model_name = 'stub'

            @staticmethod
            def is_available():
                return False

            @staticmethod
            def generate(*args, **kwargs):
                return {'response': 'fallback'}

        adapter_get_instance_mock.return_value = StubAdapter()
        processor = QueryProcessor()
        result = processor.process('show me available options', assistant_mode='inbox_general')
        self.assertIsInstance(result.get('reply'), str)
        self.assertIn(result.get('source'), {'rag_fallback', 'error_fallback', 'llm'})


class Phase8SessionReplayVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='phase8-replay@example.com',
            password='pass1234',
            first_name='Replay',
            last_name='User',
            role='buyer',
        )
        self.client.force_authenticate(user=self.user)

    @patch('assistant.views.ConversationManager')
    @patch('assistant.views._log_conversation')
    @patch('assistant.views.audit_event')
    def test_scenario_6_post_login_resume_slot_merge(self, _audit_event, _log_conversation, manager_mock):
        session = ConversationSession.objects.create(
            session_id='phase8-replay-session',
            user=self.user,
            user_name='Replay User',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
            constraint_state={'condition': 'used'},
            intent_state={'last_intent': 'product_search'},
        )

        manager = manager_mock.return_value
        manager.session = session
        manager.get_current_state.return_value = 'chat_mode'
        manager.process_message.return_value = 'done'
        manager.get_conversation_summary.return_value = {
            'satisfaction_score': 0.9,
            'message_count': 1,
            'sentiment': 'neutral',
            'escalation_level': 0,
            'user_name': 'Replay User',
        }
        manager.context_mgr.is_escalated.return_value = False
        manager.get_user_name.return_value = 'Replay User'

        response = self.client.post(
            '/assistant/api/chat/',
            {
                'message': 'show me options',
                'session_id': session.session_id,
                'assistant_mode': 'homepage_reco',
                'pre_collected_slots': {'product_type': 'phone', 'price_max': 200000, 'condition': None},
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.constraint_state.get('product_type'), 'phone')
        self.assertEqual(session.constraint_state.get('price_max'), 200000)
        self.assertEqual(session.constraint_state.get('condition'), 'used')
