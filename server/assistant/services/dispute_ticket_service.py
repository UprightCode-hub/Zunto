#server/assistant/services/dispute_ticket_service.py
import logging
from datetime import timedelta
from typing import Any, List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from assistant.services.dispute_monitoring_hooks import (
    on_ai_override_flagged,
    on_dispute_escalated,
    on_high_value_detected,
)

from assistant.models import (
    ConversationLog,
    ConversationSession,
    DisputeTicket,
    DisputeTicketCommunication,
    DisputeAuditLog,
    Report,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class DisputeTicketError(ValueError):
    """Validation error for ticket creation/admin execution."""


class DisputeTicketService:
    ALLOWED_STATUS_TRANSITIONS = {
        DisputeTicket.STATUS_OPEN: {
            DisputeTicket.STATUS_UNDER_REVIEW,
            DisputeTicket.STATUS_RESOLVED_APPROVED,
            DisputeTicket.STATUS_RESOLVED_DENIED,
        },
        DisputeTicket.STATUS_UNDER_REVIEW: {
            DisputeTicket.STATUS_ESCALATED,
            DisputeTicket.STATUS_RESOLVED_APPROVED,
            DisputeTicket.STATUS_RESOLVED_DENIED,
        },
        DisputeTicket.STATUS_ESCALATED: {DisputeTicket.STATUS_UNDER_SENIOR_REVIEW},
        DisputeTicket.STATUS_UNDER_SENIOR_REVIEW: {
            DisputeTicket.STATUS_RESOLVED_APPROVED,
            DisputeTicket.STATUS_RESOLVED_DENIED,
        },
        DisputeTicket.STATUS_RESOLVED_APPROVED: {DisputeTicket.STATUS_CLOSED},
        DisputeTicket.STATUS_RESOLVED_DENIED: {DisputeTicket.STATUS_CLOSED},
        DisputeTicket.STATUS_CLOSED: set(),
    }

    ALLOWED_ESCROW_TRANSITIONS = {
        DisputeTicket.ESCROW_NOT_APPLICABLE: {DisputeTicket.ESCROW_NOT_APPLICABLE, DisputeTicket.ESCROW_FROZEN},
        DisputeTicket.ESCROW_FROZEN: {
            DisputeTicket.ESCROW_FROZEN,
            DisputeTicket.ESCROW_RELEASED_TO_BUYER,
            DisputeTicket.ESCROW_RELEASED_TO_SELLER,
        },
        DisputeTicket.ESCROW_RELEASED_TO_BUYER: {DisputeTicket.ESCROW_RELEASED_TO_BUYER},
        DisputeTicket.ESCROW_RELEASED_TO_SELLER: {DisputeTicket.ESCROW_RELEASED_TO_SELLER},
    }


    @staticmethod
    def _audit_log(*, ticket: DisputeTicket, action_type: str, performed_by=None, previous_value=None, new_value=None, metadata=None):
        DisputeAuditLog.objects.create(
            dispute_ticket=ticket,
            action_type=action_type,
            performed_by=performed_by,
            previous_value=previous_value or {},
            new_value=new_value or {},
            metadata=metadata or {},
        )
    @staticmethod
    def _resolve_order(order_id: Optional[str]):
        if not order_id:
            return None
        from orders.models import Order
        try:
            return Order.objects.select_related('customer').get(id=order_id)
        except Order.DoesNotExist as exc:
            raise DisputeTicketError('Invalid order_id supplied.') from exc

    @staticmethod
    def _resolve_product(product_id: Optional[str]):
        if not product_id:
            return None
        from market.models import Product
        try:
            return Product.objects.select_related('seller').get(id=product_id)
        except Product.DoesNotExist as exc:
            raise DisputeTicketError('Invalid product_id supplied.') from exc

    @classmethod
    def _resolve_seller(cls, *, order, product):
        seller = None

        if product and product.seller_id:
            seller = product.seller

        if order and product:
            order_item = order.items.filter(product_id=product.id).select_related('seller').first()
            if order_item and order_item.seller_id:
                if seller and seller.id != order_item.seller_id:
                    raise DisputeTicketError('order_id and product_id reference different sellers.')
                seller = order_item.seller

        if order and not product:
            sellers = list(
                order.items.exclude(seller__isnull=True).values_list('seller_id', flat=True).distinct()[:2]
            )
            if len(sellers) != 1:
                raise DisputeTicketError('order_id must map to exactly one seller when product_id is omitted.')
            seller = User.objects.get(id=sellers[0])

        if not seller:
            raise DisputeTicketError('Unable to resolve seller_id. Provide valid product_id or order_id.')

        return seller

    @staticmethod
    def _seller_type_for_user(seller: User) -> str:
        return (
            DisputeTicket.SELLER_TYPE_VERIFIED
            if getattr(seller, 'is_managed_seller', False)
            else DisputeTicket.SELLER_TYPE_UNVERIFIED
        )

    @staticmethod
    def _normalize_evidence(evidence: Optional[Any]) -> List[str]:
        if not evidence:
            return []
        if isinstance(evidence, list):
            return [str(item).strip() for item in evidence if str(item).strip()]
        if isinstance(evidence, str):
            txt = evidence.strip()
            return [txt] if txt else []
        raise DisputeTicketError('evidence must be a list of links or a single link string.')

    @staticmethod
    def _ticket_supports_escrow(ticket: DisputeTicket) -> bool:
        if ticket.seller_type != DisputeTicket.SELLER_TYPE_VERIFIED:
            return False
        if not ticket.order_id:
            return False

        from orders.commerce import is_managed_order
        return is_managed_order(ticket.order)

    @classmethod
    def _freeze_escrow_for_ticket(cls, ticket: DisputeTicket) -> None:
        if ticket.escrow_state == DisputeTicket.ESCROW_FROZEN:
            return

        if not cls._ticket_supports_escrow(ticket):
            cls._validate_escrow_transition(ticket.escrow_state, DisputeTicket.ESCROW_NOT_APPLICABLE)
            ticket.escrow_state = DisputeTicket.ESCROW_NOT_APPLICABLE
            ticket.escrow_execution_meta = {
                **(ticket.escrow_execution_meta or {}),
                'freeze_reason': 'ticket_not_escrow_eligible',
            }
            ticket.save(update_fields=['escrow_state', 'escrow_execution_meta', 'updated_at'])
            return

        if ticket.order.payment_status != 'paid':
            raise DisputeTicketError('Escrow cannot be frozen because the order payment_status is not paid.')

        now = timezone.now()
        cls._validate_escrow_transition(ticket.escrow_state, DisputeTicket.ESCROW_FROZEN)
        ticket.escrow_state = DisputeTicket.ESCROW_FROZEN
        ticket.escrow_frozen_at = now
        ticket.escrow_executed_at = None
        ticket.escrow_execution_locked = False
        ticket.escrow_execution_reference = f'ESCROW-FREEZE-{ticket.ticket_id}'
        ticket.escrow_execution_meta = {
            **(ticket.escrow_execution_meta or {}),
            'frozen_by': 'ticket_creation',
            'frozen_at': now.isoformat(),
        }
        ticket.save(
            update_fields=[
                'escrow_state',
                'escrow_frozen_at',
                'escrow_execution_reference',
                'escrow_execution_meta',
                'escrow_executed_at',
                'escrow_execution_locked',
                'updated_at',
            ]
        )

        DisputeTicketCommunication.objects.create(
            ticket=ticket,
            sender_role=DisputeTicketCommunication.SENDER_SYSTEM,
            channel=DisputeTicketCommunication.CHANNEL_SYSTEM,
            message_type='escrow_frozen',
            body='Escrow funds have been frozen pending dispute outcome.',
            meta={'order_id': str(ticket.order_id), 'financial_action': 'escrow_frozen'},
        )

    @classmethod
    def create_ticket(
        cls,
        *,
        buyer: User,
        order_id: Optional[str],
        product_id: Optional[str],
        dispute_category: str,
        description: str,
        desired_resolution: str,
        evidence: Optional[Any] = None,
        attached_report_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> DisputeTicket:
        order = cls._resolve_order(order_id)
        product = cls._resolve_product(product_id)
        seller = cls._resolve_seller(order=order, product=product)

        if order and order.customer_id != buyer.id:
            raise DisputeTicketError('buyer does not own the supplied order_id.')

        if buyer.id == seller.id:
            raise DisputeTicketError('buyer and seller cannot be the same account.')

        evidence_links = cls._normalize_evidence(evidence)
        seller_type = cls._seller_type_for_user(seller)
        response_hours = int(getattr(settings, 'DISPUTE_SELLER_RESPONSE_HOURS', 48))
        due_at = timezone.now() + timedelta(hours=max(response_hours, 1))

        with transaction.atomic():
            legacy_report = None
            if attached_report_id:
                legacy_report = Report.objects.filter(id=attached_report_id).first()

            ticket = DisputeTicket.objects.create(
                ticket_id=DisputeTicket.generate_ticket_id(),
                buyer=buyer,
                seller=seller,
                legacy_report=legacy_report,
                seller_type=seller_type,
                order=order,
                product=product,
                dispute_category=dispute_category,
                description=description,
                desired_resolution=desired_resolution or '',
                evidence_links=evidence_links,
                status=DisputeTicket.STATUS_OPEN,
                seller_response_due_at=due_at,
            )

            DisputeTicketCommunication.objects.create(
                ticket=ticket,
                sender_role=DisputeTicketCommunication.SENDER_BUYER,
                channel=DisputeTicketCommunication.CHANNEL_CHAT,
                message_type='ticket_created',
                body=description,
                meta={
                    'desired_resolution': desired_resolution,
                    'dispute_category': dispute_category,
                    'attached_report_id': attached_report_id,
                    'session_id': session_id,
                    'order_id': str(order.id) if order else '',
                    'product_id': str(product.id) if product else '',
                },
            )

            cls._freeze_escrow_for_ticket(ticket)

        cls._send_notifications(ticket)

        # Advisory-only AI recommendation run; failures must never block ticket creation.
        try:
            from assistant.services.dispute_ai_service import DisputeAIService
            DisputeAIService.evaluate_ticket(ticket=ticket, trigger='ticket_created')
            ticket.refresh_from_db()
            cls._apply_auto_escalation_rules(ticket)
        except Exception:
            logger.exception('Dispute AI evaluation failed after ticket creation')

        return ticket

    @classmethod
    def _validate_admin_transition(cls, current_status: str, target_status: str):
        allowed = cls.ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            if current_status in {DisputeTicket.STATUS_RESOLVED_APPROVED, DisputeTicket.STATUS_RESOLVED_DENIED}:
                raise DisputeTicketError('Resolved tickets cannot transition again except to CLOSED.')
            raise DisputeTicketError(f'Illegal status transition: {current_status} -> {target_status}')

    @classmethod
    def _validate_escrow_transition(cls, current_state: str, target_state: str):
        allowed = cls.ALLOWED_ESCROW_TRANSITIONS.get(current_state, set())
        if target_state not in allowed:
            raise DisputeTicketError(f'Illegal escrow transition: {current_state} -> {target_state}')

    @staticmethod
    def _assert_invariants(ticket: DisputeTicket):
        if ticket.escrow_state == DisputeTicket.ESCROW_RELEASED_TO_BUYER and ticket.status != DisputeTicket.STATUS_RESOLVED_APPROVED:
            raise DisputeTicketError('Invariant violation: released_to_buyer requires RESOLVED_APPROVED status.')
        if ticket.escrow_state == DisputeTicket.ESCROW_RELEASED_TO_SELLER and ticket.status != DisputeTicket.STATUS_RESOLVED_DENIED:
            raise DisputeTicketError('Invariant violation: released_to_seller requires RESOLVED_DENIED status.')

        released = ticket.escrow_state in {
            DisputeTicket.ESCROW_RELEASED_TO_BUYER,
            DisputeTicket.ESCROW_RELEASED_TO_SELLER,
        }
        if ticket.escrow_executed_at and not released:
            raise DisputeTicketError('Invariant violation: escrow_executed_at requires released escrow state.')
        if released and not ticket.escrow_executed_at:
            raise DisputeTicketError('Invariant violation: released escrow state requires escrow_executed_at.')

    @classmethod
    def _transition_status(cls, *, ticket: DisputeTicket, target_status: str, reason: str = ''):
        current_status = ticket.status
        cls._validate_admin_transition(current_status, target_status)
        ticket.status = target_status
        meta = {'from_status': current_status, 'to_status': target_status}
        if reason:
            meta['reason'] = reason
        return meta

    @staticmethod
    def _is_high_value_ticket(ticket: DisputeTicket) -> bool:
        threshold = float(getattr(settings, 'DISPUTE_HIGH_VALUE_THRESHOLD', 250000))
        if not ticket.order_id or threshold <= 0:
            return False
        try:
            amount = float(ticket.order.total_amount)
        except Exception:
            return False
        is_high_value = amount >= threshold
        if is_high_value:
            on_high_value_detected(ticket_id=ticket.ticket_id, order_total=amount, threshold=threshold)
        return is_high_value

    @classmethod
    def _apply_auto_escalation_rules(cls, ticket: DisputeTicket) -> bool:
        if ticket.admin_decision_at:
            return False

        high_risk_threshold = float(getattr(settings, 'DISPUTE_AI_HIGH_RISK_THRESHOLD', 0.85))
        ai_risk = float(ticket.ai_risk_score or 0.0)

        if ai_risk >= high_risk_threshold and ticket.status == DisputeTicket.STATUS_OPEN:
            cls._validate_admin_transition(ticket.status, DisputeTicket.STATUS_UNDER_REVIEW)
            ticket.status = DisputeTicket.STATUS_UNDER_REVIEW
            cls._validate_admin_transition(ticket.status, DisputeTicket.STATUS_ESCALATED)
            ticket.status = DisputeTicket.STATUS_ESCALATED
            DisputeTicketCommunication.objects.create(
                ticket=ticket,
                sender_role=DisputeTicketCommunication.SENDER_SYSTEM,
                channel=DisputeTicketCommunication.CHANNEL_SYSTEM,
                message_type='auto_escalation',
                body='Ticket auto-escalated due to high AI risk score.',
                meta={
                    'ai_risk_score': ai_risk,
                    'high_risk_threshold': high_risk_threshold,
                },
            )
            ticket.save(update_fields=['status', 'updated_at'])
            cls._audit_log(
                ticket=ticket,
                action_type=DisputeAuditLog.ACTION_ESCALATION_TRIGGER,
                previous_value={'status': DisputeTicket.STATUS_OPEN},
                new_value={'status': ticket.status},
                metadata={'ai_risk_score': ai_risk, 'threshold': high_risk_threshold, 'trigger': 'auto_risk'},
            )
            on_dispute_escalated(ticket_id=ticket.ticket_id, ai_risk_score=ai_risk, threshold=high_risk_threshold)
            return True
        return False

    @classmethod
    def _record_ai_admin_comparison(cls, *, ticket: DisputeTicket, status: str):
        now = timezone.now()
        ai_decision = (ticket.ai_recommended_decision or '').strip().lower()
        admin_decision = ''
        if status == DisputeTicket.STATUS_RESOLVED_APPROVED:
            admin_decision = 'approved'
        elif status == DisputeTicket.STATUS_RESOLVED_DENIED:
            admin_decision = 'denied'

        if not ai_decision or not admin_decision:
            ticket.ai_admin_agreement = None
            ticket.ai_override_flag = False
            ticket.ai_override_reason = ''
            ticket.ai_evaluated_against_admin_at = now
            return

        agreement = ai_decision == admin_decision
        ticket.ai_admin_agreement = agreement
        ticket.ai_evaluated_against_admin_at = now

        conf_threshold = float(getattr(settings, 'DISPUTE_AI_OVERRIDE_CONFIDENCE_THRESHOLD', 0.8))
        ai_conf = float(ticket.ai_confidence_score or 0.0)
        if not agreement and ai_conf >= conf_threshold:
            ticket.ai_override_flag = True
            ticket.ai_override_reason = (
                f'Admin decision diverged from AI recommendation at confidence {ai_conf:.2f} '
                f'(threshold {conf_threshold:.2f}).'
            )
        else:
            ticket.ai_override_flag = False
            ticket.ai_override_reason = ''

    @classmethod
    def _release_escrow_to_buyer(cls, *, ticket: DisputeTicket, admin_user, reason: str):
        from orders.models import OrderStatusHistory, Payment, Refund

        order = ticket.order
        if not order:
            raise DisputeTicketError('Escrow buyer release requires a linked order.')

        payment = (
            Payment.objects.filter(order=order)
            .order_by('-created_at')
            .first()
        )

        now = timezone.now()
        refund_ref = f'DISPUTE-{ticket.ticket_id}'
        refund_defaults = {
            'payment': payment,
            'amount': order.total_amount,
            'reason': 'other',
            'description': reason or f'Dispute resolution refund for {ticket.ticket_id}',
            'status': 'completed',
            'refund_reference': refund_ref,
            'processed_by': admin_user,
            'processed_at': now,
            'admin_notes': f'Dispute ticket {ticket.ticket_id}',
            'gateway_response': {'source': 'dispute_escrow_engine', 'ticket_id': ticket.ticket_id},
        }
        refund, created = Refund.objects.get_or_create(
            order=order,
            refund_reference=refund_ref,
            defaults=refund_defaults,
        )

        if not created and refund.status != 'completed':
            refund.status = 'completed'
            refund.processed_by = admin_user
            refund.processed_at = now
            refund.payment = payment
            refund.admin_notes = f'Dispute ticket {ticket.ticket_id}'
            refund.save(update_fields=['status', 'processed_by', 'processed_at', 'payment', 'admin_notes'])

        if payment and payment.status != 'refunded':
            payment.status = 'refunded'
            payment.save(update_fields=['status', 'updated_at'])

        old_status = order.status
        if order.payment_status != 'refunded' or order.status != 'refunded':
            order.payment_status = 'refunded'
            order.status = 'refunded'
            order.save(update_fields=['payment_status', 'status', 'updated_at'])

        if old_status != order.status:
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=order.status,
                notes=f'Dispute {ticket.ticket_id} resolved in favor of buyer.',
                changed_by=admin_user,
            )

        ticket.escrow_state = DisputeTicket.ESCROW_RELEASED_TO_BUYER
        ticket.escrow_released_at = now
        ticket.escrow_execution_reference = refund.refund_reference or f'BUYER-{ticket.ticket_id}'
        ticket.escrow_execution_meta = {
            **(ticket.escrow_execution_meta or {}),
            'financial_action': 'release_to_buyer',
            'refund_id': str(refund.id),
            'refund_created': created,
        }

    @classmethod
    def _release_escrow_to_seller(cls, *, ticket: DisputeTicket, admin_user, reason: str):
        from orders.models import Payment

        if not ticket.order_id:
            raise DisputeTicketError('Escrow seller release requires a linked order.')

        order = ticket.order
        payment = Payment.objects.filter(order=order).order_by('-created_at').first()
        if payment and payment.status in {'pending', 'processing'}:
            payment.status = 'success'
            payment.save(update_fields=['status', 'updated_at'])

        now = timezone.now()
        ticket.escrow_state = DisputeTicket.ESCROW_RELEASED_TO_SELLER
        ticket.escrow_released_at = now
        ticket.escrow_execution_reference = f'SELLER-{ticket.ticket_id}'
        ticket.escrow_execution_meta = {
            **(ticket.escrow_execution_meta or {}),
            'financial_action': 'release_to_seller',
            'released_by_admin_id': str(admin_user.id),
            'reason': reason,
        }

    @classmethod
    def _apply_financial_resolution(cls, *, ticket: DisputeTicket, status: str, admin_user, reason: str):
        if not cls._ticket_supports_escrow(ticket):
            cls._validate_escrow_transition(ticket.escrow_state, DisputeTicket.ESCROW_NOT_APPLICABLE)
            ticket.escrow_state = DisputeTicket.ESCROW_NOT_APPLICABLE
            ticket.escrow_execution_meta = {
                **(ticket.escrow_execution_meta or {}),
                'resolution_skipped_reason': 'ticket_not_escrow_eligible',
            }
            return

        if status not in {DisputeTicket.STATUS_RESOLVED_APPROVED, DisputeTicket.STATUS_RESOLVED_DENIED}:
            return

        if ticket.escrow_execution_locked or ticket.escrow_executed_at:
            raise DisputeTicketError('Escrow execution already completed; replay blocked.')

        if ticket.escrow_state != DisputeTicket.ESCROW_FROZEN:
            raise DisputeTicketError('Escrow must be frozen before financial release can occur.')

        ticket.escrow_execution_locked = True
        ticket.escrow_execution_meta = {
            **(ticket.escrow_execution_meta or {}),
            'execution_lock_acquired_at': timezone.now().isoformat(),
        }

        if status == DisputeTicket.STATUS_RESOLVED_APPROVED:
            cls._validate_escrow_transition(ticket.escrow_state, DisputeTicket.ESCROW_RELEASED_TO_BUYER)
            cls._release_escrow_to_buyer(ticket=ticket, admin_user=admin_user, reason=reason)
            action_msg = 'Escrow released to buyer based on approved dispute resolution.'
            action_type = 'escrow_released_to_buyer'
        else:
            cls._validate_escrow_transition(ticket.escrow_state, DisputeTicket.ESCROW_RELEASED_TO_SELLER)
            cls._release_escrow_to_seller(ticket=ticket, admin_user=admin_user, reason=reason)
            action_msg = 'Escrow released to seller based on denied dispute resolution.'
            action_type = 'escrow_released_to_seller'

        ticket.escrow_executed_at = timezone.now()
        ticket.escrow_execution_meta = {
            **(ticket.escrow_execution_meta or {}),
            'execution_completed_at': ticket.escrow_executed_at.isoformat(),
            'execution_status': 'completed',
        }
        cls._audit_log(
            ticket=ticket,
            action_type=DisputeAuditLog.ACTION_ESCROW_EXECUTION,
            performed_by=admin_user,
            previous_value={'escrow_state': DisputeTicket.ESCROW_FROZEN},
            new_value={
                'escrow_state': ticket.escrow_state,
                'escrow_executed_at': ticket.escrow_executed_at.isoformat(),
            },
            metadata={'status': status, 'execution_reference': ticket.escrow_execution_reference},
        )

        DisputeTicketCommunication.objects.create(
            ticket=ticket,
            sender_role=DisputeTicketCommunication.SENDER_ADMIN,
            channel=DisputeTicketCommunication.CHANNEL_SYSTEM,
            message_type=action_type,
            body=action_msg,
            meta={
                'financial_action': action_type,
                'execution_reference': ticket.escrow_execution_reference,
                'escrow_state': ticket.escrow_state,
                'escrow_executed_at': ticket.escrow_executed_at.isoformat(),
            },
        )

    @classmethod
    def apply_admin_decision(
        cls,
        *,
        ticket: DisputeTicket,
        admin_user,
        status: str,
        decision: str,
        reason: str = '',
    ) -> DisputeTicket:
        with transaction.atomic():
            ticket = DisputeTicket.objects.select_for_update().select_related('order', 'legacy_report').get(id=ticket.id)

            same_payload = (
                ticket.status == status
                and (ticket.admin_decision or '') == (decision or '')
                and (ticket.admin_decision_reason or '') == (reason or '')
            )
            if same_payload:
                raise DisputeTicketError('Duplicate admin decision payload detected; replay rejected.')

            if ticket.status in {
                DisputeTicket.STATUS_RESOLVED_APPROVED,
                DisputeTicket.STATUS_RESOLVED_DENIED,
                DisputeTicket.STATUS_CLOSED,
            }:
                raise DisputeTicketError('Ticket already decided; further admin decision updates are blocked.')

            if status in {DisputeTicket.STATUS_RESOLVED_APPROVED, DisputeTicket.STATUS_RESOLVED_DENIED}:
                if cls._is_high_value_ticket(ticket) and ticket.status != DisputeTicket.STATUS_UNDER_SENIOR_REVIEW:
                    raise DisputeTicketError('High-value disputes must transition through UNDER_SENIOR_REVIEW before final resolution.')

            previous_status = ticket.status
            cls._validate_admin_transition(ticket.status, status)
            ticket.status = status
            ticket.admin_decision = decision
            ticket.admin_decision_reason = reason
            ticket.admin_user = admin_user
            ticket.admin_decision_at = timezone.now()

            if status in {DisputeTicket.STATUS_RESOLVED_APPROVED, DisputeTicket.STATUS_RESOLVED_DENIED}:
                cls._apply_financial_resolution(ticket=ticket, status=status, admin_user=admin_user, reason=reason)

            cls._record_ai_admin_comparison(ticket=ticket, status=status)
            cls._assert_invariants(ticket)

            ticket.save(
                update_fields=[
                    'status',
                    'admin_decision',
                    'admin_decision_reason',
                    'admin_user',
                    'admin_decision_at',
                    'ai_admin_agreement',
                    'ai_override_flag',
                    'ai_override_reason',
                    'ai_evaluated_against_admin_at',
                    'escrow_state',
                    'escrow_frozen_at',
                    'escrow_released_at',
                    'escrow_executed_at',
                    'escrow_execution_locked',
                    'escrow_execution_reference',
                    'escrow_execution_meta',
                    'updated_at',
                ]
            )

        meta = {
            'status': status,
            'previous_status': previous_status,
            'admin_user_id': str(admin_user.id),
            'legacy_report_id': ticket.legacy_report_id,
            'escrow_state': ticket.escrow_state,
            'escrow_execution_reference': ticket.escrow_execution_reference,
            'escrow_executed_at': ticket.escrow_executed_at.isoformat() if ticket.escrow_executed_at else None,
            'ai_admin_agreement': ticket.ai_admin_agreement,
            'ai_override_flag': ticket.ai_override_flag,
        }
        if reason:
            meta['reason'] = reason

        cls._audit_log(
            ticket=ticket,
            action_type=DisputeAuditLog.ACTION_STATUS_CHANGE,
            performed_by=admin_user,
            previous_value={'status': meta.get('previous_status')},
            new_value={'status': status},
            metadata={'reason': reason},
        )
        cls._audit_log(
            ticket=ticket,
            action_type=DisputeAuditLog.ACTION_ADMIN_DECISION,
            performed_by=admin_user,
            previous_value={'admin_decision': ''},
            new_value={'admin_decision': decision, 'admin_decision_reason': reason, 'status': status},
            metadata={'legacy_report_id': ticket.legacy_report_id},
        )
        if ticket.ai_override_flag:
            cls._audit_log(
                ticket=ticket,
                action_type=DisputeAuditLog.ACTION_AI_OVERRIDE_FLAGGED,
                performed_by=admin_user,
                previous_value={'ai_override_flag': False},
                new_value={'ai_override_flag': True},
                metadata={'ai_override_reason': ticket.ai_override_reason, 'ai_confidence_score': ticket.ai_confidence_score},
            )
            on_ai_override_flagged(
                ticket_id=ticket.ticket_id,
                ai_confidence_score=float(ticket.ai_confidence_score or 0.0),
                threshold=float(getattr(settings, 'DISPUTE_AI_OVERRIDE_CONFIDENCE_THRESHOLD', 0.8)),
            )

        DisputeTicketCommunication.objects.create(
            ticket=ticket,
            sender_role=DisputeTicketCommunication.SENDER_ADMIN,
            channel=DisputeTicketCommunication.CHANNEL_SYSTEM,
            message_type='admin_decision',
            body=decision,
            meta=meta,
        )

        cls._sync_admin_decision_to_conversation(ticket=ticket, decision=decision, status=status)
        return ticket

    @classmethod
    def _sync_admin_decision_to_conversation(cls, *, ticket: DisputeTicket, decision: str, status: str) -> None:
        session_id = ''
        if ticket.legacy_report_id:
            session_id = str(ticket.legacy_report.meta.get('session_id', '') or '') if ticket.legacy_report and isinstance(ticket.legacy_report.meta, dict) else ''

        if not session_id:
            for comm_meta in ticket.communications.order_by('-created_at').values_list('meta', flat=True):
                if isinstance(comm_meta, dict) and comm_meta.get('session_id'):
                    session_id = str(comm_meta.get('session_id') or '')
                    break

        if not session_id:
            return

        session = ConversationSession.objects.filter(session_id=session_id).first()
        system_message = f"Admin decision on {ticket.ticket_id}: {decision} (status={status})."

        if session:
            context = session.context or {}
            history = context.get('history', [])
            history.append({
                'role': 'admin',
                'content': system_message[:500],
                'timestamp': timezone.now().isoformat(),
                'intent': 'admin_decision',
                'emotion': 'neutral',
                'confidence': 1.0,
            })
            context['history'] = history[-20:]
            session.context = context
            session.save(update_fields=['context', 'updated_at'])

        ConversationLog.objects.create(
            user=ticket.admin_user,
            session=session,
            anonymous_session_id=session_id,
            message=f"Admin decision for {ticket.ticket_id}",
            final_reply=system_message,
            confidence=1.0,
            explanation='Source: admin_decision',
            processing_time_ms=0,
        )

    @classmethod
    def _send_notifications(cls, ticket: DisputeTicket):
        app_name = getattr(settings, 'APP_NAME', 'Zunto Marketplace')

        buyer_subject = f"[{app_name}] Dispute ticket created: {ticket.ticket_id}"
        buyer_body = (
            f"Hi {ticket.buyer.get_full_name() or ticket.buyer.email},\n\n"
            f"Your dispute ticket has been created successfully.\n"
            f"Ticket ID: {ticket.ticket_id}\n"
            f"Category: {ticket.dispute_category}\n"
            f"Status: {ticket.status}\n\n"
            "This email is a notification only and cannot execute refunds or dispute actions."
        )

        cls._send_email(
            subject=buyer_subject,
            body=buyer_body,
            recipient=ticket.buyer.email,
            ticket=ticket,
            role=DisputeTicketCommunication.SENDER_SYSTEM,
            msg_type='buyer_confirmation_email',
        )

        seller_subject = f"[{app_name}] Dispute notice: {ticket.ticket_id}"
        seller_body = (
            f"Hi {ticket.seller.get_full_name() or ticket.seller.email},\n\n"
            f"A dispute has been opened by buyer {ticket.buyer.get_full_name() or ticket.buyer.email}.\n"
            f"Ticket ID: {ticket.ticket_id}\n"
            f"Category: {ticket.dispute_category}\n"
            f"Response deadline: {ticket.seller_response_due_at.isoformat()}\n\n"
            "Please provide your response and evidence in the platform chat."
        )

        cls._send_email(
            subject=seller_subject,
            body=seller_body,
            recipient=ticket.seller.email,
            ticket=ticket,
            role=DisputeTicketCommunication.SENDER_SYSTEM,
            msg_type='seller_notice_email',
        )

        if ticket.seller_type == DisputeTicket.SELLER_TYPE_VERIFIED:
            admin_emails = list(User.objects.filter(is_staff=True).exclude(email='').values_list('email', flat=True))
            if admin_emails:
                admin_subject = f"[{app_name}] Verified seller dispute alert: {ticket.ticket_id}"
                admin_body = (
                    f"A verified seller dispute ticket was opened.\n"
                    f"Ticket ID: {ticket.ticket_id}\n"
                    f"Buyer: {ticket.buyer.email}\n"
                    f"Seller: {ticket.seller.email}\n"
                    f"Category: {ticket.dispute_category}\n"
                )
                for email in admin_emails:
                    cls._send_email(
                        subject=admin_subject,
                        body=admin_body,
                        recipient=email,
                        ticket=ticket,
                        role=DisputeTicketCommunication.SENDER_SYSTEM,
                        msg_type='admin_verified_seller_alert',
                    )

    @staticmethod
    def _send_email(*, subject: str, body: str, recipient: str, ticket: DisputeTicket, role: str, msg_type: str):
        if not recipient:
            return

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@zunto.local')
        try:
            send_mail(subject, body, from_email, [recipient], fail_silently=False)
            status_label = 'sent'
        except Exception:
            logger.exception('Failed to send dispute ticket email')
            status_label = 'failed'

        DisputeTicketCommunication.objects.create(
            ticket=ticket,
            sender_role=role,
            channel=DisputeTicketCommunication.CHANNEL_EMAIL,
            message_type=msg_type,
            body=subject,
            meta={'recipient': recipient, 'delivery_status': status_label},
        )
