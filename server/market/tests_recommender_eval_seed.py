from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from market.models import Category, Location, Product, ProductImage
from market.recommender_eval_seed import (
    DATASET_LABEL,
    audit_product_recommendation_quality,
    run_seeded_recommender_evals,
    seeded_product_queryset,
)

User = get_user_model()


class RecommenderEvalSeedTests(TestCase):
    def _seed(self):
        with patch(
            'market.recommender_eval_seed.generate_product_embedding',
            return_value=[0.1, 0.2, 0.3],
        ):
            call_command('seed_recommender_eval_products', stdout=StringIO())

    def _create_foreign_iphone(self):
        seller = User.objects.create_user(
            email='outside-catalog@example.com',
            password='pass1234',
            role='seller',
        )
        category, _ = Category.objects.get_or_create(name='Phones')
        location, _ = Location.objects.get_or_create(state='Lagos', city='Ikeja')
        return Product.objects.create(
            seller=seller,
            title='Outside Catalog iPhone Budget',
            description='Non-labeled iPhone that must not appear in seeded evals.',
            category=category,
            location=location,
            price=50000,
            quantity=5,
            condition='fair',
            status='active',
        )

    def test_seed_command_is_idempotent_and_structured(self):
        self._seed()
        first_product_count = seeded_product_queryset().count()
        first_image_count = ProductImage.objects.filter(product__in=seeded_product_queryset()).count()

        self._seed()

        self.assertEqual(seeded_product_queryset().count(), first_product_count)
        self.assertEqual(
            ProductImage.objects.filter(product__in=seeded_product_queryset()).count(),
            first_image_count,
        )

        sample = Product.objects.get(attributes__eval_key='iphone_11_budget_lagos')
        self.assertEqual(sample.attributes['dataset_label'], DATASET_LABEL)
        self.assertTrue(sample.attributes['fake_demo_data'])
        self.assertTrue(sample.attributes['product_family'])
        self.assertTrue(sample.attributes['tags'])
        self.assertTrue(sample.attributes_verified)
        self.assertTrue(sample.is_verified_product)
        self.assertTrue(sample.images.exists())
        self.assertEqual(sample.embedding_vector, [0.1, 0.2, 0.3])

        audit = audit_product_recommendation_quality(seeded_product_queryset().filter(status='active'))
        self.assertGreaterEqual(audit['coverage']['category']['percent'], 90)
        self.assertGreaterEqual(audit['coverage']['product_family']['percent'], 90)
        self.assertGreaterEqual(audit['coverage']['tags']['percent'], 90)
        self.assertGreaterEqual(audit['coverage']['images']['percent'], 90)
        self.assertGreaterEqual(audit['coverage']['embeddings']['percent'], 90)

    @override_settings(DEBUG=False, TESTING=False)
    def test_seed_command_refuses_non_debug_by_default(self):
        with self.assertRaises(CommandError):
            call_command('seed_recommender_eval_products', stdout=StringIO())

    def test_seeded_catalog_supports_recommender_eval_cases(self):
        self._seed()

        def semantic_results(_query, queryset, candidate_limit=250, top_k=80):
            ids = list(queryset.order_by('price', 'title').values_list('id', flat=True)[:top_k])
            return [(product_id, 0.99 - index * 0.01) for index, product_id in enumerate(ids)]

        with patch(
            'assistant.services.recommendation_service.search_similar_products',
            side_effect=semantic_results,
        ):
            report = run_seeded_recommender_evals()

        self.assertEqual(report['failed'], 0, report)
        self.assertEqual(report['passed'], report['total'])
        self.assertEqual(report['remaining_gaps'], [])
        self.assertFalse(any(
            result['foreign_results']
            for result in report['results']
        ))

    def test_seeded_evals_ignore_non_labeled_catalog_products(self):
        self._seed()
        self._create_foreign_iphone()

        def semantic_results(_query, queryset, candidate_limit=250, top_k=80):
            ids = list(queryset.order_by('price', 'title').values_list('id', flat=True)[:top_k])
            return [(product_id, 0.99 - index * 0.01) for index, product_id in enumerate(ids)]

        with patch(
            'assistant.services.recommendation_service.search_similar_products',
            side_effect=semantic_results,
        ):
            report = run_seeded_recommender_evals()

        self.assertEqual(report['failed'], 0, report)
        self.assertEqual(report['remaining_gaps'], [])
        self.assertFalse(any(
            product['title'] == 'Outside Catalog iPhone Budget'
            for result in report['results']
            for product in result['results']
        ))

    def test_eval_command_reports_seeded_results(self):
        self._seed()

        def semantic_results(_query, queryset, candidate_limit=250, top_k=80):
            ids = list(queryset.order_by('price', 'title').values_list('id', flat=True)[:top_k])
            return [(product_id, 0.99 - index * 0.01) for index, product_id in enumerate(ids)]

        with patch(
            'assistant.services.recommendation_service.search_similar_products',
            side_effect=semantic_results,
        ):
            output = StringIO()
            call_command('eval_recommender_seed', stdout=output)

        self.assertIn('Seeded recommender evals:', output.getvalue())
