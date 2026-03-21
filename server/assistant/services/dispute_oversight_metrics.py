# server/assistant/services/dispute_oversight_metrics.py
from assistant.models import DisputeTicket


class DisputeOversightMetricsService:
    """Lightweight oversight metrics for AI/admin dispute monitoring."""

    @staticmethod
    def _pct(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round((numerator / denominator) * 100.0, 2)

    @classmethod
    def summary(cls) -> dict:
        tickets = DisputeTicket.objects.all()
        total = tickets.count()

        resolved = tickets.filter(
            status__in=[DisputeTicket.STATUS_RESOLVED_APPROVED, DisputeTicket.STATUS_RESOLVED_DENIED]
        )
        resolved_count = resolved.count()

        agreements = resolved.filter(ai_admin_agreement=True).count()
        overrides = resolved.filter(ai_override_flag=True).count()
        high_risk = tickets.filter(ai_risk_score__gte=0.85).count()
        escalated = tickets.filter(status=DisputeTicket.STATUS_ESCALATED).count()
        senior_review = tickets.filter(status=DisputeTicket.STATUS_UNDER_SENIOR_REVIEW).count()

        return {
            'total_tickets': total,
            'resolved_tickets': resolved_count,
            'ai_accuracy_rate_pct': cls._pct(agreements, resolved_count),
            'admin_override_rate_pct': cls._pct(overrides, resolved_count),
            'high_risk_dispute_pct': cls._pct(high_risk, total),
            'escalation_rate_pct': cls._pct(escalated, total),
            'senior_review_rate_pct': cls._pct(senior_review, total),
            'counts': {
                'agreements': agreements,
                'overrides': overrides,
                'high_risk': high_risk,
                'escalated': escalated,
                'senior_review': senior_review,
            },
        }
