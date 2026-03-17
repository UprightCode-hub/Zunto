import importlib.util

from django.utils import timezone
from django.db.models import Count, Q

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
from .models import DemandEvent, Product, ProductVideo


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
        video.scanned_at = None
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



def schedule_product_embedding_generation(product_id):
    """Queue product embedding generation with graceful fallback when Celery runtime is unavailable."""
    try:
        generate_product_embedding_task.delay(str(product_id))
        return 'queued'
    except Exception:
        generate_product_embedding_task(str(product_id))
        return 'executed_inline'


def schedule_demand_event_processing(event_id):
    """Queue demand-event aggregation with graceful fallback when Celery runtime is unavailable."""
    try:
        process_demand_event.delay(str(event_id))
        return 'queued'
    except Exception:
        process_demand_event(str(event_id))
        return 'executed_inline'


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 2})
def process_demand_event(event_id):
    """Compute baseline demand score snapshot for the event's product."""
    try:
        event = DemandEvent.objects.only('id', 'product_id').get(id=event_id)
    except DemandEvent.DoesNotExist:
        return {'status': 'missing'}

    if not event.product_id:
        return {'status': 'no_product'}

    aggregates = DemandEvent.objects.filter(product_id=event.product_id).aggregate(
        views=Count('id', filter=Q(event_type=DemandEvent.EVENT_VIEW)),
        favorites=Count('id', filter=Q(event_type=DemandEvent.EVENT_FAVORITE)),
        cart_adds=Count('id', filter=Q(event_type=DemandEvent.EVENT_CART_ADD)),
        purchases=Count('id', filter=Q(event_type=DemandEvent.EVENT_PURCHASE)),
    )

    score = (
        int(aggregates.get('views') or 0)
        + (int(aggregates.get('favorites') or 0) * 3)
        + (int(aggregates.get('cart_adds') or 0) * 4)
        + (int(aggregates.get('purchases') or 0) * 6)
    )

    return {
        'status': 'processed',
        'event_id': str(event.id),
        'product_id': str(event.product_id),
        'score': score,
        'counts': {
            'views': int(aggregates.get('views') or 0),
            'favorites': int(aggregates.get('favorites') or 0),
            'cart_adds': int(aggregates.get('cart_adds') or 0),
            'purchases': int(aggregates.get('purchases') or 0),
        },
    }


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 2})
def generate_product_embedding_task(product_id):
    try:
        product = Product.objects.select_related('category').get(id=product_id)
    except Product.DoesNotExist:
        return {'status': 'missing'}

    from market.search.embeddings import generate_product_embedding

    embedding = generate_product_embedding(product)
    Product.objects.filter(id=product.id).update(embedding_vector=embedding)
    return {'status': 'updated', 'product_id': str(product.id), 'embedding_dimensions': len(embedding or [])}
