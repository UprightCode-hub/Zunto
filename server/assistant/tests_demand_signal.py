from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assistant.models import DemandCluster, RecommendationDemandGap
from assistant.services.demand_signal_service import RANKING_MULTIPLIER
from market.models import Category, Location, Product
from market.views import _apply_feed_personalization
from notifications.models import Notification

User = get_user_model()


class DemandSignalEngineTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(email='seller-hot@example.com', password='TestPass123!', role='seller')
        self.buyer = User.objects.create_user(email='buyer-hot@example.com', password='TestPass123!')
        self.other = User.objects.create_user(email='other-hot@example.com', password='TestPass123!')
        self.category = Category.objects.create(name='Laptops')
        self.location = Location.objects.create(state='Lagos', city='Ikeja', area='Allen')

        self.product = Product.objects.create(
            seller=self.seller,
            title='Seller Laptop',
            description='In-demand laptop',
            category=self.category,
            location=self.location,
            price=500,
            status='active',
        )

    def _create_gap(self, seed, user=None):
        return RecommendationDemandGap.objects.create(
            user=user or self.buyer,
            requested_category='Laptops',
            requested_attributes={'seed': seed},
            user_location=str(self.location),
        )

    def test_cluster_creation_and_hot_transition_notifies_seller_once(self):
        buyers = [
            User.objects.create_user(email=f'buyer-hot-{idx}@example.com', password='TestPass123!')
            for idx in range(5)
        ]
        for idx, buyer in enumerate(buyers):
            self._create_gap(idx, user=buyer)

        cluster = DemandCluster.objects.get(category=self.category, location=self.location)
        self.assertEqual(cluster.demand_count, 5)
        self.assertTrue(cluster.is_hot)

        notifications = Notification.objects.filter(user=self.seller, type='hot_demand')
        self.assertEqual(notifications.count(), 1)
        notification = notifications.first()
        self.assertIn('High Buyer Demand Detected', notification.title)
        self.assertEqual(notification.related_url, f'/seller/dashboard?hot={self.category.slug}')

        self._create_gap(99)
        self.assertEqual(Notification.objects.filter(user=self.seller, type='hot_demand').count(), 1)

    def test_hot_endpoint_returns_top5_by_score(self):
        for n in range(1, 7):
            cat = Category.objects.create(name=f'Cat {n}')
            DemandCluster.objects.create(
                category=cat,
                location=self.location,
                demand_count=10 + n,
                hot_score=float(n),
                is_hot=True,
            )

        url = reverse('hot_demand_clusters_api')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 5)
        self.assertGreaterEqual(response.json()[0]['hot_score'], response.json()[1]['hot_score'])

    def test_ranking_boost_hook_prioritizes_hot_category(self):
        hot_category = Category.objects.create(name='Phones')
        hot_product = Product.objects.create(
            seller=self.seller,
            title='Hot Phone',
            description='Hot category listing',
            category=hot_category,
            location=self.location,
            price=100,
            status='active',
        )
        normal_product = Product.objects.create(
            seller=self.other,
            title='Normal Laptop',
            description='Normal category listing',
            category=self.category,
            location=self.location,
            price=100,
            status='active',
        )
        DemandCluster.objects.create(
            category=hot_category,
            location=self.location,
            demand_count=9,
            hot_score=12.0,
            is_hot=True,
        )

        request = self.client.get('/market/api/products/').wsgi_request
        ordered = _apply_feed_personalization(request, [normal_product, hot_product])

        self.assertEqual(ordered[0].id, hot_product.id)
        self.assertGreaterEqual(RANKING_MULTIPLIER, 1.0)
