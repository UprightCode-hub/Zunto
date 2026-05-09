"""Deterministic, data-grounded customer service assistant."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db.models import Q
from django.utils import timezone

from chat.models import Conversation
from orders.models import Order, Payment


class CustomerServiceAgent:
    """Guided support flow that grounds replies in the user's records."""

    MAX_RECORDS = 5
    FLOW_KEY = 'customer_service_flow'
    STAGE_DISPUTE_AWAITING_DESCRIPTION = 'dispute_awaiting_description'
    STAGE_DISPUTE_AWAITING_RESOLUTION = 'dispute_awaiting_resolution'
    STAGE_DISPUTE_ESCALATED = 'dispute_escalated'

    GREETINGS = {'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'}
    SHORT_ACKS = {'yes', 'yeah', 'yep', 'ok', 'okay', 'sure', 'no', 'nope', 'nah'}
    ORDER_REFERENCE_RE = re.compile(r'\bORD[-\s][A-Z0-9]{2,12}[-\s][A-Z0-9]{2,12}\b', re.I)
    PAYMENT_REFERENCE_RE = re.compile(r'\b(?:ZUNTO_[A-Z0-9_]{8,}|PAYSTACK[-_A-Z0-9]{6,}|PAY[-_A-Z0-9]{6,}|REF[-_A-Z0-9]{6,})\b', re.I)
    ORDER_REFERENCE_HINT_RE = re.compile(r'\border\s*(?:number|no|#|id|reference|ref)\b', re.I)
    PAYMENT_REFERENCE_HINT_RE = re.compile(r'\b(?:paystack|payment|transaction)\s*(?:reference|ref|id|code)\b', re.I)

    ANGRY_TERMS = {
        'angry', 'furious', 'mad', 'unacceptable', 'ridiculous', 'nonsense',
        'worst', 'useless', 'terrible', 'horrible',
    }
    FRUSTRATION_TERMS = {
        'frustrated', 'fed up', 'tired of this', 'annoyed', 'disappointed',
        'waste of time', 'no one is helping', 'ignored me', 'still waiting',
        'this is taking too long',
    }

    PAYMENT_TERMS = {
        'payment', 'paystack', 'paid', 'charged', 'charge', 'transaction',
        'transfer', 'card', 'debit', 'credit', 'failed payment', 'duplicate charge',
    }
    REFUND_TERMS = {'refund', 'money back', 'return my money', 'reverse payment', 'reversal'}
    DELIVERY_TERMS = {'delivery', 'shipping', 'shipment', 'tracking', 'delivered', 'arrived', 'in transit', 'package'}
    DISPUTE_TERMS = {
        'dispute', 'seller', 'buyer', 'complaint', 'wrong item', 'damaged',
        'not as described', 'scam', 'fraud', 'fake', 'refused', 'problem with',
    }

    def __init__(self, session):
        self.session = session
        self.user = getattr(session, 'user', None)
        context_data = session.context_data if isinstance(session.context_data, dict) else {}
        self.flow = context_data.get(self.FLOW_KEY) if isinstance(context_data.get(self.FLOW_KEY), dict) else {}
        self.metadata: Dict[str, Any] = {
            'assistant_mode': 'customer_service',
            'retrieval_system': 'structured_customer_service_flow',
        }

    def run(self, message: str) -> Dict[str, Any]:
        text = self._clean(message)
        lower = text.lower()
        self._active_emotion = self._detect_emotion(lower)

        if not self.user:
            return self._final(
                "Please sign in first so I can pull your actual orders, payments, and buyer/seller chats.",
                intent='auth_required',
                confidence=0.95,
            )

        if self._is_active_dispute_continuation():
            return self._handle_dispute_continuation(text)

        if lower in self.GREETINGS:
            self._active_emotion = 'neutral'
            self._clear_pending()
            return self._final(
                f"Hello {self._user_name()}! I am Gigi from Zunto Customer Service. "
                "I can help with payments, refunds, deliveries, and buyer/seller disputes. "
                "What happened?",
                intent='greeting',
                confidence=0.96,
            )

        pending_kind = self.flow.get('awaiting_selection')
        if pending_kind:
            selected = self._resolve_candidate_selection(text)
            if selected:
                return self._handle_selection(selected)

        reference_result = self._handle_explicit_reference(text)
        if reference_result:
            return reference_result

        if pending_kind:
            return self._final(
                self._selection_retry_message(pending_kind),
                intent='selection_retry',
                confidence=0.78,
            )

        intent = self._detect_intent(lower)

        if intent == 'dispute':
            return self._present_dispute_choices()

        if intent == 'payment':
            return self._present_payments()

        if intent == 'delivery':
            return self._present_delivery_orders()

        if intent == 'refund':
            return self._handle_refund_request(text)

        if lower in self.SHORT_ACKS:
            return self._final(
                "I am with you. Tell me whether this is about a payment, refund, delivery, or a buyer/seller dispute, "
                "and I will pull the matching records.",
                intent='short_ack',
                confidence=0.82,
            )

        return self._final(
            "I can help with that. Is this about a payment, refund, delivery, or a buyer/seller dispute? "
            "Once you pick one, I will show the related records from your account.",
            intent='clarify_issue_type',
            confidence=0.8,
        )

    def _detect_intent(self, lower: str) -> str:
        if self._contains_any(lower, self.DISPUTE_TERMS):
            return 'dispute'
        if self._contains_any(lower, self.REFUND_TERMS):
            return 'refund'
        if self._contains_any(lower, self.PAYMENT_TERMS):
            return 'payment'
        if self._contains_any(lower, self.DELIVERY_TERMS):
            return 'delivery'
        return ''

    def _handle_explicit_reference(self, message: str) -> Optional[Dict[str, Any]]:
        lower = message.lower()

        for order_number in self._extract_order_references(message):
            order = self._get_order_by_number(order_number)
            if order:
                self.flow['selected_order_id'] = str(order.id)
                self.flow['selected_order_number'] = order.order_number
                self.flow.pop('awaiting_selection', None)
                self._save_flow()
                return self._final(
                    self._reply_for_referenced_order(order, lower),
                    intent='order_reference_matched',
                    confidence=0.96,
                )

        for reference in self._extract_payment_references(message):
            payment = self._get_payment_by_reference(reference)
            if payment:
                self.flow['selected_payment_id'] = str(payment.id)
                self.flow['selected_order_id'] = str(payment.order_id)
                self.flow['selected_order_number'] = payment.order.order_number
                self.flow['selected_payment_reference'] = payment.gateway_reference or ''
                self.flow.pop('awaiting_selection', None)
                self._save_flow()
                return self._final(
                    self._payment_selected_reply(payment),
                    intent='payment_reference_matched',
                    confidence=0.96,
                )

        if self._extract_order_references(message):
            return self._final(
                "I could not find that order number on your account. Please check the order number and send it again, or tell me whether this is about payment, refund, delivery, or a dispute.",
                intent='order_reference_not_found',
                confidence=0.76,
            )

        if self._extract_payment_references(message):
            return self._final(
                "I could not find that payment reference on your account. Please check the Paystack or transaction reference and send it again, or share the order number.",
                intent='payment_reference_not_found',
                confidence=0.76,
            )

        if self.ORDER_REFERENCE_HINT_RE.search(message):
            return self._final(
                "Send the full order number, for example ORD-20260509-ABCD, and I will pull the matching record from your account.",
                intent='order_reference_requested',
                confidence=0.78,
            )

        if self.PAYMENT_REFERENCE_HINT_RE.search(message):
            return self._final(
                "Send the Paystack or transaction reference and I will pull the matching payment record from your account.",
                intent='payment_reference_requested',
                confidence=0.78,
            )

        return None

    def _reply_for_referenced_order(self, order: Order, lower: str) -> str:
        intent = self._detect_intent(lower)
        if intent == 'payment':
            return self._payment_order_selected_reply(order)
        if intent == 'delivery':
            return self._delivery_selected_reply(order)
        if intent == 'refund':
            return self._refund_reply(order)
        if intent == 'dispute':
            self._anchor_dispute_to_order(order)
            return self._dispute_order_selected_reply(order)
        return self._order_selected_reply(order)

    def _extract_order_references(self, message: str) -> List[str]:
        refs = []
        for match in self.ORDER_REFERENCE_RE.finditer(message or ''):
            ref = re.sub(r'\s+', '-', match.group(0).upper())
            if ref not in refs:
                refs.append(ref)
        return refs

    def _extract_payment_references(self, message: str) -> List[str]:
        refs = []
        for match in self.PAYMENT_REFERENCE_RE.finditer(message or ''):
            ref = match.group(0).strip()
            if ref not in refs:
                refs.append(ref)
        return refs

    def _present_payments(self) -> Dict[str, Any]:
        payments = self._recent_payments()
        if not payments:
            orders = self._recent_orders(limit=self.MAX_RECORDS)
            if orders:
                return self._present_order_choices(
                    orders,
                    topic='payment',
                    intro=(
                        "I found these recent order payment records on your account. "
                        "Which transaction is the payment issue tied to?"
                    ),
                )
            return self._final(
                "I could not find payment or order records on your account yet. "
                "Share the Paystack reference or order number and I will help escalate it with that identifier.",
                intent='payment_no_records',
                confidence=0.75,
            )

        candidates = []
        lines = ["I found these recent payment records on your account. Which transaction has the problem?"]
        for index, payment in enumerate(payments, start=1):
            candidates.append(self._candidate_for_payment(index, payment))
            lines.append(f"{index}. {self._payment_line(payment)}")
        lines.append("Reply with the number, payment reference, or order number.")
        self._set_candidates('payment', 'payment', candidates)
        self.metadata['records_presented'] = self._public_candidates(candidates)
        return self._final('\n'.join(lines), intent='payment_lookup', confidence=0.94)

    def _present_delivery_orders(self) -> Dict[str, Any]:
        orders = self._delivery_orders()
        if not orders:
            orders = self._recent_orders(limit=self.MAX_RECORDS)
        if not orders:
            return self._final(
                "I could not find delivery-related orders on your account yet. "
                "Share an order number if you have one and I will help trace it.",
                intent='delivery_no_records',
                confidence=0.75,
            )
        return self._present_order_choices(
            orders,
            topic='delivery',
            intro="I found these orders that are in transit, processing, or recent. Which delivery is affected?",
        )

    def _present_dispute_choices(self) -> Dict[str, Any]:
        orders = self._recent_orders(limit=self.MAX_RECORDS)
        conversations = self._recent_conversations(limit=self.MAX_RECORDS)
        candidates: List[Dict[str, Any]] = []
        lines = [
            "I can help with the dispute, but first I want to anchor it to the real record. "
            "Which order or chat is involved?"
        ]

        if orders:
            lines.append("\nRecent orders:")
            for index, order in enumerate(orders, start=1):
                candidates.append(self._candidate_for_order(index, order))
                lines.append(f"{index}. {self._order_line(order)}")

        if conversations:
            lines.append("\nActive buyer/seller chats:")
            for index, conversation in enumerate(conversations, start=1):
                key = f"C{index}"
                candidates.append(self._candidate_for_conversation(key, conversation))
                lines.append(f"{key}. {self._conversation_line(conversation)}")

        if not candidates:
            return self._final(
                "I could not find recent orders or buyer/seller chats for your account. "
                "Share the order number, product, or seller/buyer name and I will help create an escalation with that context.",
                intent='dispute_no_records',
                confidence=0.76,
            )

        lines.append("Reply with an order number, list number, or chat code like C1.")
        self._set_candidates('dispute', 'order_or_conversation', candidates)
        self.metadata['records_presented'] = self._public_candidates(candidates)
        return self._final('\n'.join(lines), intent='dispute_lookup', confidence=0.94)

    def _present_order_choices(self, orders: Iterable[Order], *, topic: str, intro: str) -> Dict[str, Any]:
        candidates = []
        lines = [intro]
        for index, order in enumerate(orders, start=1):
            candidates.append(self._candidate_for_order(index, order))
            lines.append(f"{index}. {self._order_line(order)}")
        lines.append("Reply with the number or order number.")
        self._set_candidates(topic, 'order', candidates)
        self.metadata['records_presented'] = self._public_candidates(candidates)
        return self._final('\n'.join(lines), intent=f'{topic}_order_lookup', confidence=0.92)

    def _handle_selection(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        kind = candidate.get('kind')
        topic = self.flow.get('topic') or kind

        if kind == 'payment':
            payment = self._get_payment(candidate.get('payment_id'))
            if not payment:
                return self._final("I could not reload that payment record. Please pick another one.", intent='payment_missing', confidence=0.65)
            self.flow['selected_payment_id'] = str(payment.id)
            self.flow['selected_order_id'] = str(payment.order_id)
            self.flow['selected_order_number'] = payment.order.order_number
            self.flow['selected_payment_reference'] = payment.gateway_reference or ''
            self.flow.pop('awaiting_selection', None)
            self._save_flow()
            return self._final(self._payment_selected_reply(payment), intent='payment_selected', confidence=0.95)

        if kind == 'order':
            order = self._get_order(candidate.get('order_id'))
            if not order:
                return self._final("I could not reload that order. Please pick another one.", intent='order_missing', confidence=0.65)
            self.flow['selected_order_id'] = str(order.id)
            self.flow['selected_order_number'] = order.order_number
            self.flow.pop('awaiting_selection', None)
            if topic == 'delivery':
                self._save_flow()
                return self._final(self._delivery_selected_reply(order), intent='delivery_selected', confidence=0.95)
            if topic == 'dispute':
                self._anchor_dispute_to_order(order)
                return self._final(self._dispute_order_selected_reply(order), intent='dispute_order_selected', confidence=0.95)
            if topic == 'refund':
                self._save_flow()
                return self._final(self._refund_reply(order), intent='refund_grounded', confidence=0.94)
            if topic == 'payment':
                self._save_flow()
                return self._final(self._payment_order_selected_reply(order), intent='payment_order_selected', confidence=0.93)
            self._save_flow()
            return self._final(self._order_selected_reply(order), intent='order_selected', confidence=0.9)

        if kind == 'conversation':
            conversation = self._get_conversation(candidate.get('conversation_id'))
            if not conversation:
                return self._final("I could not reload that chat. Please pick another one.", intent='conversation_missing', confidence=0.65)
            self.flow['selected_conversation_id'] = str(conversation.id)
            self.flow.pop('awaiting_selection', None)
            self._anchor_dispute_to_conversation(conversation)
            return self._final(self._conversation_selected_reply(conversation), intent='dispute_conversation_selected', confidence=0.95)

        return self._final("I could not identify that selection. Please send the number or reference again.", intent='selection_unknown', confidence=0.65)

    def _handle_refund_request(self, message: str) -> Dict[str, Any]:
        payment = self._selected_payment()
        order = self._selected_order()
        if payment and not order:
            order = payment.order

        if order:
            return self._final(self._refund_reply(order, payment=payment), intent='refund_grounded', confidence=0.94)

        paid_orders = list(
            self._orders_queryset()
            .filter(payment_status='paid')
            .exclude(status__in=['cancelled', 'refunded'])
            .order_by('-created_at')[: self.MAX_RECORDS]
        )
        if paid_orders:
            return self._present_order_choices(
                paid_orders,
                topic='refund',
                intro="I found these paid orders that can be reviewed for a refund. Which one should I use?",
            )

        return self._final(
            "I could not find a paid order eligible for refund review on your account. "
            "If you have a Paystack reference or order number, send it and I will anchor the case to that record.",
            intent='refund_no_records',
            confidence=0.76,
        )

    def _is_active_dispute_continuation(self) -> bool:
        if self.flow.get('awaiting_selection'):
            return False
        if self.flow.get('topic') != 'dispute':
            return False
        if self.flow.get('stage') not in {
            self.STAGE_DISPUTE_AWAITING_DESCRIPTION,
            self.STAGE_DISPUTE_AWAITING_RESOLUTION,
            self.STAGE_DISPUTE_ESCALATED,
        }:
            return False
        return bool(self.flow.get('selected_order_id') or self.flow.get('selected_conversation_id'))

    def _handle_dispute_continuation(self, message: str) -> Dict[str, Any]:
        stage = self.flow.get('stage')

        if stage == self.STAGE_DISPUTE_AWAITING_DESCRIPTION:
            return self._record_dispute_description(message)

        if stage == self.STAGE_DISPUTE_AWAITING_RESOLUTION:
            return self._record_dispute_resolution(message)

        context = self._dispute_context()
        order_reference = context.get('order_reference') or 'the linked record'
        return self._final(
            f"This dispute is already marked for Zunto support review on {order_reference}. "
            f"Summary: {self._dispute_summary_sentence(context)}",
            intent='dispute_already_escalated',
            confidence=0.9,
        )

    def _record_dispute_description(self, message: str) -> Dict[str, Any]:
        context = self._dispute_context()
        existing_description = self._clean(context.get('description', ''))
        new_description = self._clean(message)
        if existing_description and new_description.lower() not in existing_description.lower():
            context['description'] = f"{existing_description} {new_description}".strip()
        else:
            context['description'] = new_description or existing_description

        self.flow['dispute_context'] = context
        self.flow['stage'] = self.STAGE_DISPUTE_AWAITING_RESOLUTION
        self._save_flow()

        return self._final(
            "I understand. I have added that to the dispute details.\n\n"
            f"Dispute summary so far:\n{self._dispute_summary_lines(context)}\n\n"
            "What resolution do you want: refund, replacement, or escalation to Zunto support team?",
            intent='dispute_description_collected',
            confidence=0.94,
        )

    def _record_dispute_resolution(self, message: str) -> Dict[str, Any]:
        context = self._dispute_context()
        resolution_key, resolution_label = self._detect_desired_resolution(message)

        if not resolution_key:
            extra_detail = self._clean(message)
            existing_description = self._clean(context.get('description', ''))
            if extra_detail and extra_detail.lower() not in existing_description.lower():
                context['description'] = f"{existing_description} {extra_detail}".strip()
            self.flow['dispute_context'] = context
            self._save_flow()
            return self._final(
                "I have added that detail too.\n\n"
                f"Dispute summary so far:\n{self._dispute_summary_lines(context)}\n\n"
                "Please choose the resolution you want: refund, replacement, or escalation to Zunto support team.",
                intent='dispute_resolution_needed',
                confidence=0.88,
            )

        context['desired_resolution'] = resolution_label
        self.flow['dispute_context'] = context

        if resolution_key == 'escalation':
            ticket_reference = self._create_dispute_ticket_if_possible(context, resolution_label)
            if ticket_reference:
                context['ticket_reference'] = ticket_reference
            self.flow['dispute_context'] = context
            self.flow['stage'] = self.STAGE_DISPUTE_ESCALATED
            self._save_flow()
            support_case = f"\nSupport case: {ticket_reference}" if ticket_reference else ""
            return self._final(
                "I have escalated this dispute to the Zunto support team.\n"
                f"Order: {context.get('order_reference', 'not recorded')}\n"
                f"Items: {context.get('items', 'not recorded')}\n"
                f"Buyer: {context.get('buyer', 'not listed')}\n"
                f"Sellers: {context.get('sellers', 'not listed')}\n"
                f"Issue: {context.get('description', 'not recorded')}\n"
                f"Requested resolution: {resolution_label}"
                f"{support_case}\n\n"
                "The support team will review the order record, buyer/seller identities, and related chat context.",
                intent='dispute_escalated',
                confidence=0.96,
            )

        self.flow['stage'] = self.STAGE_DISPUTE_AWAITING_RESOLUTION
        self._save_flow()
        return self._final(
            f"Got it. I have recorded your requested resolution as {resolution_label}.\n\n"
            f"Dispute summary so far:\n{self._dispute_summary_lines(context)}\n\n"
            "If you want Zunto support to review this now, say \"escalate to Zunto support\".",
            intent='dispute_resolution_recorded',
            confidence=0.92,
        )

    def _anchor_dispute_to_order(self, order: Order) -> None:
        self.flow.update({
            'topic': 'dispute',
            'stage': self.STAGE_DISPUTE_AWAITING_DESCRIPTION,
            'selected_order_id': str(order.id),
            'selected_order_number': order.order_number,
            'dispute_context': self._build_order_dispute_context(order),
        })
        self._save_flow()

    def _anchor_dispute_to_conversation(self, conversation: Conversation) -> None:
        self.flow.update({
            'topic': 'dispute',
            'stage': self.STAGE_DISPUTE_AWAITING_DESCRIPTION,
            'selected_conversation_id': str(conversation.id),
            'dispute_context': self._build_conversation_dispute_context(conversation),
        })
        self._save_flow()

    def _build_order_dispute_context(self, order: Order) -> Dict[str, Any]:
        related_chats = self._conversations_for_order(order)
        chat_summaries = [self._conversation_public_label(chat) for chat in related_chats]
        return {
            'order_reference': order.order_number,
            'items': self._order_summary(order),
            'amount': self._money(order.total_amount),
            'order_status': order.status,
            'payment_status': order.payment_status,
            'date': self._date(order.created_at),
            'buyer': self._person(order.customer),
            'sellers': ', '.join(self._seller_names(order)) or 'not listed',
            'related_chats': chat_summaries,
            'description': self._clean(self._dispute_context().get('description', '')),
            'desired_resolution': self._clean(self._dispute_context().get('desired_resolution', '')),
        }

    def _build_conversation_dispute_context(self, conversation: Conversation) -> Dict[str, Any]:
        last_message = conversation.get_last_message()
        last_text = self._clean(getattr(last_message, 'content', '') or '')[:120] if last_message else 'no messages yet'
        return {
            'order_reference': '',
            'items': getattr(conversation.product, 'title', 'Unknown product'),
            'amount': '',
            'order_status': '',
            'payment_status': '',
            'date': self._date(conversation.updated_at),
            'buyer': self._person(conversation.buyer),
            'sellers': self._person(conversation.seller),
            'related_chats': [self._conversation_public_label(conversation)],
            'last_message': last_text,
            'description': self._clean(self._dispute_context().get('description', '')),
            'desired_resolution': self._clean(self._dispute_context().get('desired_resolution', '')),
        }

    def _dispute_context(self) -> Dict[str, Any]:
        context = self.flow.get('dispute_context')
        return dict(context) if isinstance(context, dict) else {}

    def _dispute_summary_lines(self, context: Dict[str, Any]) -> str:
        lines = []
        if context.get('order_reference'):
            lines.append(f"Order: {context['order_reference']}")
        lines.append(f"Items: {context.get('items') or 'not recorded'}")
        if context.get('amount'):
            lines.append(f"Amount: {context['amount']}")
        if context.get('date'):
            lines.append(f"Date: {context['date']}")
        if context.get('buyer'):
            lines.append(f"Buyer: {context['buyer']}")
        if context.get('sellers'):
            lines.append(f"Sellers: {context['sellers']}")
        if context.get('description'):
            lines.append(f"Issue details: {context['description']}")
        if context.get('desired_resolution'):
            lines.append(f"Requested resolution: {context['desired_resolution']}")
        related_chats = context.get('related_chats') if isinstance(context.get('related_chats'), list) else []
        if related_chats:
            lines.append(f"Related chat context: {'; '.join(related_chats[:3])}")
        return '\n'.join(lines)

    def _dispute_summary_sentence(self, context: Dict[str, Any]) -> str:
        parts = []
        if context.get('items'):
            parts.append(f"items: {context['items']}")
        if context.get('description'):
            parts.append(f"issue: {context['description']}")
        if context.get('desired_resolution'):
            parts.append(f"requested resolution: {context['desired_resolution']}")
        return '; '.join(parts) if parts else 'details are attached to the session.'

    def _detect_desired_resolution(self, message: str) -> Tuple[str, str]:
        lower = (message or '').lower()
        if any(term in lower for term in {'escalate', 'escalated', 'support', 'zunto support', 'admin', 'team review'}):
            return 'escalation', 'escalation to Zunto support team'
        if any(term in lower for term in {'replacement', 'replace', 'exchange', 'new item'}):
            return 'replacement', 'replacement'
        if any(term in lower for term in self.REFUND_TERMS):
            return 'refund', 'refund'
        return '', ''

    def _detect_dispute_category(self, description: str) -> str:
        lower = (description or '').lower()
        if any(term in lower for term in {'recorded', 'message', 'chat', 'said', 'say', 'lied', 'false statement'}):
            return 'communication_issue'
        if any(term in lower for term in {'delivery', 'delivered', 'shipping', 'package', 'arrived'}):
            return 'delivery_issue'
        if any(term in lower for term in {'damaged', 'broken', 'wrong item', 'not as described', 'fake'}):
            return 'quality_issue'
        if any(term in lower for term in {'payment', 'charged', 'refund', 'paid'}):
            return 'payment_issue'
        return 'other'

    def _create_dispute_ticket_if_possible(self, context: Dict[str, Any], desired_resolution: str) -> str:
        order = self._selected_order()
        if not order:
            return ''

        product_id = self._single_product_id(order)
        try:
            from assistant.services.dispute_ticket_service import DisputeTicketError, DisputeTicketService

            ticket = DisputeTicketService.create_ticket(
                buyer=self.user,
                order_id=str(order.id),
                product_id=product_id,
                dispute_category=self._detect_dispute_category(context.get('description', '')),
                description=context.get('description') or 'Dispute details provided in customer service chat.',
                desired_resolution=desired_resolution,
                session_id=self.session.session_id,
                evaluate_on_create=False,
            )
            return ticket.ticket_id
        except DisputeTicketError as exc:
            self.metadata['ticket_creation_status'] = 'not_created'
            self.metadata['ticket_creation_reason'] = str(exc)
            return ''
        except Exception as exc:
            self.metadata['ticket_creation_status'] = 'failed'
            self.metadata['ticket_creation_reason'] = type(exc).__name__
            return ''

    def _single_product_id(self, order: Order) -> Optional[str]:
        product_ids = []
        for item in order.items.all():
            if item.product_id and item.product_id not in product_ids:
                product_ids.append(item.product_id)
        if len(product_ids) == 1:
            return str(product_ids[0])
        return None

    def _payment_selected_reply(self, payment: Payment) -> str:
        order = payment.order
        lines = [
            "Got it. I have linked this issue to this payment record:",
            f"Payment reference: {payment.gateway_reference or 'not recorded'}",
            f"Order: {order.order_number}",
            f"Amount: {self._money(payment.amount)}",
            f"Payment status: {payment.status}",
            f"Order status: {order.status} / payment status: {order.payment_status}",
            f"Date: {self._date(payment.created_at)}",
            "",
            "What should I help with on this transaction: verify a failed payment, investigate a duplicate charge, or request a refund?",
        ]
        return '\n'.join(lines)

    def _order_selected_reply(self, order: Order) -> str:
        return (
            f"I have linked this to order {order.order_number}: {self._order_summary(order)}. "
            f"Current status is {order.status}, payment status is {order.payment_status}, total is {self._money(order.total_amount)}. "
            "Tell me what went wrong on this order."
        )

    def _payment_order_selected_reply(self, order: Order) -> str:
        reference = order.payment_reference or 'not recorded'
        return (
            f"Got it. I have linked this payment issue to order {order.order_number}.\n"
            f"Payment reference: {reference}\n"
            f"Amount: {self._money(order.total_amount)}\n"
            f"Payment method: {order.payment_method}\n"
            f"Order status: {order.status} / payment status: {order.payment_status}\n"
            f"Date: {self._date(order.created_at)}\n\n"
            "What should I help with on this transaction: verify a debit, investigate a failed/duplicate payment, or request a refund?"
        )

    def _delivery_selected_reply(self, order: Order) -> str:
        tracking = order.tracking_number or 'not added yet'
        shipped = self._date(order.shipped_at) if order.shipped_at else 'not marked shipped yet'
        return (
            f"I have order {order.order_number}: {self._order_summary(order)}. "
            f"Order status is {order.status}, tracking number is {tracking}, shipped date is {shipped}. "
            "Tell me what delivery problem you are seeing, for example late delivery, wrong address, or marked delivered but not received."
        )

    def _dispute_order_selected_reply(self, order: Order) -> str:
        party_lines = self._order_party_lines(order)
        related_chats = self._conversations_for_order(order)
        chat_text = '; '.join(self._conversation_public_label(chat) for chat in related_chats) if related_chats else 'no linked chat found'
        return (
            f"I have linked the dispute to order {order.order_number}.\n"
            f"Order items: {self._order_summary(order)}\n"
            f"Buyer: {self._person(order.customer)}\n"
            f"{party_lines}\n"
            f"Related chat context: {chat_text}\n\n"
            "Now tell me what happened and what resolution you want. I will keep the order reference, seller/buyer identity, and chat context attached."
        )

    def _conversation_selected_reply(self, conversation: Conversation) -> str:
        last_message = conversation.get_last_message()
        last_text = self._clean(getattr(last_message, 'content', '') or '')[:120] if last_message else 'no messages yet'
        return (
            "I have linked the dispute to this buyer/seller chat.\n"
            f"Product: {getattr(conversation.product, 'title', 'Unknown product')}\n"
            f"Buyer: {self._person(conversation.buyer)}\n"
            f"Seller: {self._person(conversation.seller)}\n"
            f"Last message: {last_text}\n\n"
            "Tell me what happened in this chat and the resolution you want."
        )

    def _refund_reply(self, order: Order, payment: Optional[Payment] = None) -> str:
        payment_line = ''
        if payment:
            payment_line = f" Payment reference: {payment.gateway_reference or 'not recorded'}, status {payment.status}."

        if order.payment_status != 'paid':
            return (
                f"I found order {order.order_number}, but its payment status is {order.payment_status}, so I cannot treat it as a paid refund yet."
                f"{payment_line} If you were debited, send the bank/Paystack reference and I will help investigate the payment first."
            )

        if order.status in {'cancelled', 'refunded'}:
            return (
                f"Order {order.order_number} is already marked {order.status}.{payment_line} "
                "If the money has not reached you, tell me when the refund was expected and I will help trace it."
            )

        return (
            f"Refund review will be tied to order {order.order_number}: {self._order_summary(order)}. "
            f"The order is {order.status}, payment status is paid, total is {self._money(order.total_amount)}.{payment_line}\n\n"
            "What is the refund reason: not delivered, wrong item, damaged item, duplicate charge, or something else?"
        )

    def _selection_retry_message(self, pending_kind: str) -> str:
        candidates = self.flow.get('candidates') if isinstance(self.flow.get('candidates'), list) else []
        if not candidates:
            self._clear_pending()
            return "I lost the previous list. Tell me the issue type again and I will pull fresh records."
        return "I could not match that to the records I showed. Reply with one of the numbers, an order number, payment reference, or chat code."

    def _set_candidates(self, topic: str, awaiting_selection: str, candidates: List[Dict[str, Any]]) -> None:
        self.flow.update({
            'topic': topic,
            'awaiting_selection': awaiting_selection,
            'candidates': candidates,
        })
        self._save_flow()

    def _resolve_candidate_selection(self, message: str) -> Optional[Dict[str, Any]]:
        normalized = self._normalize_ref(message)
        candidates = self.flow.get('candidates') if isinstance(self.flow.get('candidates'), list) else []
        if not normalized:
            return None

        simple_key = self._simple_selection_key(message)
        if simple_key:
            for candidate in candidates:
                key_refs = [candidate.get('key'), candidate.get('display_key')]
                if any(self._normalize_ref(ref) == simple_key for ref in key_refs):
                    return candidate
            return None

        for candidate in candidates:
            refs = [candidate.get('key'), candidate.get('display_key')]
            refs.extend(candidate.get('refs') or [])
            for ref in refs:
                normalized_ref = self._normalize_ref(ref)
                if not normalized_ref:
                    continue
                if normalized == normalized_ref:
                    return candidate
                if len(normalized) >= 6 and len(normalized_ref) >= 6 and (
                    normalized_ref in normalized or normalized in normalized_ref
                ):
                    return candidate
        return None

    def _candidate_for_payment(self, index: int, payment: Payment) -> Dict[str, Any]:
        order = payment.order
        return {
            'kind': 'payment',
            'key': str(index),
            'payment_id': str(payment.id),
            'order_id': str(order.id),
            'order_number': order.order_number,
            'payment_reference': payment.gateway_reference or '',
            'refs': [payment.gateway_reference, order.order_number],
            'label': self._payment_line(payment),
        }

    def _candidate_for_order(self, index: int, order: Order) -> Dict[str, Any]:
        return {
            'kind': 'order',
            'key': str(index),
            'order_id': str(order.id),
            'order_number': order.order_number,
            'refs': [order.order_number],
            'label': self._order_line(order),
        }

    def _candidate_for_conversation(self, key: str, conversation: Conversation) -> Dict[str, Any]:
        return {
            'kind': 'conversation',
            'key': str(key).lower(),
            'display_key': key,
            'conversation_id': str(conversation.id),
            'refs': [getattr(conversation.product, 'title', '')],
            'label': self._conversation_line(conversation),
        }

    def _recent_payments(self) -> List[Payment]:
        return list(
            Payment.objects.filter(order__customer=self.user)
            .select_related('order', 'order__customer')
            .prefetch_related('order__items__seller', 'order__items__product')
            .order_by('-created_at')[: self.MAX_RECORDS]
        )

    def _delivery_orders(self) -> List[Order]:
        return list(
            self._orders_queryset()
            .filter(status__in=['paid', 'processing', 'shipped', 'pending'])
            .order_by('-created_at')[: self.MAX_RECORDS]
        )

    def _recent_orders(self, *, limit: int) -> List[Order]:
        return list(self._orders_queryset().order_by('-created_at')[:limit])

    def _orders_queryset(self):
        return (
            Order.objects.filter(Q(customer=self.user) | Q(items__seller=self.user))
            .select_related('customer')
            .prefetch_related('items__seller', 'items__product')
            .distinct()
        )

    def _recent_conversations(self, *, limit: int) -> List[Conversation]:
        return list(
            Conversation.objects.filter(Q(buyer=self.user) | Q(seller=self.user))
            .select_related('buyer', 'seller', 'product')
            .order_by('-updated_at')[:limit]
        )

    def _conversations_for_order(self, order: Order) -> List[Conversation]:
        product_ids = [item.product_id for item in order.items.all() if item.product_id]
        if not product_ids:
            return []
        participant_filter = Q(buyer=order.customer) | Q(seller=order.customer)
        for item in order.items.all():
            if item.seller_id:
                participant_filter |= Q(buyer_id=item.seller_id) | Q(seller_id=item.seller_id)
        return list(
            Conversation.objects.filter(product_id__in=product_ids)
            .filter(participant_filter)
            .select_related('buyer', 'seller', 'product')
            .order_by('-updated_at')[: self.MAX_RECORDS]
        )

    def _get_payment(self, payment_id: Any) -> Optional[Payment]:
        if not payment_id:
            return None
        return (
            Payment.objects.filter(id=payment_id, order__customer=self.user)
            .select_related('order', 'order__customer')
            .prefetch_related('order__items__seller', 'order__items__product')
            .first()
        )

    def _get_payment_by_reference(self, reference: str) -> Optional[Payment]:
        if not reference:
            return None
        return (
            Payment.objects.filter(order__customer=self.user)
            .filter(Q(gateway_reference__iexact=reference) | Q(order__payment_reference__iexact=reference))
            .select_related('order', 'order__customer')
            .prefetch_related('order__items__seller', 'order__items__product')
            .first()
        )

    def _get_order(self, order_id: Any) -> Optional[Order]:
        if not order_id:
            return None
        return self._orders_queryset().filter(id=order_id).first()

    def _get_order_by_number(self, order_number: str) -> Optional[Order]:
        if not order_number:
            return None
        return self._orders_queryset().filter(order_number__iexact=order_number).first()

    def _get_conversation(self, conversation_id: Any) -> Optional[Conversation]:
        if not conversation_id:
            return None
        return (
            Conversation.objects.filter(id=conversation_id)
            .filter(Q(buyer=self.user) | Q(seller=self.user))
            .select_related('buyer', 'seller', 'product')
            .first()
        )

    def _selected_payment(self) -> Optional[Payment]:
        return self._get_payment(self.flow.get('selected_payment_id'))

    def _selected_order(self) -> Optional[Order]:
        return self._get_order(self.flow.get('selected_order_id'))

    def _payment_line(self, payment: Payment) -> str:
        order = payment.order
        return (
            f"{payment.gateway_reference or 'payment reference not recorded'} - order {order.order_number} - "
            f"{self._money(payment.amount)} - payment {payment.status} - order {order.status}/{order.payment_status} - "
            f"{self._date(payment.created_at)}"
        )

    def _order_line(self, order: Order) -> str:
        return (
            f"{order.order_number} - {self._order_summary(order)} - "
            f"{order.status}/{order.payment_status} - {self._money(order.total_amount)} - "
            f"{self._date(order.created_at)} - {self._order_parties_short(order)}"
        )

    def _conversation_line(self, conversation: Conversation) -> str:
        return (
            f"chat about {getattr(conversation.product, 'title', 'Unknown product')} - "
            f"buyer {self._person(conversation.buyer)} / seller {self._person(conversation.seller)} - "
            f"updated {self._date(conversation.updated_at)}"
        )

    def _order_summary(self, order: Order) -> str:
        items = list(order.items.all())
        if not items:
            return 'no items listed'
        names = [f"{item.quantity}x {item.product_name}" for item in items[:3]]
        if len(items) > 3:
            names.append(f"+{len(items) - 3} more")
        return ', '.join(names)

    def _order_parties_short(self, order: Order) -> str:
        if order.customer_id == getattr(self.user, 'id', None):
            sellers = self._seller_names(order)
            return f"seller(s): {', '.join(sellers) if sellers else 'not listed'}"
        return f"buyer: {self._person(order.customer)}"

    def _order_party_lines(self, order: Order) -> str:
        seller_lines = []
        seen = set()
        for item in order.items.all():
            seller = item.seller
            seller_key = getattr(seller, 'id', None)
            if seller_key in seen:
                continue
            seen.add(seller_key)
            seller_lines.append(f"Seller: {self._person(seller)}")
        return '\n'.join(seller_lines) if seller_lines else 'Seller: not listed'

    def _seller_names(self, order: Order) -> List[str]:
        names = []
        seen = set()
        for item in order.items.all():
            seller = item.seller
            seller_id = getattr(seller, 'id', None)
            if seller_id in seen:
                continue
            seen.add(seller_id)
            names.append(self._person(seller))
        return names

    def _person(self, user) -> str:
        if not user:
            return 'not listed'
        name = (user.get_full_name() or '').strip()
        email = getattr(user, 'email', '') or ''
        return name or email or 'not listed'

    def _user_name(self) -> str:
        name = (self.user.get_full_name() or '').strip()
        if name:
            return name.split()[0]
        first_name = getattr(self.user, 'first_name', '').strip()
        if first_name:
            return first_name
        email = getattr(self.user, 'email', '') or ''
        return email.split('@')[0] if email else 'there'

    def _money(self, value: Any) -> str:
        try:
            number = Decimal(str(value or 0))
        except (InvalidOperation, ValueError, TypeError):
            number = Decimal('0')
        return f"NGN {number:,.2f}"

    def _date(self, value: Any) -> str:
        if not value:
            return 'not recorded'
        try:
            return timezone.localtime(value).strftime('%Y-%m-%d %H:%M')
        except Exception:
            return str(value)

    def _contains_any(self, lower: str, terms: Iterable[str]) -> bool:
        return any(term in lower for term in terms)

    def _conversation_public_label(self, conversation: Conversation) -> str:
        return (
            f"{getattr(conversation.product, 'title', 'Unknown product')} chat with "
            f"buyer {self._person(conversation.buyer)} and seller {self._person(conversation.seller)}, "
            f"updated {self._date(conversation.updated_at)}"
        )

    def _detect_emotion(self, lower: str) -> str:
        if self._contains_any(lower, self.ANGRY_TERMS):
            return 'angry'
        if self._contains_any(lower, self.FRUSTRATION_TERMS):
            return 'frustrated'
        return 'neutral'

    def _apply_empathy_prefix(self, reply: str) -> str:
        emotion = getattr(self, '_active_emotion', 'neutral')
        if emotion not in {'angry', 'frustrated'}:
            return reply

        lowered = reply.lower().strip()
        already_warm = lowered.startswith((
            "i'm sorry",
            "i understand",
            "i hear",
            "your safety",
        ))
        if already_warm:
            return reply

        if emotion == 'angry':
            prefix = "I'm sorry this has been so frustrating."
        else:
            prefix = "I hear you. Let's sort this out carefully."
        self.metadata['empathy_applied'] = True
        return f"{prefix} {reply}"

    def _normalize_ref(self, value: Any) -> str:
        return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())

    def _simple_selection_key(self, message: str) -> str:
        match = re.fullmatch(
            r'\s*(?:#|no\.?|number|option|order)?\s*([a-z]?\d{1,3})\s*\.?\s*',
            str(message or '').strip().lower(),
        )
        return self._normalize_ref(match.group(1)) if match else ''

    def _clean(self, value: Any) -> str:
        return re.sub(r'\s+', ' ', str(value or '').strip())

    def _public_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self._public_candidate(candidate) for candidate in candidates]

    def _public_candidate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        public = {
            'kind': candidate.get('kind'),
            'key': candidate.get('display_key') or candidate.get('key'),
            'label': candidate.get('label'),
        }
        if candidate.get('order_number'):
            public['order_number'] = candidate.get('order_number')
        if candidate.get('payment_reference'):
            public['payment_reference'] = candidate.get('payment_reference')
        return public

    def _public_flow_state(self) -> Dict[str, Any]:
        context = self._dispute_context()
        state = {
            'topic': self.flow.get('topic'),
            'stage': self.flow.get('stage'),
            'awaiting_selection': self.flow.get('awaiting_selection'),
        }
        order_reference = self.flow.get('selected_order_number') or context.get('order_reference')
        if order_reference:
            state['selected_order_reference'] = order_reference
        payment_reference = self.flow.get('selected_payment_reference')
        if payment_reference:
            state['selected_payment_reference'] = payment_reference
        if context.get('desired_resolution'):
            state['desired_resolution'] = context.get('desired_resolution')
        return state

    def _clear_pending(self) -> None:
        self.flow.pop('awaiting_selection', None)
        self.flow.pop('candidates', None)
        self._save_flow()

    def _save_flow(self) -> None:
        context_data = self.session.context_data if isinstance(self.session.context_data, dict) else {}
        context_data[self.FLOW_KEY] = self.flow
        self.session.context_data = context_data
        self.session.save(update_fields=['context_data', 'updated_at'])

    def _final(self, reply: str, *, intent: str, confidence: float) -> Dict[str, Any]:
        reply = self._apply_empathy_prefix(reply)
        self.metadata['intent'] = intent
        self.metadata['emotion'] = getattr(self, '_active_emotion', 'neutral')
        self.metadata['flow_state'] = self._public_flow_state()
        return {
            'reply': reply,
            'confidence': confidence,
            'source': 'customer_service_agent',
            'metadata': self.metadata,
        }
