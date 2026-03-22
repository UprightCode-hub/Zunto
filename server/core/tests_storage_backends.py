from django.test import SimpleTestCase, override_settings

from core.storage_backends import PublicMediaStorage


@override_settings(
    USE_OBJECT_STORAGE=False,
    MEDIA_ROOT='C:/tmp/zunto-media',
    MEDIA_URL='/media/',
)
class PublicMediaStorageTests(SimpleTestCase):
    def test_url_strips_duplicate_location_prefix(self):
        storage = PublicMediaStorage()

        url = storage.url('public/products/2026/03/example.jpg')

        self.assertNotIn('/public/public/', url)
        self.assertTrue(url.endswith('/public/products/2026/03/example.jpg'))

    def test_url_keeps_normalized_public_path(self):
        storage = PublicMediaStorage()

        url = storage.url('products/2026/03/example.jpg')

        self.assertNotIn('/public/public/', url)
        self.assertTrue(url.endswith('/public/products/2026/03/example.jpg'))
