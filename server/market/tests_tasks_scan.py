from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import User
from market.models import Category, Product, ProductVideo
from market.tasks import scan_product_video_task


class ProductVideoScanLifecycleTaskTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller-video-scan@example.com',
            password='TestPass123!',
            role='seller',
            is_verified=True,
        )
        self.category = Category.objects.create(name='Video Scan Category')
        self.product = Product.objects.create(
            seller=self.seller,
            title='Video Scan Product',
            description='Video scan task tests',
            listing_type='product',
            price='40.00',
            quantity=1,
            condition='new',
            status='active',
            category=self.category,
        )

    @patch('market.tasks.scan_uploaded_file')
    def test_scan_task_marks_clean_when_scanner_returns_clean(self, scan_mock):
        class Result:
            is_clean = True
            reason = ''

        scan_mock.return_value = Result()
        video = ProductVideo.objects.create(
            product=self.product,
            video=SimpleUploadedFile('clean.webm', b'webm-clean', content_type='video/webm'),
            security_scan_status=ProductVideo.SCAN_PENDING,
        )

        result = scan_product_video_task(str(video.id))

        video.refresh_from_db()
        self.assertEqual(result['status'], 'clean')
        self.assertEqual(video.security_scan_status, ProductVideo.SCAN_CLEAN)
        self.assertIsNotNone(video.scanned_at)

    @patch('market.tasks.quarantine_uploaded_file')
    @patch('market.tasks.scan_uploaded_file')
    def test_scan_task_marks_quarantined_when_scanner_detects_malware(self, scan_mock, quarantine_mock):
        class Result:
            is_clean = False
            reason = 'malware-detected'

        scan_mock.return_value = Result()
        quarantine_mock.return_value = '/tmp/quarantine/bad.webm'
        video = ProductVideo.objects.create(
            product=self.product,
            video=SimpleUploadedFile('bad.webm', b'webm-bad', content_type='video/webm'),
            security_scan_status=ProductVideo.SCAN_PENDING,
        )

        result = scan_product_video_task(str(video.id))

        video.refresh_from_db()
        self.assertEqual(result['status'], 'quarantined')
        self.assertEqual(video.security_scan_status, ProductVideo.SCAN_QUARANTINED)
        self.assertEqual(video.security_quarantine_path, '/tmp/quarantine/bad.webm')
        self.assertIsNotNone(video.scanned_at)

    @override_settings(MALWARE_SCAN_FAIL_CLOSED=False)
    @patch('market.tasks.scan_uploaded_file')
    def test_scan_task_keeps_pending_with_no_scanned_timestamp_on_scanner_unavailable_fail_open(self, scan_mock):
        from core.file_scanning import MalwareScannerUnavailable

        scan_mock.side_effect = MalwareScannerUnavailable('scanner down')
        video = ProductVideo.objects.create(
            product=self.product,
            video=SimpleUploadedFile('retry.webm', b'webm-retry', content_type='video/webm'),
            security_scan_status=ProductVideo.SCAN_PENDING,
        )

        with self.assertRaises(MalwareScannerUnavailable):
            scan_product_video_task(str(video.id))

        video.refresh_from_db()
        self.assertEqual(video.security_scan_status, ProductVideo.SCAN_PENDING)
        self.assertEqual(video.security_scan_reason, 'scanner-unavailable-retry')
        self.assertIsNone(video.scanned_at)

    @override_settings(MALWARE_SCAN_FAIL_CLOSED=True)
    @patch('market.tasks.scan_uploaded_file')
    def test_scan_task_marks_rejected_on_scanner_unavailable_fail_closed(self, scan_mock):
        from core.file_scanning import MalwareScannerUnavailable

        scan_mock.side_effect = MalwareScannerUnavailable('scanner down')
        video = ProductVideo.objects.create(
            product=self.product,
            video=SimpleUploadedFile('reject.webm', b'webm-reject', content_type='video/webm'),
            security_scan_status=ProductVideo.SCAN_PENDING,
        )

        result = scan_product_video_task(str(video.id))

        video.refresh_from_db()
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(video.security_scan_status, ProductVideo.SCAN_REJECTED)
        self.assertEqual(video.security_scan_reason, 'scanner-unavailable-fail-closed')
        self.assertIsNotNone(video.scanned_at)
