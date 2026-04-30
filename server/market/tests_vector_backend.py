from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from market.models import Category, Location, Product
from market.search.embeddings import search_similar_products
from market.search.vector_backend import (
    PRODUCT_VECTOR_LANE,
    product_vector_backend_status,
)

User = get_user_model()


class ProductVectorBackendTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='vector-seller@example.com',
            password='pass1234',
            role='seller',
        )
        self.category = Category.objects.create(name='Phones')
        self.location = Location.objects.create(state='Lagos', city='Ikeja')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Vector Test iPhone',
            description='Phone for vector backend tests',
            category=self.category,
            location=self.location,
            price=200000,
            quantity=3,
            condition='fair',
            status='active',
            embedding_vector=[0.1, 0.2, 0.3],
        )

    @override_settings(PRODUCT_VECTOR_BACKEND='auto')
    def test_auto_backend_falls_back_to_json_cosine_on_sqlite(self):
        status = product_vector_backend_status()

        self.assertEqual(status.backend, 'json_cosine')
        self.assertTrue(status.ready)
        self.assertEqual(status.lane, PRODUCT_VECTOR_LANE)
        self.assertIn('fallback', status.reason)

    @override_settings(PRODUCT_VECTOR_BACKEND='sqlite_vec')
    def test_sqlite_vec_backend_falls_back_when_extension_missing(self):
        status = product_vector_backend_status()

        self.assertEqual(status.backend, 'sqlite_vec')
        self.assertFalse(status.ready)
        self.assertIn('unavailable', status.reason)

    def test_search_uses_configured_vector_backend_results_when_available(self):
        with patch('market.search.embeddings._encode_single', return_value=[0.1, 0.2, 0.3]), \
             patch('market.search.embeddings.search_product_vectors', return_value=[
                 (str(self.product.id), 0.88),
             ]) as vector_search:
            results = search_similar_products(
                'iphone',
                Product.objects.filter(status='active'),
                top_k=5,
            )

        self.assertEqual(results, [(str(self.product.id), 0.88)])
        vector_search.assert_called_once()
