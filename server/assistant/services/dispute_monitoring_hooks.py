# server/assistant/services/dispute_monitoring_hooks.py
import logging

logger = logging.getLogger(__name__)


def on_dispute_escalated(*, ticket_id: str, ai_risk_score: float, threshold: float):
    logger.info(
        'dispute_monitoring.escalated ticket_id=%s ai_risk_score=%.4f threshold=%.4f',
        ticket_id,
        ai_risk_score,
        threshold,
    )


def on_ai_override_flagged(*, ticket_id: str, ai_confidence_score: float, threshold: float):
    logger.info(
        'dispute_monitoring.ai_override_flagged ticket_id=%s ai_confidence_score=%.4f threshold=%.4f',
        ticket_id,
        ai_confidence_score,
        threshold,
    )


def on_high_value_detected(*, ticket_id: str, order_total: float, threshold: float):
    logger.info(
        'dispute_monitoring.high_value_detected ticket_id=%s order_total=%.2f threshold=%.2f',
        ticket_id,
        order_total,
        threshold,
    )
