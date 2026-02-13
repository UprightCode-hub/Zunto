# assistant/utils/response_builder.py

import logging
from typing import Optional, List
from datetime import datetime

from assistant.utils.constants import EMOJIS, ConfidenceConfig

logger = logging.getLogger(__name__)


class ResponseBuilder:
    
    MAX_EMOJIS = 3
    MAX_GREETING_LENGTH = 50
    
    def __init__(self, context_manager=None):
        self.context_manager = context_manager
        self.core_content = ""
        self.greeting = ""
        self.closing = ""
        self.emojis = []
        self.clarification = ""
        self.disclaimer = ""
        self.escalation_note = ""
        self.user_name = None
        
        if context_manager:
            self.user_name = context_manager.session.user_name

    def set_core_content(self, content: str) -> 'ResponseBuilder':
        self.core_content = content.strip()
        return self

    def add_greeting(self, auto: bool = True, custom_greeting: Optional[str] = None) -> 'ResponseBuilder':
        if custom_greeting:
            self.greeting = custom_greeting
            return self
        
        if not auto:
            return self
        
        if self._has_existing_greeting():
            logger.debug("Content already has greeting, skipping")
            return self
        
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Good morning"
        elif 12 <= hour < 17:
            greeting = "Good afternoon"
        elif 17 <= hour < 21:
            greeting = "Good evening"
        else:
            greeting = "Hello"
        
        if self.user_name:
            self.greeting = f"{greeting} {self.user_name}!"
        else:
            self.greeting = f"{greeting}!"
        
        return self

    def add_emoji(self, category: str = 'helpful', auto: bool = True) -> 'ResponseBuilder':
        if not auto:
            return self
        
        existing_emoji_count = sum(1 for c in self.core_content if ord(c) > 0x1F300)
        existing_emoji_count += len(self.emojis)
        
        if existing_emoji_count >= self.MAX_EMOJIS:
            logger.debug(f"Emoji limit reached ({existing_emoji_count}), skipping")
            return self
        
        emoji_list = EMOJIS.get(category, EMOJIS['helpful'])
        import random
        selected = random.choice(emoji_list)
        
        if selected not in self.emojis:
            self.emojis.append(selected)
        
        return self

    def add_closing(self, auto: bool = True, custom_closing: Optional[str] = None) -> 'ResponseBuilder':
        if custom_closing:
            self.closing = custom_closing
            return self
        
        if not auto:
            return self
        
        if self._has_existing_closing():
            logger.debug("Content already has closing, skipping")
            return self
        
        closings = [
            "Hope this helps!",
            "Let me know if you need anything else!",
            "Happy to help!",
            "Feel free to ask if you have more questions!"
        ]
        
        import random
        self.closing = random.choice(closings)
        return self

    def add_clarification_prompt(self, confidence: Optional[float] = None) -> 'ResponseBuilder':
        if confidence and confidence >= ConfidenceConfig.RAG['high']:
            return self
        
        prompts = [
            "Did this answer your question?",
            "Let me know if you need more details!",
            "Is there anything else you'd like to know?"
        ]
        
        import random
        self.clarification = random.choice(prompts)
        return self

    def add_disclaimer(self, confidence: Optional[float] = None) -> 'ResponseBuilder':
        if confidence and confidence >= ConfidenceConfig.RAG['medium']:
            return self
        
        disclaimers = [
            "For more specific details, please contact our support team.",
            "Our support team can provide personalized assistance.",
            "If you need further help, feel free to reach out to support."
        ]
        
        import random
        self.disclaimer = random.choice(disclaimers)
        return self

    def add_escalation_note(self) -> 'ResponseBuilder':
        if not self.context_manager:
            return self
        
        if self.context_manager.is_escalated():
            self.escalation_note = "I understand this needs immediate attention."
        
        return self

    def add_empathy_prefix(self, emotion: str) -> 'ResponseBuilder':
        empathy_map = {
            'frustrated': "I understand this can be frustrating.",
            'angry': "I sincerely apologize for this experience.",
            'confused': "Let me clarify this for you.",
            'urgent': "I understand this is urgent."
        }
        
        prefix = empathy_map.get(emotion)
        if prefix:
            self.core_content = f"{prefix} {self.core_content}"
        
        return self

    def build(self) -> str:
        parts = []
        
        if self.escalation_note:
            parts.append(self.escalation_note)
        
        if self.greeting:
            parts.append(self.greeting)
        
        if self.core_content:
            parts.append(self.core_content)
        
        if self.emojis and len(self.emojis) > 0:
            emoji_str = " ".join(self.emojis)
            if not any(ord(c) > 0x1F300 for c in self.core_content):
                parts.append(emoji_str)
        
        if self.clarification:
            parts.append(self.clarification)
        
        if self.disclaimer:
            parts.append(self.disclaimer)
        
        if self.closing:
            parts.append(self.closing)
        
        response = " ".join(parts)
        response = " ".join(response.split())
        
        return response

    def _has_existing_greeting(self) -> bool:
        if not self.core_content:
            return False
        
        first_50 = self.core_content[:50].lower()
        greetings = ['hi ', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']
        return any(g in first_50 for g in greetings)

    def _has_existing_closing(self) -> bool:
        if not self.core_content:
            return False
        
        last_50 = self.core_content[-50:].lower()
        closings = ['hope this helps', 'let me know', 'feel free', 'happy to help']
        return any(c in last_50 for c in closings)

    def reset(self) -> 'ResponseBuilder':
        self.core_content = ""
        self.greeting = ""
        self.closing = ""
        self.emojis = []
        self.clarification = ""
        self.disclaimer = ""
        self.escalation_note = ""
        return self


def create_response(
    content: str,
    confidence: float = 0.7,
    context_manager=None,
    emotion: str = 'neutral',
    add_greeting: bool = True,
    add_closing: bool = True
) -> str:
    
    builder = ResponseBuilder(context_manager)
    builder.set_core_content(content)
    
    if emotion in ['frustrated', 'angry', 'urgent']:
        builder.add_empathy_prefix(emotion)
    
    if context_manager and context_manager.is_escalated():
        builder.add_escalation_note()
    
    if add_greeting:
        builder.add_greeting(auto=True)
    
    if confidence < ConfidenceConfig.RAG['high']:
        builder.add_emoji('helpful', auto=True)
    
    if confidence < ConfidenceConfig.RAG['medium']:
        builder.add_clarification_prompt(confidence)
    
    if confidence < ConfidenceConfig.RAG['low']:
        builder.add_disclaimer(confidence)
    
    if add_closing and confidence >= ConfidenceConfig.RAG['medium']:
        builder.add_closing(auto=True)
    
    return builder.build()
```
