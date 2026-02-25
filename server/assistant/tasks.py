#server/assistant/tasks.py
import logging
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Q, Avg

from assistant.models import DisputeMedia, ConversationSession, ConversationLog, UserBehaviorProfile, RecommendationDemandGap
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


@shared_task
def aggregate_user_behavior_profiles_task():
    from django.contrib.auth import get_user_model
    from cart.models import CartEvent
    from market.models import ProductView

    User = get_user_model()
    users = User.objects.filter(is_active=True)
    now = timezone.now()
    updated = 0

    for user in users.iterator():
        ai_search_count = ConversationSession.objects.filter(
            user=user,
            assistant_mode='homepage_reco',
            context_type=ConversationSession.CONTEXT_TYPE_RECOMMENDATION,
        ).count()
        normal_search_count = ProductView.objects.filter(user=user, source='normal_search').count()

        dominant_categories = list(
            ProductView.objects.filter(user=user)
            .values('product__category__name')
            .annotate(total=Count('id'))
            .order_by('-total')
            .values_list('product__category__name', flat=True)[:3]
        )

        budgets = ConversationSession.objects.filter(user=user).exclude(
            Q(constraint_state__budget_range={}) | Q(constraint_state__budget_range__isnull=True)
        ).values_list('constraint_state', flat=True)

        mins, maxs = [], []
        for st in budgets:
            b = (st or {}).get('budget_range') if isinstance(st, dict) else None
            if isinstance(b, dict):
                if b.get('min') is not None:
                    mins.append(float(b.get('min')))
                if b.get('max') is not None:
                    maxs.append(float(b.get('max')))

        ai_cart_actions = CartEvent.objects.filter(user=user, data__source='ai', event_type='cart_item_added').count()
        normal_cart_actions = CartEvent.objects.filter(user=user, data__source='normal_search', event_type='cart_item_added').count()

        ai_conversion_rate = (ai_cart_actions / ai_search_count) if ai_search_count else 0.0
        normal_conversion_rate = (normal_cart_actions / normal_search_count) if normal_search_count else 0.0

        switched = ConversationSession.objects.filter(user=user, drift_flag=True).count()
        total_reco = ConversationSession.objects.filter(user=user, assistant_mode='homepage_reco').count()
        switch_frequency = (switched / total_reco) if total_reco else 0.0

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        profile.ai_search_count = ai_search_count
        profile.normal_search_count = normal_search_count
        profile.dominant_categories = [c for c in dominant_categories if c]
        profile.avg_budget_min = (sum(mins) / len(mins)) if mins else None
        profile.avg_budget_max = (sum(maxs) / len(maxs)) if maxs else None
        profile.ai_conversion_rate = ai_conversion_rate
        profile.normal_conversion_rate = normal_conversion_rate
        profile.switch_frequency = switch_frequency
        profile.ai_high_intent_no_conversion = ai_search_count >= 3 and ai_cart_actions >= 2 and ai_conversion_rate < 0.25
        profile.last_aggregated_at = now
        profile.save()
        updated += 1

    return {'updated_profiles': updated}


@shared_task
def aggregate_demand_gap_task():
    stale_gaps = RecommendationDemandGap.objects.filter(last_seen_at__lt=timezone.now() - timedelta(days=90))
    deleted = stale_gaps.count()
    stale_gaps.delete()
    return {'deleted_stale_gaps': deleted}
