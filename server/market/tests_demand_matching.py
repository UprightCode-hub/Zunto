from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from assistant.models import RecommendationDemandGap
from market.models import Category, Location, Product
from notifications.models import Notification, NotificationPreference

User = get_user_model()
    

class ProductDemandMatchingSignalTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller-demand@example.com',
            password='TestPass123!',
            role='seller',
        )
        self.buyer = User.objects.create_user(
            email='buyer-demand@example.com',
            password='TestPass123!',
        )

        self.category = Category.objects.create(name='Phones')
        self.location = Location.objects.create(state='Lagos', city='Ikeja', area='Allen')

    @patch('assistant.services.demand_matching_service.send_mail')
    def test_product_create_matches_demand_and_notifies_once_per_user(self, mock_send_mail):
        RecommendationDemandGap.objects.create(
            user=self.buyer,
            requested_category='Phones',
            requested_attributes={'min_price': 100, 'max_price': 1000, 'brand': 'any'},
            user_location=str(self.location),
        )
        RecommendationDemandGap.objects.create(
            user=self.buyer,
            requested_category='Phones',
            requested_attributes={'brand': 'Samsung'},
            user_location=str(self.location),
        )

        product = Product.objects.create(
            seller=self.seller,
            title='Galaxy S23',
            description='Good phone',
            category=self.category,
            location=self.location,
            price=550,
            listing_type='product',
            condition='good',
            brand='Samsung',
            status='active',
        )

        self.assertEqual(Notification.objects.filter(user=self.buyer, type='product').count(), 1)
        notification = Notification.objects.get(user=self.buyer, type='product')
        self.assertEqual(notification.title, 'Product Now Available')
        self.assertEqual(notification.related_url, f'/products/{product.slug}/')
        mock_send_mail.assert_called_once()

    @patch('assistant.services.demand_matching_service.send_mail')
    def test_notification_respects_preference(self, mock_send_mail):
        prefs = NotificationPreference.objects.get(user=self.buyer)
        prefs.email_promotional = False
        prefs.save(update_fields=['email_promotional'])

        RecommendationDemandGap.objects.create(
            user=self.buyer,
            requested_category='Phones',
            requested_attributes={},
            user_location='',
        )

        Product.objects.create(
            seller=self.seller,
            title='Pixel 8',
            description='Another phone',
            category=self.category,
            location=self.location,
            price=650,
            listing_type='product',
            condition='good',
            brand='Google',
            status='active',
        )

        self.assertFalse(Notification.objects.filter(user=self.buyer, type='product').exists())
        mock_send_mail.assert_not_called()

    def test_category_and_location_must_match(self):
        RecommendationDemandGap.objects.create(
            user=self.buyer,
            requested_category='Laptops',
            requested_attributes={},
            user_location=str(self.location),
        )

        Product.objects.create(
            seller=self.seller,
            title='iPhone 14',
            description='Phone listing',
            category=self.category,
            location=self.location,
            price=700,
            listing_type='product',
            condition='good',
            brand='Apple',
            status='active',
        )

        self.assertFalse(Notification.objects.filter(user=self.buyer, type='product').exists())
