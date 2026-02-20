#server/core/tests_file_validation.py
from io import BytesIO
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from rest_framework import serializers

from core.file_validation import validate_uploaded_file
from core.file_scanning import MalwareScanResult, MalwareScannerUnavailable


class DummyUpload(BytesIO):
    def __init__(self, data: bytes, *, name: str, content_type: str):
        super().__init__(data)
        self.name = name
        self.content_type = content_type
        self.size = len(data)

    def chunks(self):
        self.seek(0)
        yield self.read()
        self.seek(0)


class FileValidationTests(TestCase):
    @patch('core.file_validation.settings', SimpleNamespace(MALWARE_SCAN_FAIL_CLOSED=False, MALWARE_QUARANTINE_ON_DETECT=True))
    @patch('core.file_validation.scan_uploaded_file', return_value=MalwareScanResult(is_clean=True))
    def test_allows_valid_png_when_scan_passes(self, _scan_mock):
        upload = DummyUpload(
            b'\x89PNG\r\n\x1a\nrest-of-content',
            name='image.png',
            content_type='image/png',
        )

        validated = validate_uploaded_file(
            upload,
            allowed_mime_types={'image/png'},
            allowed_extensions={'.png'},
            max_bytes=5 * 1024 * 1024,
            field_name='image',
        )

        self.assertIs(validated, upload)

    @patch('core.file_validation.settings', SimpleNamespace(MALWARE_SCAN_FAIL_CLOSED=False, MALWARE_QUARANTINE_ON_DETECT=True))
    @patch('core.file_validation.quarantine_uploaded_file')
    @patch('core.file_validation.scan_uploaded_file', return_value=MalwareScanResult(is_clean=False, reason='Eicar-Test-Signature FOUND'))
    def test_rejects_file_when_scan_reports_malware(self, _scan_mock, quarantine_mock):
        upload = DummyUpload(
            b'\x89PNG\r\n\x1a\nrest-of-content',
            name='bad.png',
            content_type='image/png',
        )

        with self.assertRaises(serializers.ValidationError):
            validate_uploaded_file(
                upload,
                allowed_mime_types={'image/png'},
                allowed_extensions={'.png'},
                max_bytes=5 * 1024 * 1024,
                field_name='image',
            )

        quarantine_mock.assert_called_once()


    @patch('core.file_validation.settings', SimpleNamespace(MALWARE_SCAN_FAIL_CLOSED=True, MALWARE_QUARANTINE_ON_DETECT=True))
    @patch('core.file_validation.scan_uploaded_file', side_effect=MalwareScannerUnavailable('clamav-unreachable'))
    def test_rejects_when_scanner_unavailable_and_fail_closed(self, _scan_mock):
        upload = DummyUpload(
            b'\x89PNG\r\n\x1a\nrest-of-content',
            name='image.png',
            content_type='image/png',
        )

        with self.assertRaises(serializers.ValidationError):
            validate_uploaded_file(
                upload,
                allowed_mime_types={'image/png'},
                allowed_extensions={'.png'},
                max_bytes=5 * 1024 * 1024,
                field_name='image',
            )
