#server/market/tests.py
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from .models import Category, Product, ProductReport, ProductVideo


User = get_user_model()


class SellerPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.buyer = User.objects.create_user(
            email='buyer-market@example.com',
            password='TestPass123!',
            first_name='Buyer',
            last_name='User',
            role='buyer',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            email='seller-market@example.com',
            password='TestPass123!',
            first_name='Seller',
            last_name='User',
            role='seller',
            is_verified=True,
        )
        self.admin_role_user = User.objects.create_user(
            email='admin-role-market@example.com',
            password='TestPass123!',
            first_name='Admin',
            last_name='Role',
            role='admin',
            is_verified=True,
        )
        self.category = Category.objects.create(name='Accessories')

    def test_buyer_cannot_create_product_listing(self):
        self.client.force_authenticate(user=self.buyer)
        payload = {
            'title': 'Restricted listing',
            'description': 'Only sellers should create this',
            'listing_type': 'product',
            'price': '15.00',
            'quantity': 2,
            'condition': 'new',
            'status': 'active',
            'category': str(self.category.id),
        }
        response = self.client.post('/api/market/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_seller_can_create_product_listing(self):
        self.client.force_authenticate(user=self.seller)
        payload = {
            'title': 'Seller listing',
            'description': 'Valid seller listing',
            'listing_type': 'product',
            'price': '25.00',
            'quantity': 3,
            'condition': 'new',
            'status': 'active',
            'category': str(self.category.id),
        }
        response = self.client.post('/api/market/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Product.objects.filter(title='Seller listing', seller=self.seller).exists())


    def test_admin_role_can_create_product_listing(self):
        self.client.force_authenticate(user=self.admin_role_user)
        payload = {
            'title': 'Admin created listing',
            'description': 'Admin override listing',
            'listing_type': 'product',
            'price': '45.00',
            'quantity': 1,
            'condition': 'new',
            'status': 'active',
            'category': str(self.category.id),
        }
        response = self.client.post('/api/market/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_product_view_deduplicates_within_window(self):
        product = Product.objects.create(
            seller=self.seller,
            title='View-tracked product',
            description='View dedupe check',
            listing_type='product',
            price=Decimal('55.00'),
            quantity=2,
            condition='new',
            status='active',
            category=self.category,
        )

        self.client.force_authenticate(user=self.buyer)
        detail_url = f'/api/market/products/{product.slug}/'

        first = self.client.get(detail_url)
        second = self.client.get(detail_url)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)

        product.refresh_from_db()
        self.assertEqual(product.views_count, 1)


    def test_favorite_toggle_updates_counter_atomically(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Favorite tracked product',
            description='Favorite counter check',
            listing_type='product',
            price=Decimal('35.00'),
            quantity=2,
            condition='new',
            status='active',
            category=self.category,
        )

        self.client.force_authenticate(user=self.buyer)
        toggle_url = f'/api/market/products/{product.slug}/favorite/'

        first = self.client.post(toggle_url)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data.get('favorites_count'), 1)

        second = self.client.post(toggle_url)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data.get('favorites_count'), 0)

        product.refresh_from_db()
        self.assertEqual(product.favorites_count, 0)


    def test_product_stats_cache_invalidated_after_favorite_toggle(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Stats cache product',
            description='Stats invalidation check',
            listing_type='product',
            price=Decimal('65.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )

        self.client.force_authenticate(user=self.seller)
        stats_url = f'/api/market/products/{product.slug}/stats/'
        initial = self.client.get(stats_url)
        self.assertEqual(initial.status_code, status.HTTP_200_OK)
        self.assertEqual(initial.data.get('favorites_count'), 0)

        self.client.force_authenticate(user=self.buyer)
        toggle_url = f'/api/market/products/{product.slug}/favorite/'
        toggle = self.client.post(toggle_url)
        self.assertEqual(toggle.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.seller)
        refreshed = self.client.get(stats_url)
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertEqual(refreshed.data.get('favorites_count'), 1)


    def test_admin_role_can_moderate_product_report(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Reported product',
            description='Needs moderation',
            listing_type='product',
            price=Decimal('80.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )
        report = ProductReport.objects.create(
            product=product,
            reporter=self.buyer,
            reason='spam',
            description='Spam listing',
            status='pending',
        )

        self.client.force_authenticate(user=self.admin_role_user)
        response = self.client.patch(
            f'/api/market/reports/moderation/{report.id}/',
            {'status': 'reviewing', 'admin_notes': 'Investigating'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, 'reviewing')
        self.assertEqual(report.admin_notes, 'Investigating')
        self.assertEqual(report.moderated_by, self.admin_role_user)

    def test_buyer_cannot_access_report_moderation(self):
        self.client.force_authenticate(user=self.buyer)
        response = self.client.get('/api/market/reports/moderation/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_report_status_transition_is_rejected(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Report transition product',
            description='Transition guard',
            listing_type='product',
            price=Decimal('70.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )
        report = ProductReport.objects.create(
            product=product,
            reporter=self.buyer,
            reason='fraud',
            description='Suspicious listing',
            status='pending',
        )

        self.client.force_authenticate(user=self.admin_role_user)
        first = self.client.patch(
            f'/api/market/reports/moderation/{report.id}/',
            {'status': 'resolved'},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.patch(
            f'/api/market/reports/moderation/{report.id}/',
            {'status': 'reviewing'},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)


    def test_product_detail_excludes_non_clean_videos(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Video visibility product',
            description='Video scan visibility check',
            listing_type='product',
            price=Decimal('99.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )

        clean_file = SimpleUploadedFile('clean.webm', b'\x1aE\xdf\xa3clean-video', content_type='video/webm')
        pending_file = SimpleUploadedFile('pending.webm', b'\x1aE\xdf\xa3pending-video', content_type='video/webm')

        ProductVideo.objects.create(
            product=product,
            video=clean_file,
            security_scan_status=ProductVideo.SCAN_CLEAN,
        )
        ProductVideo.objects.create(
            product=product,
            video=pending_file,
            security_scan_status=ProductVideo.SCAN_PENDING,
        )

        self.client.force_authenticate(user=self.buyer)
        response = self.client.get(f'/api/market/products/{product.slug}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        videos = response.data.get('videos', [])
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0].get('security_scan_status'), ProductVideo.SCAN_CLEAN)


    @patch('market.tasks.schedule_product_video_scan')
    def test_video_upload_marks_pending_and_enqueues_scan_task(self, schedule_mock):
        product = Product.objects.create(
            seller=self.seller,
            title='Video upload product',
            description='Video upload async scan check',
            listing_type='product',
            price=Decimal('101.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )

        self.client.force_authenticate(user=self.seller)
        video_file = SimpleUploadedFile('upload.webm', b'\x1aE\xdf\xa3video-content', content_type='video/webm')

        response = self.client.post(
            f'/api/market/products/{product.slug}/videos/',
            {'video': video_file, 'caption': 'upload'},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_video = ProductVideo.objects.get(id=response.data['id'])
        self.assertEqual(created_video.security_scan_status, ProductVideo.SCAN_PENDING)
        schedule_mock.assert_called_once_with(str(created_video.id))


    def test_admin_can_list_video_scan_moderation_queue(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Video queue product',
            description='Video queue',
            listing_type='product',
            price=Decimal('22.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )
        video_file = SimpleUploadedFile('queue.webm', b'\x1aE\xdf\xa3queue-video', content_type='video/webm')
        ProductVideo.objects.create(
            product=product,
            video=video_file,
            security_scan_status=ProductVideo.SCAN_QUARANTINED,
            security_scan_reason='eicar-detected',
        )

        self.client.force_authenticate(user=self.admin_role_user)
        response = self.client.get('/api/market/videos/moderation/?status=quarantined')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data.get('results', response.data)
        self.assertGreaterEqual(len(payload), 1)
        self.assertEqual(payload[0].get('security_scan_status'), ProductVideo.SCAN_QUARANTINED)


    def test_admin_can_mark_quarantined_video_clean(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Video release product',
            description='Video release',
            listing_type='product',
            price=Decimal('23.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )
        video_file = SimpleUploadedFile('release.webm', b'\x1aE\xdf\xa3release-video', content_type='video/webm')
        video = ProductVideo.objects.create(
            product=product,
            video=video_file,
            security_scan_status=ProductVideo.SCAN_QUARANTINED,
            security_scan_reason='false-positive',
            security_quarantine_path='/tmp/quarantine/release.webm',
        )

        self.client.force_authenticate(user=self.admin_role_user)
        response = self.client.patch(
            f'/api/market/videos/moderation/{video.id}/',
            {'action': 'mark_clean', 'reason': 'Manual release after review'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        video.refresh_from_db()
        self.assertEqual(video.security_scan_status, ProductVideo.SCAN_CLEAN)
        self.assertEqual(video.security_quarantine_path, '')


    def test_buyer_cannot_moderate_video_scan(self):
        product = Product.objects.create(
            seller=self.seller,
            title='Video denied product',
            description='Video denied',
            listing_type='product',
            price=Decimal('24.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )
        video_file = SimpleUploadedFile('denied.webm', b'\x1aE\xdf\xa3denied-video', content_type='video/webm')
        video = ProductVideo.objects.create(
            product=product,
            video=video_file,
            security_scan_status=ProductVideo.SCAN_QUARANTINED,
        )

        self.client.force_authenticate(user=self.buyer)
        response = self.client.patch(
            f'/api/market/videos/moderation/{video.id}/',
            {'action': 'mark_clean'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    @override_settings(USE_OBJECT_STORAGE=True, OBJECT_STORAGE_BUCKET_NAME='bucket', OBJECT_STORAGE_REGION='auto', OBJECT_STORAGE_ENDPOINT_URL='https://example.com', OBJECT_STORAGE_ACCESS_KEY_ID='k', OBJECT_STORAGE_SECRET_ACCESS_KEY='s', OBJECT_UPLOAD_HMAC_SECRET='secret', OBJECT_UPLOAD_SIGNED_UPLOAD_EXP_SECONDS=900)
    @patch('boto3.client')
    def test_seller_can_request_direct_upload_ticket(self, boto_client_mock):
        product = Product.objects.create(
            seller=self.seller,
            title='Direct upload ticket product',
            description='Direct upload',
            listing_type='product',
            price=Decimal('88.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )

        mock_client = boto_client_mock.return_value
        mock_client.generate_presigned_post.return_value = {
            'url': 'https://example.com/bucket',
            'fields': {'key': 'products/videos/key.webm', 'Content-Type': 'video/webm'},
        }

        self.client.force_authenticate(user=self.seller)
        response = self.client.post(
            f'/api/market/products/{product.slug}/videos/direct-upload-ticket/',
            {'filename': 'clip.webm', 'content_type': 'video/webm'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('upload', response.data)
        self.assertIn('callback', response.data)


    @override_settings(USE_OBJECT_STORAGE=True, OBJECT_UPLOAD_HMAC_SECRET='secret')
    @patch('market.tasks.schedule_product_video_scan')
    def test_direct_upload_callback_verifies_signature_and_creates_pending_video(self, schedule_mock):
        product = Product.objects.create(
            seller=self.seller,
            title='Direct upload callback product',
            description='Direct upload callback',
            listing_type='product',
            price=Decimal('89.00'),
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )

        from market.views import _sign_upload_callback_payload
        import time

        payload = {
            'product_id': str(product.id),
            'product_slug': product.slug,
            'uploader_id': str(self.seller.id),
            'key': f'products/videos/{product.id}/uploaded.webm',
            'content_type': 'video/webm',
            'exp': int(time.time()) + 600,
        }
        signature = _sign_upload_callback_payload(payload)

        self.client.force_authenticate(user=self.seller)
        response = self.client.post(
            f'/api/market/products/{product.slug}/videos/direct-upload-callback/',
            {'payload': payload, 'signature': signature},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_video = ProductVideo.objects.get(id=response.data['id'])
        self.assertEqual(created_video.security_scan_status, ProductVideo.SCAN_PENDING)
        schedule_mock.assert_called_once_with(str(created_video.id))
