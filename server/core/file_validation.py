#server/core/file_validation.py
from pathlib import Path

from django.conf import settings
from rest_framework import serializers

from core.file_scanning import (
    MalwareScannerUnavailable,
    quarantine_uploaded_file,
    scan_uploaded_file,
)


IMAGE_SIGNATURES = {
    'image/jpeg': [b'\xff\xd8\xff'],
    'image/png': [b'\x89PNG\r\n\x1a\n'],
    'image/webp': [b'RIFF'],
}

VIDEO_SIGNATURES = {
    'video/mp4': [b'ftyp'],
    'video/webm': [b'\x1a\x45\xdf\xa3'],
    'video/quicktime': [b'ftypqt'],
}


def _detect_type(uploaded_file):
    head = uploaded_file.read(64)
    uploaded_file.seek(0)

    for mime, signatures in IMAGE_SIGNATURES.items():
        for sig in signatures:
            if mime == 'image/webp':
                if head.startswith(sig) and b'WEBP' in head[:16]:
                    return mime
            elif head.startswith(sig):
                return mime

    for mime, signatures in VIDEO_SIGNATURES.items():
        for sig in signatures:
            if mime in {'video/mp4', 'video/quicktime'}:
                if sig in head[:16]:
                    return mime
            elif head.startswith(sig):
                return mime

    return None


def _scan_for_malware(uploaded_file, field_name):
    try:
        result = scan_uploaded_file(uploaded_file)
    except MalwareScannerUnavailable:
        if getattr(settings, 'MALWARE_SCAN_FAIL_CLOSED', False):
            raise serializers.ValidationError(
                f'{field_name} could not be security-scanned at this time.'
            )
        return

    if not result.is_clean:
        if getattr(settings, 'MALWARE_QUARANTINE_ON_DETECT', True):
            quarantine_uploaded_file(uploaded_file, reason=result.reason or 'malware-detected')
        raise serializers.ValidationError(f'{field_name} failed malware scan checks.')


def validate_uploaded_file(uploaded_file, *, allowed_mime_types, allowed_extensions, max_bytes, field_name='file'):
    if not uploaded_file:
        raise serializers.ValidationError(f'{field_name} is required.')

    if uploaded_file.size > max_bytes:
        raise serializers.ValidationError(f'{field_name} exceeds maximum allowed size.')

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in allowed_extensions:
        raise serializers.ValidationError(f'Unsupported {field_name} extension.')

    detected = _detect_type(uploaded_file)
    if detected not in allowed_mime_types:
        raise serializers.ValidationError(f'Unsupported or invalid {field_name} content type.')

    content_type = (getattr(uploaded_file, 'content_type', '') or '').lower()
    if content_type and content_type not in allowed_mime_types:
        raise serializers.ValidationError(f'Unsupported declared {field_name} content type.')

    _scan_for_malware(uploaded_file, field_name)

    return uploaded_file
