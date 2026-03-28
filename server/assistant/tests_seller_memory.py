from django.test import TestCase

from accounts.models import SellerProfile, User
from assistant.services.seller_memory_service import SellerMemoryService


class SellerMemoryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='seller@example.com',
            password='pass12345',
            first_name='Ada',
            last_name='Seller',
            role='seller',
            is_seller=True,
        )
        self.profile = SellerProfile.objects.create(
            user=self.user,
            status=SellerProfile.STATUS_APPROVED,
            is_verified_seller=True,
        )

    def test_update_from_conversation_updates_memory(self):
        ok = SellerMemoryService.update_from_conversation(
            user=self.user,
            user_message='Abeg help me sell more phones, quick reply pls',
            assistant_reply='Sure, I can keep it short and casual.',
        )
        self.assertTrue(ok)
        self.profile.refresh_from_db()
        memory = self.profile.ai_memory
        self.assertEqual(memory.get('preferred_language'), 'pidgin')
        self.assertIn(memory.get('tone_preference'), {'casual', 'formal', 'neutral'})
        self.assertIn('phone', memory.get('product_specialization', []))
        self.assertIn('increase_sales', memory.get('seller_goals', []))
        self.assertFalse(memory.get('manually_reviewed'))

    def test_update_from_conversation_no_crash_for_non_seller(self):
        buyer = User.objects.create_user(
            email='buyer@example.com',
            password='pass12345',
            first_name='Bisi',
            last_name='Buyer',
            role='buyer',
        )
        ok = SellerMemoryService.update_from_conversation(
            user=buyer,
            user_message='hello',
            assistant_reply='hi',
        )
        self.assertFalse(ok)
