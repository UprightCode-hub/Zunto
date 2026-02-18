"""Assistant mode normalization and policy helpers."""

from __future__ import annotations

from typing import Dict

ASSISTANT_MODE_HOMEPAGE_RECO = 'homepage_reco'
ASSISTANT_MODE_INBOX_GENERAL = 'inbox_general'
ASSISTANT_MODE_CUSTOMER_SERVICE = 'customer_service'

DEFAULT_ASSISTANT_MODE = ASSISTANT_MODE_INBOX_GENERAL

LEGACY_LANE_TO_MODE = {
    'inbox': ASSISTANT_MODE_INBOX_GENERAL,
    'general': ASSISTANT_MODE_INBOX_GENERAL,
    'customer_service': ASSISTANT_MODE_CUSTOMER_SERVICE,
    'dispute': ASSISTANT_MODE_CUSTOMER_SERVICE,
    'homepage_reco': ASSISTANT_MODE_HOMEPAGE_RECO,
}

MODE_TO_LEGACY_LANE = {
    ASSISTANT_MODE_HOMEPAGE_RECO: 'inbox',
    ASSISTANT_MODE_INBOX_GENERAL: 'inbox',
    ASSISTANT_MODE_CUSTOMER_SERVICE: 'customer_service',
}


def normalize_assistant_mode(request_data: Dict) -> str:
    mode = (request_data.get('assistant_mode') or '').strip().lower()
    if mode in MODE_TO_LEGACY_LANE:
        return mode

    lane = (request_data.get('assistant_lane') or '').strip().lower()
    if lane in LEGACY_LANE_TO_MODE:
        return LEGACY_LANE_TO_MODE[lane]

    return DEFAULT_ASSISTANT_MODE


def resolve_legacy_lane(assistant_mode: str) -> str:
    return MODE_TO_LEGACY_LANE.get(assistant_mode, 'inbox')


def is_dispute_message(message: str) -> bool:
    text = (message or '').lower()
    keywords = {
        'dispute', 'complaint', 'issue', 'problem', 'refund', 'scam',
        'seller', 'buyer', 'order issue', 'did not receive', 'not delivered',
        'damaged', 'chargeback', 'wrong item', 'fake product'
    }
    return any(keyword in text for keyword in keywords)


def is_recommendation_message(message: str) -> bool:
    text = (message or '').lower()
    keywords = {
        'recommend', 'recommendation', 'suggest product', 'what should i buy',
        'best for me', 'looking for', 'find me', 'which product', 'product suggestion'
    }
    return any(keyword in text for keyword in keywords)


def mode_gate_response(mode: str, message: str):
    """Return deterministic policy response if message is out-of-scope for mode."""
    if mode == ASSISTANT_MODE_HOMEPAGE_RECO:
        if is_dispute_message(message):
            return (
                "For disputes, please use the Customer Service assistant. "
                "Homepage assistant is for product recommendations only."
            )
        return None

    if mode == ASSISTANT_MODE_INBOX_GENERAL and is_recommendation_message(message):
        return (
            "For personalized product recommendations, please start from the homepage assistant. "
            "This AI inbox is for general marketplace Q&A."
        )

    if mode == ASSISTANT_MODE_CUSTOMER_SERVICE and not is_dispute_message(message):
        return (
            "Customer Service mode is for disputes only. "
            "Please describe the dispute, affected order/product, and timeline."
        )

    return None
