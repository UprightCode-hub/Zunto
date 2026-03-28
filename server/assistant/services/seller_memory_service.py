import logging
import re
import threading
from typing import Dict, List, Optional

from accounts.models import SellerProfile, User

logger = logging.getLogger(__name__)


class SellerMemoryService:
    """Rule-based seller memory updater. Designed to fail silently."""

    _PIDGIN_TOKENS = {
        'abeg', 'dey', 'waka', 'wey', 'na', 'oga', 'sha', 'ehen', 'una', 'pls',
        'no wahala', 'how far', 'sef', 'make we', 'fit',
    }
    _CASUAL_TOKENS = {
        'abeg', 'hey', 'hi', 'yo', 'bro', 'sis', 'buddy', 'lol', 'haha', '🔥', '😊', '😅',
    }
    _FORMAL_TOKENS = {
        'please', 'kindly', 'thank you', 'regards', 'assist', 'apologize',
    }
    _SPECIALIZATION_KEYWORDS = {
        'phone': ['phone', 'phones', 'iphone', 'android', 'samsung'],
        'fashion': ['dress', 'shirt', 'shoe', 'bag', 'jacket'],
        'electronics': ['laptop', 'tv', 'generator', 'fridge', 'tablet'],
        'home_appliances': ['washing machine', 'microwave', 'blender', 'freezer'],
    }
    _GOAL_KEYWORDS = {
        'increase_sales': ['sales', 'sell more', 'conversion', 'buyers'],
        'grow_brand': ['brand', 'visibility', 'reputation', 'trust'],
        'fast_responses': ['fast response', 'quick reply', 'instant'],
    }

    @classmethod
    def _default_memory(cls) -> Dict:
        return {
            'tone_preference': 'neutral',
            'product_specialization': [],
            'communication_style': 'balanced',
            'preferred_language': 'english',
            'seller_goals': [],
            'response_length_preference': 'medium',
            'manually_reviewed': False,
        }

    @classmethod
    def _normalize_text(cls, text: Optional[str]) -> str:
        return (text or '').strip().lower()

    @classmethod
    def _detect_language(cls, text: str) -> str:
        if any(token in text for token in cls._PIDGIN_TOKENS):
            return 'pidgin'
        return 'english'

    @classmethod
    def _detect_tone(cls, text: str) -> str:
        if any(token in text for token in cls._FORMAL_TOKENS):
            return 'formal'
        if any(token in text for token in cls._CASUAL_TOKENS):
            return 'casual'
        return 'neutral'

    @classmethod
    def _detect_response_length_preference(cls, message_text: str) -> str:
        message_len = len(message_text.split())
        if message_len <= 6:
            return 'short'
        if message_len >= 20:
            return 'long'
        return 'medium'

    @classmethod
    def _detect_specializations(cls, combined_text: str) -> List[str]:
        specializations = []
        for label, keywords in cls._SPECIALIZATION_KEYWORDS.items():
            if any(re.search(rf'\b{re.escape(keyword)}\b', combined_text) for keyword in keywords):
                specializations.append(label)
        return specializations

    @classmethod
    def _detect_goals(cls, combined_text: str) -> List[str]:
        goals = []
        for goal, keywords in cls._GOAL_KEYWORDS.items():
            if any(keyword in combined_text for keyword in keywords):
                goals.append(goal)
        return goals

    @classmethod
    def _is_approved_seller(cls, user: Optional[User]) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        try:
            seller_profile = user.seller_profile
        except SellerProfile.DoesNotExist:
            return False
        return seller_profile.status == SellerProfile.STATUS_APPROVED

    @classmethod
    def update_from_conversation(cls, user: Optional[User], user_message: str, assistant_reply: str = '') -> bool:
        """
        Update seller memory using rules only.
        - Silent failure by design.
        - Runs only for approved sellers.
        """
        try:
            if not cls._is_approved_seller(user):
                return False

            seller_profile = user.seller_profile
            memory = cls._default_memory()
            if isinstance(seller_profile.ai_memory, dict):
                memory.update(seller_profile.ai_memory)

            user_text = cls._normalize_text(user_message)
            reply_text = cls._normalize_text(assistant_reply)
            combined = f"{user_text} {reply_text}".strip()

            detected_tone = cls._detect_tone(combined)
            detected_language = cls._detect_language(combined)
            length_pref = cls._detect_response_length_preference(user_text)
            specializations = cls._detect_specializations(combined)
            goals = cls._detect_goals(combined)

            changed = False
            if detected_tone != memory.get('tone_preference'):
                memory['tone_preference'] = detected_tone
                changed = True

            communication_style = {
                'short': 'concise',
                'medium': 'balanced',
                'long': 'detailed',
            }.get(length_pref, 'balanced')
            if communication_style != memory.get('communication_style'):
                memory['communication_style'] = communication_style
                changed = True

            if detected_language != memory.get('preferred_language'):
                memory['preferred_language'] = detected_language
                changed = True

            if length_pref != memory.get('response_length_preference'):
                memory['response_length_preference'] = length_pref
                changed = True

            merged_specializations = sorted(set((memory.get('product_specialization') or []) + specializations))
            if merged_specializations != (memory.get('product_specialization') or []):
                memory['product_specialization'] = merged_specializations
                changed = True

            merged_goals = sorted(set((memory.get('seller_goals') or []) + goals))
            if merged_goals != (memory.get('seller_goals') or []):
                memory['seller_goals'] = merged_goals
                changed = True

            if memory.get('manually_reviewed') is None:
                memory['manually_reviewed'] = False
                changed = True

            if not changed:
                return True

            seller_profile.ai_memory = memory
            seller_profile.save(update_fields=['ai_memory', 'updated_at'])
            return True
        except Exception:
            logger.exception('Seller memory update failed silently.')
            return False

    @classmethod
    def update_from_conversation_async(cls, user: Optional[User], user_message: str, assistant_reply: str = '') -> None:
        """Best-effort async wrapper to avoid slowing request pipeline."""

        def _runner():
            try:
                cls.update_from_conversation(user, user_message, assistant_reply)
            except Exception:
                logger.exception('Seller memory async update failed silently.')

        try:
            threading.Thread(target=_runner, daemon=True).start()
        except Exception:
            logger.exception('Seller memory async launcher failed silently.')
