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

def schedule_batch_embedding_generation(product_ids, batch_size=128):
    """
    Chunk product_ids into batches and queue one task per batch.
    Called by management commands only — never by signals.
    Returns the number of batches queued.
    """
    product_ids = list(product_ids)
    if not product_ids:
        return 0
    batches = [
        product_ids[i:i + batch_size]
        for i in range(0, len(product_ids), batch_size)
    ]
    for batch in batches:
        try:
            generate_batch_embedding_task.delay([str(pid) for pid in batch])
        except Exception:
            generate_batch_embedding_task([str(pid) for pid in batch])
    return len(batches)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 2})
def generate_batch_embedding_task(product_ids):
    """
    Encode a batch of products in ONE model.encode() call and write all
    vectors in a single bulk operation.
    Idempotent — safe to re-run on the same product IDs.
    """
    if not product_ids:
        return {'status': 'empty'}

    from market.models import Product
    from market.search.embeddings import _build_product_embedding_text, _encode_batch
    from market.search.vector_backend import bulk_sync_product_vectors

    # select_related avoids N+1 queries inside _build_product_embedding_text
    products = list(
        Product.objects.filter(id__in=product_ids)
        .select_related('category', 'product_family', 'location')
    )
    if not products:
        return {'status': 'no_products_found'}

    texts = [_build_product_embedding_text(p) for p in products]

    # ONE model.encode() call for the entire batch
    vectors = _encode_batch(texts)

    # Drop products whose text was empty
    valid_pairs = [
        (p, v)
        for p, t, v in zip(products, texts, vectors)
        if t.strip()
    ]

    if not valid_pairs:
        return {'status': 'no_valid_text', 'count': 0}

    # Bulk-update embedding_vector in one SQL statement (batch_size=500 avoids
    # generating an excessively large single query for large batches)
    for product, vector in valid_pairs:
        product.embedding_vector = vector
    Product.objects.bulk_update(
        [p for p, _ in valid_pairs],
        ['embedding_vector'],
        batch_size=500,
    )

    # FIX: build embedding_text_map so text_hash is stored correctly per product.
    # Without this, every vector gets sha256('') as its hash, breaking any
    # skip-if-unchanged logic that compares hashes before re-embedding.
    valid_products = [p for p, _ in valid_pairs]
    valid_texts = [
        t for p, t, v in zip(products, texts, vectors)
        if t.strip()
    ]
    embedding_text_map = {
        p.id: t
        for p, t in zip(valid_products, valid_texts)
    }

    # Write to the configured vector backend in one operation
    bulk_sync_product_vectors(valid_pairs, embedding_text_map=embedding_text_map)

    return {
        'status': 'updated',
        'count': len(valid_pairs),
        'skipped': len(products) - len(valid_pairs),
    }