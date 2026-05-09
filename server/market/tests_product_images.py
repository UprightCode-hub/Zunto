from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from market.demo_image_urls import existing_image_url_or_blank, image_url_for_product, tags_for_category
from market.product_images import build_product_image_query, ensure_product_image_locked


class DemoImageUrlTests(SimpleTestCase):
    def test_loremflickr_url_uses_all_tags_and_product_lock(self):
        self.assertEqual(
            image_url_for_product(
                category='Phones',
                product_identifier='iphone-15-pro',
            ),
            'https://loremflickr.com/400/400/electronics,smartphone/all?lock=iphone-15-pro',
        )

    def test_category_mapping_uses_broad_demo_tags(self):
        self.assertEqual(tags_for_category('Rice & Grains'), 'food,market')
        self.assertEqual(tags_for_category('Skincare'), 'beauty,cosmetics')
        self.assertEqual(tags_for_category('Unknown Demo Category'), 'product,shopping')
        self.assertEqual(tags_for_category('Headphones Premium', 'Headphones Premium'), 'electronics,gadget')
        self.assertEqual(tags_for_category('iPhones Premium', 'iPhones Premium'), 'electronics,smartphone')

    def test_existing_unsplash_url_is_treated_as_blank(self):
        self.assertEqual(
            existing_image_url_or_blank('https://source.unsplash.com/400x400/?smartphone'),
            '',
        )


class ProductImageLockingTests(SimpleTestCase):
    def test_query_keeps_model_numbers_and_variants(self):
        product = SimpleNamespace(
            title='Wholesale Cheap iPhone 16 Pro Max 256GB Best Sale',
            brand='',
            product_family=None,
            category=None,
        )

        self.assertEqual(
            build_product_image_query(product),
            'iphone 16 pro max 256gb',
        )

    def test_existing_locked_image_is_never_regenerated(self):
        product = SimpleNamespace(
            image_url_locked='/media/public/product_locked_images/fixed.jpg',
        )

        with patch('market.product_images.fetch_image_candidates') as fetch:
            self.assertEqual(
                ensure_product_image_locked(product),
                '/media/public/product_locked_images/fixed.jpg',
            )

        fetch.assert_not_called()
