#server/assistant/tasks.py
import logging
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.utils import timezone

from assistant.models import DisputeMedia, ConversationSession, ConversationLog
from assistant.services.dispute_storage import dispute_storage

logger = logging.getLogger('audit')


def _sniff_type(file_path: str) -> str:
    """Lightweight MIME sniffing using magic headers."""
    try:
        with open(file_path, 'rb') as fh:
            header = fh.read(16)

        if header.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if header.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if header[0:4] == b'RIFF' and header[8:12] == b'WAVE':
            return 'audio/wav'
        if header.startswith(b'OggS'):
            return 'audio/ogg'
    except Exception:
        return 'unknown'

    return 'unknown'


def _antivirus_scan_stub(file_path: str) -> bool:
    """Placeholder for AV integration (ClamAV/Cloud AV). Returns True if safe."""
                                                
    _ = file_path
    return True


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def validate_dispute_media_task(self, media_id: int):
    try:
        media = DisputeMedia.objects.select_related('report').get(id=media_id)
    except DisputeMedia.DoesNotExist:
        return {'status': 'not_found', 'media_id': media_id}

    if media.is_deleted:
        return {'status': 'deleted', 'media_id': media_id}

    file_path = media.file.path if media.file else ''
    sniffed = _sniff_type(file_path) if file_path else 'unknown'

                                                      
    max_size = 15 * 1024 * 1024 if media.media_type == 'audio' else 5 * 1024 * 1024
    if media.file_size > max_size:
        media.validation_status = DisputeMedia.VALIDATION_REJECTED
        media.validation_reason = 'File exceeds server validation size limit.'
        media.validated_at = timezone.now()
        media.save(update_fields=['validation_status', 'validation_reason', 'validated_at', 'updated_at'])
        dispute_storage.delete(media.file.name)
        media.mark_deleted()
        return {'status': 'rejected', 'reason': 'size_limit'}

    if media.media_type == 'image' and not sniffed.startswith('image/'):
        media.validation_status = DisputeMedia.VALIDATION_REJECTED
        media.validation_reason = f'Content sniffing failed for image: {sniffed}'
        media.validated_at = timezone.now()
        media.save(update_fields=['validation_status', 'validation_reason', 'validated_at', 'updated_at'])
        dispute_storage.delete(media.file.name)
        media.mark_deleted()
        return {'status': 'rejected', 'reason': 'mime_mismatch'}

    if media.media_type == 'audio' and sniffed not in {'audio/wav', 'audio/ogg'}:
        media.validation_status = DisputeMedia.VALIDATION_REJECTED
        media.validation_reason = f'Content sniffing failed for audio: {sniffed}'
        media.validated_at = timezone.now()
        media.save(update_fields=['validation_status', 'validation_reason', 'validated_at', 'updated_at'])
        dispute_storage.delete(media.file.name)
        media.mark_deleted()
        return {'status': 'rejected', 'reason': 'mime_mismatch'}

    if not _antivirus_scan_stub(file_path):
        media.validation_status = DisputeMedia.VALIDATION_REJECTED
        media.validation_reason = 'Antivirus scan failed.'
        media.validated_at = timezone.now()
        media.save(update_fields=['validation_status', 'validation_reason', 'validated_at', 'updated_at'])
        dispute_storage.delete(media.file.name)
        media.mark_deleted()
        return {'status': 'rejected', 'reason': 'antivirus'}

    media.validation_status = DisputeMedia.VALIDATION_APPROVED
    media.validation_reason = ''
    media.validated_at = timezone.now()
    media.save(update_fields=['validation_status', 'validation_reason', 'validated_at', 'updated_at'])

    logger.info(
        f'{{"action":"assistant.dispute_media.approved","media_id":{media.id},"report_id":{media.report_id}}}'
    )
    return {'status': 'approved', 'media_id': media.id}


@shared_task
def cleanup_expired_dispute_media_task(limit: int = 500):
    from django.core.management import call_command
    call_command('cleanup_dispute_media', limit=limit)


@shared_task
def cleanup_assistant_archives_task(session_days: int = 30, log_days: int = 90):
    now = timezone.now()
    session_cutoff = now - timedelta(days=session_days)
    log_cutoff = now - timedelta(days=log_days)

    stale_sessions = ConversationSession.objects.filter(last_activity__lt=session_cutoff)
    stale_logs = ConversationLog.objects.filter(created_at__lt=log_cutoff)

    deleted_sessions = stale_sessions.count()
    deleted_logs = stale_logs.count()

    stale_sessions.delete()
    stale_logs.delete()

    logger.info(
        f'{{"action":"assistant.archive.cleanup","deleted_sessions":{deleted_sessions},"deleted_logs":{deleted_logs}}}'
    )

    return {'deleted_sessions': deleted_sessions, 'deleted_logs': deleted_logs}
