from django.contrib.auth import get_user_model
from django.test import TestCase

from assistant.models import ConversationSession, RecommendationDemandGap, UserBehaviorProfile
from assistant.services.recommendation_service import RecommendationService
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
        self.location = Location.objects.create(state='Lagos', city='Ikeja')
        self.product = Product.objects.create(
            seller=self.seller,
            title='iPhone 12',
            description='Good phone',
            category=self.cat_phone,
            location=self.location,
            price=500000,
            quantity=3,
            status='active',
        )

    def _new_session(self):
        return ConversationSession.objects.create(
            session_id='sess-1',
            user=self.user,
            user_name='Buyer One',
            assistant_mode='homepage_reco',
            current_state='chat_mode',
            context={},
        )

    def test_constraint_extraction_is_structured(self):
        extracted = RecommendationService.extract_constraints('I need phones under 600000 in lagos size: 6inch color: black')
        self.assertIn('category', extracted)
        self.assertIn('budget_range', extracted)
        self.assertEqual(extracted['category'], 'Phones')
        self.assertEqual(extracted['location'], 'Lagos')
        self.assertEqual(extracted['attributes'].get('color'), 'black')

    def test_context_drift_requires_confirmation_and_creates_new_session(self):
        session = self._new_session()
        RecommendationService.evaluate_recommendation_message(session, 'Show me phones under 600000')
        session.refresh_from_db()
        self.assertEqual(session.constraint_state.get('category'), 'Phones')

        drift = RecommendationService.evaluate_recommendation_message(session, 'Now I want shoes')
        self.assertTrue(drift['drift_detected'])

        switched = RecommendationService.evaluate_recommendation_message(session, 'yes')
        self.assertIsNotNone(switched['new_session_id'])
        self.assertNotEqual(switched['new_session_id'], session.session_id)
        session.refresh_from_db()
        self.assertIsNotNone(session.completed_at)

    def test_demand_gap_logging_increments_frequency(self):
        session = self._new_session()
        constraints = {'category': 'Tractors', 'attributes': {'brand': 'X'}, 'location': 'Abuja'}
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
