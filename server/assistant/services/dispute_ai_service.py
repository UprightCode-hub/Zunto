# server/assistant/services/dispute_ai_service.py
import hashlib
import json
import logging
from typing import Dict, List

from django.utils import timezone

from assistant.models import ConversationSession, DisputeTicket, DisputeTicketCommunication, DisputeAuditLog
from assistant.processors.local_model import LocalModelAdapter

logger = logging.getLogger(__name__)


class DisputeAIService:
    """Structured advisory AI layer for dispute recommendations."""

    DECISION_APPROVED = 'approved'
    DECISION_DENIED = 'denied'
    MESSAGE_TYPE_AI_RECOMMENDATION = 'AI_RECOMMENDATION'

    @classmethod
    def evaluate_ticket(cls, *, ticket: DisputeTicket, trigger: str = 'manual', force: bool = False) -> bool:
        if ticket.admin_decision_at:
            return False

        fingerprint = cls._build_input_fingerprint(ticket)
        current_flags = ticket.ai_policy_flags or {}
        last_fingerprint = current_flags.get('_input_fingerprint') if isinstance(current_flags, dict) else None
        if ticket.ai_evaluated_at and not force and last_fingerprint == fingerprint:
            return False

        payload = cls._build_payload(ticket)
        model_output = cls._call_provider(payload)
        parsed = cls._validate_model_output(model_output)

        now = timezone.now()
        flags = {
            'flags': parsed['policy_flags'],
            '_input_fingerprint': fingerprint,
        }

        ticket.ai_recommended_decision = parsed['recommended_decision']
        ticket.ai_confidence_score = parsed['confidence_score']
        ticket.ai_risk_score = parsed['risk_score']
        ticket.ai_reasoning_summary = parsed['reasoning_summary']
        ticket.ai_policy_flags = flags
        ticket.ai_evaluated_at = now
        ticket.ai_recommendation = cls._render_summary(parsed)
        ticket.save(
            update_fields=[
                'ai_recommended_decision',
                'ai_confidence_score',
                'ai_risk_score',
                'ai_reasoning_summary',
                'ai_policy_flags',
                'ai_evaluated_at',
                'ai_recommendation',
                'updated_at',
            ]
        )

        comm_meta = {
            'trigger': trigger,
            'recommended_decision': ticket.ai_recommended_decision,
            'confidence_score': ticket.ai_confidence_score,
            'risk_score': ticket.ai_risk_score,
            'policy_flags': parsed['policy_flags'],
            'ai_evaluated_at': now.isoformat(),
        }
        DisputeTicketCommunication.objects.create(
            ticket=ticket,
            sender_role=DisputeTicketCommunication.SENDER_AI,
            channel=DisputeTicketCommunication.CHANNEL_SYSTEM,
            message_type=cls.MESSAGE_TYPE_AI_RECOMMENDATION,
            body=ticket.ai_recommendation or '',
            meta=comm_meta,
        )
        DisputeAuditLog.objects.create(
            dispute_ticket=ticket,
            action_type=DisputeAuditLog.ACTION_AI_RECOMMENDATION,
            performed_by=None,
            previous_value={},
            new_value={
                'ai_recommended_decision': ticket.ai_recommended_decision,
                'ai_confidence_score': ticket.ai_confidence_score,
                'ai_risk_score': ticket.ai_risk_score,
            },
            metadata=comm_meta,
        )
        return True

    @classmethod
    def _build_payload(cls, ticket: DisputeTicket) -> Dict:
        conversation_history = cls._conversation_history(ticket)
        communications = list(
            ticket.communications.order_by('-created_at').values('sender_role', 'message_type', 'body', 'created_at')[:20]
        )
        communications.reverse()

        return {
            'ticket_id': ticket.ticket_id,
            'seller_type': ticket.seller_type,
            'escrow_state': ticket.escrow_state,
            'dispute_category': ticket.dispute_category,
            'description': ticket.description,
            'desired_resolution': ticket.desired_resolution,
            'evidence_links': ticket.evidence_links or [],
            'conversation_history': conversation_history,
            'communications': [
                {
                    'sender_role': row['sender_role'],
                    'message_type': row['message_type'],
                    'body': (row['body'] or '')[:500],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                }
                for row in communications
            ],
        }

    @classmethod
    def _conversation_history(cls, ticket: DisputeTicket) -> List[Dict]:
        session_id = ''
        if ticket.legacy_report and isinstance(ticket.legacy_report.meta, dict):
            session_id = str(ticket.legacy_report.meta.get('session_id') or '')
        if not session_id:
            comm_meta = ticket.communications.order_by('-created_at').values_list('meta', flat=True)
            for meta in comm_meta:
                if isinstance(meta, dict) and meta.get('session_id'):
                    session_id = str(meta.get('session_id') or '')
                    break
        if not session_id:
            return []

        session = ConversationSession.objects.filter(session_id=session_id).first()
        if not session:
            return []

        history = (session.context or {}).get('history', [])
        if not isinstance(history, list):
            return []
        return history[-20:]

    @classmethod
    def _call_provider(cls, payload: Dict) -> Dict:
        adapter = LocalModelAdapter.get_instance()
        system_prompt = (
            'You are a dispute-policy recommendation engine for a marketplace. '
            'You are advisory only and never execute actions. Respond in JSON only.'
        )
        user_prompt = (
            'Evaluate the dispute payload and return strictly valid JSON with keys: '
            'recommended_decision (approved|denied), confidence_score (0-1), risk_score (0-1), '
            'reasoning_summary (string), policy_flags (array of strings).\n'
            f'Payload:\n{json.dumps(payload, default=str)}'
        )

        if adapter.is_available():
            result = adapter.generate(prompt=user_prompt, system_prompt=system_prompt, max_tokens=350, temperature=0.1)
            response_text = (result or {}).get('response') or ''
            if response_text.strip():
                return {'provider': 'llm', 'raw': response_text}

        fallback = cls._heuristic_recommendation(payload)
        return {'provider': 'heuristic', 'raw': json.dumps(fallback)}

    @classmethod
    def _heuristic_recommendation(cls, payload: Dict) -> Dict:
        text = f"{payload.get('description', '')} {payload.get('desired_resolution', '')}".lower()
        evidence_count = len(payload.get('evidence_links') or [])

        risk = 0.35
        confidence = 0.58
        flags: List[str] = []
        decision = cls.DECISION_DENIED

        if payload.get('seller_type') == DisputeTicket.SELLER_TYPE_UNVERIFIED:
            risk += 0.25
            flags.append('liability_unverified_seller')

        if any(term in text for term in ['not delivered', 'never arrived', 'scam', 'fraud']):
            decision = cls.DECISION_APPROVED
            risk += 0.2
            confidence += 0.14
            flags.append('delivery_or_fraud_claim')

        if evidence_count > 0:
            confidence += min(0.2, evidence_count * 0.05)
            flags.append('evidence_provided')
        else:
            confidence -= 0.1
            flags.append('limited_evidence')

        confidence = max(0.0, min(confidence, 0.99))
        risk = max(0.0, min(risk, 0.99))

        summary = (
            'Advisory recommendation based on dispute description, seller type, evidence count, '
            'and conversation context. This recommendation does not execute financial actions.'
        )

        return {
            'recommended_decision': decision,
            'confidence_score': confidence,
            'risk_score': risk,
            'reasoning_summary': summary,
            'policy_flags': flags,
        }

    @classmethod
    def _validate_model_output(cls, model_output: Dict) -> Dict:
        raw = (model_output or {}).get('raw') or '{}'
        data = cls._safe_parse_json(raw)

        decision = str(data.get('recommended_decision', '')).strip().lower()
        if decision not in {cls.DECISION_APPROVED, cls.DECISION_DENIED}:
            decision = cls.DECISION_DENIED

        confidence = cls._to_unit_float(data.get('confidence_score'), default=0.55)
        risk = cls._to_unit_float(data.get('risk_score'), default=0.45)

        summary = str(data.get('reasoning_summary') or '').strip()
        if not summary:
            summary = 'AI advisory summary unavailable; default conservative recommendation applied.'

        policy_flags = data.get('policy_flags')
        if isinstance(policy_flags, list):
            normalized_flags = [str(item).strip() for item in policy_flags if str(item).strip()]
        elif isinstance(policy_flags, str) and policy_flags.strip():
            normalized_flags = [policy_flags.strip()]
        else:
            normalized_flags = ['insufficient_structured_policy_flags']

        return {
            'recommended_decision': decision,
            'confidence_score': confidence,
            'risk_score': risk,
            'reasoning_summary': summary,
            'policy_flags': normalized_flags,
        }

    @staticmethod
    def _safe_parse_json(raw: str) -> Dict:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw[start:end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return {}

    @staticmethod
    def _to_unit_float(value, *, default: float) -> float:
        try:
            val = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(val, 1.0))

    @classmethod
    def _render_summary(cls, parsed: Dict) -> str:
        return (
            f"AI recommendation: {parsed['recommended_decision']} | "
            f"confidence={parsed['confidence_score']:.2f} | "
            f"risk={parsed['risk_score']:.2f}. "
            f"{parsed['reasoning_summary']}"
        )

    @classmethod
    def _build_input_fingerprint(cls, ticket: DisputeTicket) -> str:
        evidence = sorted([str(link) for link in (ticket.evidence_links or [])])
        latest_signal = ticket.communications.filter(
            message_type__in=['ticket_created', 'seller_response', 'evidence_uploaded']
        ).order_by('-created_at').values_list('created_at', flat=True).first()

        payload = {
            'description': ticket.description,
            'dispute_category': ticket.dispute_category,
            'desired_resolution': ticket.desired_resolution,
            'seller_type': ticket.seller_type,
            'escrow_state': ticket.escrow_state,
            'evidence': evidence,
            'latest_signal': latest_signal.isoformat() if latest_signal else None,
        }
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
