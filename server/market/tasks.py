import importlib.util

from django.utils import timezone

if importlib.util.find_spec('celery') is not None:
    from celery import shared_task
else:
    def shared_task(*args, **kwargs):
        def decorator(func):
            def _direct_delay(*a, **kw):
                return func(*a, **kw)
            func.delay = _direct_delay
            return func
        return decorator

from core.file_scanning import MalwareScannerUnavailable, quarantine_uploaded_file, scan_uploaded_file
from .models import ProductVideo


def schedule_product_video_scan(video_id):
    """Queue product-video scan task with graceful fallback if Celery runtime is unavailable."""
    try:
        scan_product_video_task.delay(video_id)
        return 'queued'
    except Exception:
        scan_product_video_task(video_id)
        return 'executed_inline'


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def scan_product_video_task(video_id):
    try:
        video = ProductVideo.objects.get(id=video_id)
    except ProductVideo.DoesNotExist:
        return {'status': 'missing'}

    uploaded_file = getattr(video, 'video', None)
    if not uploaded_file:
        video.security_scan_status = ProductVideo.SCAN_REJECTED
        video.security_scan_reason = 'missing-video-file'
        video.scanned_at = timezone.now()
        video.save(update_fields=['security_scan_status', 'security_scan_reason', 'scanned_at'])
        return {'status': 'rejected', 'reason': 'missing-video-file'}

    try:
        result = scan_uploaded_file(uploaded_file)
    except MalwareScannerUnavailable:
        from django.conf import settings

        if getattr(settings, 'MALWARE_SCAN_FAIL_CLOSED', False):
            video.security_scan_status = ProductVideo.SCAN_REJECTED
            video.security_scan_reason = 'scanner-unavailable-fail-closed'
            video.scanned_at = timezone.now()
            video.save(update_fields=['security_scan_status', 'security_scan_reason', 'scanned_at'])
            return {'status': 'rejected', 'reason': 'scanner-unavailable-fail-closed'}

        video.security_scan_status = ProductVideo.SCAN_PENDING
        video.security_scan_reason = 'scanner-unavailable-retry'
        video.scanned_at = timezone.now()
        video.save(update_fields=['security_scan_status', 'security_scan_reason', 'scanned_at'])
        raise

    if not result.is_clean:
        quarantine_path = quarantine_uploaded_file(uploaded_file, reason=result.reason or 'malware-detected')
        video.security_scan_status = ProductVideo.SCAN_QUARANTINED
        video.security_scan_reason = result.reason or 'malware-detected'
        video.security_quarantine_path = quarantine_path
        video.scanned_at = timezone.now()
        video.save(update_fields=['security_scan_status', 'security_scan_reason', 'security_quarantine_path', 'scanned_at'])
        return {'status': 'quarantined', 'reason': video.security_scan_reason}

    video.security_scan_status = ProductVideo.SCAN_CLEAN
    video.security_scan_reason = ''
    video.security_quarantine_path = ''
    video.scanned_at = timezone.now()
    video.save(update_fields=['security_scan_status', 'security_scan_reason', 'security_quarantine_path', 'scanned_at'])
    return {'status': 'clean'}
