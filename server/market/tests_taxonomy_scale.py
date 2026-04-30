from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from market.models import Category, Product, ProductAttributeSchema, ProductFamily
from market.services.attribute_extractor import suggest_product_metadata
from market.taxonomy_seed import (
    SCALE_DATASET_LABEL,
    seed_taxonomy_scale_catalog,
)

User = get_user_model()


class ProductAttributeSuggestionTests(TestCase):
    def setUp(self):
        self.top = Category.objects.create(name='Phones & Tablets')
        self.sub = Category.objects.create(name='iPhones', parent=self.top)
        self.family = ProductFamily.objects.create(
            name='iPhones Premium',
            top_category=self.top,
            subcategory=self.sub,
            aliases=['iphone', 'apple phone'],
            keywords=['smartphone', 'ios'],
        )
        ProductAttributeSchema.objects.create(
            product_family=self.family,
            key='storage',
            label='Storage',
            value_type='select',
            required=True,
            order=1,
        )
        ProductAttributeSchema.objects.create(
            product_family=self.family,
            key='battery_health',
            label='Battery health',
            value_type='number',
            required=False,
            order=2,
        )

    def test_extractor_suggests_family_attributes_and_tags(self):
        suggestion = suggest_product_metadata(
            title='Apple iPhone 13 Pro 256GB',
            description='Clean unlocked phone with battery health 88%.',
            product_family=self.family,
            brand='Apple',
        )

        self.assertEqual(suggestion['product_family']['name'], 'iPhones Premium')
        self.assertEqual(suggestion['attributes']['storage'].lower(), '256gb')
        self.assertEqual(suggestion['attributes']['battery_health'], '88%')
        self.assertIn('iphone', suggestion['search_tags'])
        self.assertEqual(suggestion['missing_required'], [])

    def test_suggestion_endpoint_returns_metadata(self):
        user = User.objects.create_user(
            email='seller@example.com',
            password='pass1234',
            role='seller',
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post('/api/market/products/suggest-metadata/', {
            'title': 'Apple iPhone 13 Pro 256GB',
            'description': 'Battery health 88%, unlocked network.',
            'product_family': str(self.family.id),
            'brand': 'Apple',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['product_family']['name'], 'iPhones Premium')
        self.assertIn('storage', response.data['attributes'])
        self.assertTrue(response.data['search_tags'])


class TaxonomyScaleSeedTests(TestCase):
    def test_scale_seed_creates_expected_taxonomy_and_products(self):
        summary = seed_taxonomy_scale_catalog(
            product_count=40,
            seller_count=4,
            rebuild_embeddings=False,
        )

        self.assertEqual(summary['top_categories'], 20)
        self.assertEqual(summary['subcategories'], 250)
        self.assertEqual(summary['product_families'], 1500)
        self.assertGreaterEqual(summary['attribute_schemas'], 15000)
        self.assertEqual(summary['products'], 40)
        self.assertEqual(summary['sellers'], 4)

        product = Product.objects.filter(
            attributes__dataset_label=SCALE_DATASET_LABEL,
            product_family__isnull=False,
        ).first()
        self.assertIsNotNone(product)
        self.assertTrue(product.search_tags)
        self.assertTrue(product.attributes.get('product_family'))
        self.assertTrue(product.attributes.get('taxonomy_path'))

    def test_scale_seed_command_reports_summary(self):
        output = StringIO()
        call_command(
            'seed_taxonomy_scale_catalog',
            '--products',
            '12',
            '--sellers',
            '3',
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn('Scale taxonomy seed complete.', value)
        self.assertIn('Top categories: 20', value)
        self.assertIn('Product families: 1500', value)
