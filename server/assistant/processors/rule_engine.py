#server/assistant/processors/rule_engine.py
"""
Rule Engine - conservative matching against safety/support rules.

The customer-service agent owns contextual support work. This engine should only
catch clear safety/escalation cases and explicit report commands.
"""
import logging
import re
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

RULE_MATCH_THRESHOLD = 0.78
BLOCK_THRESHOLD = 0.90
MIN_RULE_MESSAGE_WORDS = 4
SHORT_ACKNOWLEDGEMENTS = {
    'y', 'yes', 'yeah', 'yep', 'no', 'nope', 'nah', 'ok', 'okay',
    'sure', 'fine', 'cool', 'alright', 'thanks', 'thank you',
}
EXPLICIT_RULE_COMMANDS = {
    'report seller',
    'report buyer',
    'report user',
    'report account',
    'report scam',
    'report fraud',
    'freeze account',
    'freeze my account',
    'lock account',
    'lock my account',
}


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

    @staticmethod
    def _meaningful_words(text: str) -> List[str]:
        """Return simple alphanumeric words used for short-message gating."""
        return [token for token in re.findall(r"[a-z0-9']+", (text or '').lower()) if len(token) > 1]

    def _fuzzy_match_phrase(self, phrase: str, message: str) -> float:
        """
        Calculate fuzzy match score using rapidfuzz.
        
        Returns:
            float: Confidence score (0.0 to 1.0)
        """
        phrase_lower = phrase.lower().strip()
        message_lower = message.lower().strip()
        phrase_words = self._meaningful_words(phrase_lower)
        message_words = self._meaningful_words(message_lower)

        if not phrase_words or not message_words:
            return 0.0

        if re.search(rf"\b{re.escape(phrase_lower)}\b", message_lower):
            return 1.0

        phrase_word_set = set(phrase_words)
        message_word_set = set(message_words)
        overlap = phrase_word_set.intersection(message_word_set)

        if phrase_word_set.issubset(message_word_set):
            return 1.0

        if not HAS_RAPIDFUZZ:
            return 0.0

        if not overlap:
            return 0.0

        # Short rule phrases are precise policy hooks, not fuzzy suggestions.
        # Require every meaningful word so "hello support" cannot drift into a
        # support/escalation rule because of a high partial-ratio score.
        if len(phrase_word_set) <= 2 and overlap != phrase_word_set:
            return 0.0

        if len(overlap) / len(phrase_word_set) < 0.5:
            return 0.0

        partial_score = fuzz.partial_ratio(phrase_lower, message_lower) / 100.0

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

        normalized_message = message.lower().strip()
        meaningful_words = self._meaningful_words(normalized_message)
        is_explicit_command = normalized_message in EXPLICIT_RULE_COMMANDS
        if (
            normalized_message in SHORT_ACKNOWLEDGEMENTS
            or (len(meaningful_words) < MIN_RULE_MESSAGE_WORDS and not is_explicit_command)
        ):
            logger.debug("Skipping rule match for short/non-meaningful message: %r", message)
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
                        'description': description,
                        'response': rule.get('response', ''),
                    }

                                                    
                    if action in ['block', 'freeze_account', 'escalate_urgent'] and confidence >= BLOCK_THRESHOLD:
                        logger.warning(f"BLOCKING: Rule '{rule_id}' matched with {confidence:.2f} confidence")
                        return best_match

        if best_match:
            logger.info(f"Rule '{best_match['id']}' matched (confidence: {best_confidence:.2f})")

        return best_match

    def evaluate(self, message: str) -> Optional[Dict]:
        """Backward-compatible alias."""
        return self.match(message)

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
