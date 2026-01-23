"""
Rule Engine - Fuzzy matching against safety/support rules.
Matches user messages against rules.yaml using rapidfuzz for robustness.
"""
import logging
import yaml
from pathlib import Path
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    logger.warning("rapidfuzz not installed. Falling back to simple string matching.")
    HAS_RAPIDFUZZ = False

RULE_MATCH_THRESHOLD = 0.75
BLOCK_THRESHOLD = 0.90


class RuleEngine:
    """
    Singleton rule engine for matching user messages against predefined rules.
    Uses fuzzy matching for robustness against typos and variations.
    """

    _instance = None

    def __init__(self, rules_path: Optional[str] = None):
        if rules_path is None:
            base_dir = Path(__file__).parent.parent
            rules_path = base_dir / 'data' / 'rules.yaml'

        self.rules_path = Path(rules_path)
        self.rules: List[Dict] = []
        self._load_rules()

    @classmethod
    def get_instance(cls, rules_path: Optional[str] = None):
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(rules_path)
        return cls._instance

    def _load_rules(self):
        """Load rules from YAML file."""
        try:
            if not self.rules_path.exists():
                logger.warning(f"Rules file not found: {self.rules_path}")
                self.rules = []
                return

            with open(self.rules_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.rules = data.get('rules', [])

            logger.info(f"Loaded {len(self.rules)} rules from {self.rules_path}")

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            self.rules = []
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            self.rules = []

    def _fuzzy_match_phrase(self, phrase: str, message: str) -> float:
        """
        Calculate fuzzy match score using rapidfuzz.
        
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        phrase_lower = phrase.lower().strip()
        message_lower = message.lower().strip()

        # Direct substring match = perfect score
        if phrase_lower in message_lower:
            return 1.0

        if not HAS_RAPIDFUZZ:
            return 0.0

        # Partial ratio for subsequence matching
        partial_score = fuzz.partial_ratio(phrase_lower, message_lower) / 100.0

        # Token set ratio for word-order-insensitive matching
        token_score = fuzz.token_set_ratio(phrase_lower, message_lower) / 100.0

        return max(partial_score, token_score)

    def match(self, message: str) -> Optional[Dict]:
        """
        Match message against all rules.
        
        Args:
            message: User's input message
        
        Returns:
            {
                'id': str,
                'action': str,
                'severity': str,
                'matched_phrase': str,
                'confidence': float,
                'description': str
            } or None if no match
        """
        if not message or not self.rules:
            return None

        best_match = None
        best_confidence = 0.0

        for rule in self.rules:
            rule_id = rule.get('id', 'unknown')
            phrases = rule.get('phrases', [])
            action = rule.get('action', 'escalate')
            severity = rule.get('severity', 'medium')
            description = rule.get('description', '')

            for phrase in phrases:
                confidence = self._fuzzy_match_phrase(phrase, message)

                if confidence >= RULE_MATCH_THRESHOLD and confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        'id': rule_id,
                        'action': action,
                        'severity': severity,
                        'matched_phrase': phrase,
                        'confidence': confidence,
                        'description': description
                    }

                    # Early exit for critical blocks
                    if action in ['block', 'freeze_account', 'escalate_urgent'] and confidence >= BLOCK_THRESHOLD:
                        logger.warning(f"BLOCKING: Rule '{rule_id}' matched with {confidence:.2f} confidence")
                        return best_match

        if best_match:
            logger.info(f"Rule '{best_match['id']}' matched (confidence: {best_confidence:.2f})")

        return best_match

    def should_block(self, rule: Dict) -> bool:
        """
        Determine if a rule match should block the message.
        
        Args:
            rule: Matched rule dict
        
        Returns:
            bool: True if message should be blocked
        """
        if not rule:
            return False

        blocking_actions = ['block', 'freeze_account', 'escalate_urgent']
        return (
            rule['action'] in blocking_actions and
            rule['confidence'] >= BLOCK_THRESHOLD
        )

    def get_blocked_response(self, rule: Dict) -> str:
        """Generate appropriate blocked response based on rule."""
        severity = rule.get('severity', 'medium')

        responses = {
            'critical': "This message has been flagged for immediate review. Our team will contact you shortly.",
            'high': "Your message requires review by our support team. We'll get back to you within 24 hours.",
            'medium': "We've received your message and it's being reviewed. Thank you for your patience."
        }

        return responses.get(severity, "Your message is being reviewed by our team.")

    def reload_rules(self):
        """Reload rules from file (useful for hot-reloading)."""
        logger.info("Reloading rules...")
        self._load_rules()

    def get_rule_count(self) -> int:
        """Get total number of loaded rules."""
        return len(self.rules)