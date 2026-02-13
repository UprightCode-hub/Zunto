# assistant/processors/conversation_manager.py

import logging
from typing import Dict, Tuple, Optional
from functools import lru_cache
import gc

from django.conf import settings

from assistant.models import ConversationSession
from assistant.processors.query_processor import QueryProcessor
from assistant.processors.local_model import LocalModelAdapter

from assistant.ai import (
    detect_name,
    classify_intent,
    ContextManager,
    ResponsePersonalizer
)

from assistant.flows import (
    GreetingFlow,
    FAQFlow,
    DisputeFlow,
    FeedbackFlow
)

from assistant.utils.constants import (
    STATE_GREETING,
    STATE_AWAITING_NAME,
    STATE_MENU,
    STATE_FAQ_MODE,
    STATE_DISPUTE_MODE,
    STATE_FEEDBACK_MODE,
    STATE_CHAT_MODE,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM
)
from assistant.utils.validators import (
    validate_message,
    sanitize_message,
    is_spam_message
)
from assistant.utils.formatters import (
    clean_message
)

logger = logging.getLogger(__name__)


class ConversationManager:
    
    def __init__(self, session_id: str, user_id: int = None):
        self.session_id = session_id
        self.user_id = user_id
        self.session = self._get_or_create_session()

        self.query_processor = QueryProcessor()
        self.llm = LocalModelAdapter.get_instance()

        self.context_mgr = ContextManager(self.session)
        self.personalizer = ResponsePersonalizer(self.session)

        self.greeting_flow = GreetingFlow(self.session, self.context_mgr)
        self.faq_flow = FAQFlow(self.session, self.query_processor, self.context_mgr)
        self.dispute_flow = DisputeFlow(self.session, self.llm, self.context_mgr)
        self.feedback_flow = FeedbackFlow(self.session, self.context_mgr, intent_classifier=True)

        self._message_intent_cache = {}

        gc.collect()
        logger.info(f"ConversationManager initialized for session {session_id[:8]}")

    def _get_or_create_session(self) -> ConversationSession:
        try:
            session, created = ConversationSession.objects.get_or_create(
                session_id=self.session_id,
                defaults={
                    'user_id': self.user_id,
                    'current_state': STATE_GREETING,
                    'context': {}
                }
            )

            if created:
                logger.info(f"New session created: {self.session_id}")

            return session
        except Exception as e:
            logger.error(f"Session creation error: {e}", exc_info=True)
            raise

    def process_message(self, message: str) -> str:
        try:
            is_valid, error = validate_message(message)
            if not is_valid:
                logger.warning(f"Invalid message: {error}")
                return f"⚠️ {error}"

            if is_spam_message(message):
                logger.warning(f"Spam detected: {message[:50]}...")
                return "I'm sorry, but your message appears to be spam. Please try again with a genuine question."

            message = sanitize_message(message)
            message = clean_message(message)

            current_state = self.session.current_state

            logger.info(f"Processing message in state '{current_state}': {message[:50]}...")

            if current_state == STATE_GREETING:
                return self._handle_greeting()

            elif current_state == STATE_AWAITING_NAME:
                return self._handle_name_input(message)

            elif current_state == STATE_MENU:
                return self._handle_menu_selection(message)

            elif current_state == STATE_FAQ_MODE:
                return self._handle_faq_mode(message)

            elif current_state == STATE_DISPUTE_MODE:
                return self._handle_dispute_mode(message)

            elif current_state == STATE_FEEDBACK_MODE:
                return self._handle_feedback_mode(message)

            elif current_state == STATE_CHAT_MODE:
                return self._handle_chat_mode(message)

            else:
                logger.warning(f"Unknown state '{current_state}', falling back to query processor")
                return self._handle_chat_mode(message)
        
        except Exception as e:
            logger.error(f"ConversationManager error: {e}", exc_info=True)
            return (
                "I apologize, but I encountered an error processing your message. "
                "Please try again or contact our support team for assistance."
            )

    def _get_or_classify_intent(self, message: str):
        use_caching = getattr(settings, 'PHASE1_INTENT_CACHING', True)
        
        if not use_caching:
            intent, confidence, metadata = classify_intent(message, self.session.context)
            logger.debug(f"Intent classified without cache: {intent.value} ({confidence:.2f})")
            return intent, confidence, metadata
        
        if message not in self._message_intent_cache:
            try:
                intent, confidence, metadata = classify_intent(message, self.session.context)
                self._message_intent_cache[message] = (intent, confidence, metadata)
                logger.debug(f"Intent classified and cached: {intent.value} ({confidence:.2f})")
            except Exception as e:
                logger.error(f"Intent classification error: {e}", exc_info=True)
                from assistant.ai.intent_classifier import Intent
                return Intent.UNKNOWN, 0.0, {'emotion': 'neutral'}
        else:
            logger.debug(f"Intent retrieved from cache")
        
        return self._message_intent_cache[message]

    def _handle_greeting(self) -> str:
        try:
            return self.greeting_flow.start_conversation()
        except Exception as e:
            logger.error(f"Greeting flow error: {e}", exc_info=True)
            return "Hello! I'm Gigi, your AI assistant. How can I help you today?"

    def _handle_name_input(self, message: str) -> str:
        try:
            name, confidence = detect_name(message)

            if name:
                self.session.user_name = name
                self.session.current_state = STATE_MENU
                self.session.save()

                response, metadata = self.greeting_flow.handle_name_input(message)

                self.context_mgr.add_message(
                    role='user',
                    content=message,
                    intent='greeting',
                    emotion='neutral'
                )

                self.context_mgr.add_message(
                    role='assistant',
                    content=response,
                    confidence=confidence
                )

                return response

            else:
                return (
                    "I didn't quite catch that. Could you please share your name? "
                    "(Just your first name is fine!)"
                )
        except Exception as e:
            logger.error(f"Name input error: {e}", exc_info=True)
            return "What's your name so I can assist you better?"

    def _handle_menu_selection(self, message: str) -> str:
        try:
            message_lower = message.lower().strip()

            creator_keywords = [
                'creator', 'developer', 'wisdom', 'who made', 'who built',
                'who created', 'about you', 'technology', 'ai behind',
                'how do you work', 'who is your creator', 'who developed',
                'made you', 'built you', 'created you', 'your creator'
            ]

            is_creator_query = (
                message_lower == '4' or 
                any(keyword in message_lower for keyword in creator_keywords)
            )

            if is_creator_query:
                logger.info(f"🎨 User selected creator option: {message[:30]}")
                self.session.current_state = STATE_CHAT_MODE
                self.session.context['mode'] = 'creator_info'
                self.session.save()

                return self._get_creator_info()

            if message_lower in ['1', 'faq', 'question', 'questions', 'ask']:
                intro = self.faq_flow.enter_faq_mode()
                self.context_mgr.add_message('assistant', intro, confidence=1.0)
                return intro

            elif message_lower in ['2', 'dispute', 'report', 'problem', 'issue']:
                intro = self.dispute_flow.enter_dispute_mode()
                self.context_mgr.add_message('assistant', intro, confidence=1.0)
                return intro

            elif message_lower in ['3', 'feedback', 'suggest', 'suggestion']:
                intro = self.feedback_flow.enter_feedback_mode()
                self.context_mgr.add_message('assistant', intro, confidence=1.0)
                return intro

            else:
                intent, confidence, metadata = self._get_or_classify_intent(message)
                emotion = metadata.get('emotion', 'neutral')

                logger.info(f"Menu selection: intent={intent.value}, emotion={emotion}")

                if intent.value in ['dispute', 'complaint', 'issue']:
                    intro = self.dispute_flow.enter_dispute_mode()
                    return intro

                elif intent.value in ['faq', 'question']:
                    intro = self.faq_flow.enter_faq_mode()
                    return intro

                elif intent.value in ['feedback', 'suggestion', 'praise']:
                    intro = self.feedback_flow.enter_feedback_mode()
                    return intro

                else:
                    self.session.current_state = STATE_CHAT_MODE
                    self.session.save()
                    return self._handle_chat_mode(message)
        except Exception as e:
            logger.error(f"Menu selection error: {e}", exc_info=True)
            return "Please select an option (1-4) or describe what you need help with."

    @lru_cache(maxsize=1)
    def _get_cached_creator_info(self) -> str:
        user_name = self.session.user_name or "there"

        response = (
            f"### 🎨 About My Creator - Wisdom Ekwugha\n\n"
            f"Great question, {user_name}! I was built by **Wisdom Ekwugha**, "
            f"an AI Engineer and Full-Stack Developer at **Illuminat XO**, "
            f"passionate about creating intelligent, user-friendly systems.\n\n"
            f"**🏢 Development:**\n"
            f"• Created by: **Gigi Development Engine (GDE)** - Illuminat XO's AI division\n"
            f"• Parent Company: **Illuminat XO**\n"
            f"• Project: **Zunto Marketplace AI Assistant**\n\n"
            f"**🔧 Technologies Behind Me:**\n"
            f"• **Django & Python** - Backend architecture\n"
            f"• **NLP & Machine Learning** - Intent classification, sentiment analysis\n"
            f"• **RAG (Retrieval-Augmented Generation)** - Fast FAQ retrieval (0.03s!)\n"
            f"• **FAISS Vector Search** - Semantic similarity matching\n"
            f"• **WebSockets & Real-time Processing** - Instant responses\n"
            f"• **Context Management** - Tracks conversation history\n\n"
            f"**💡 What Makes Me Special:**\n"
            f"• Multi-turn conversation flow with state management\n"
            f"• Emotion detection and personalized responses\n"
            f"• Smart escalation for complex issues\n"
            f"• 3-tier processing (Rules → RAG → LLM) for efficiency\n"
            f"• Modular AI architecture for easy updates\n\n"
            f"**👨‍💻 About Wisdom:**\n"
            f"• LinkedIn: [linkedin.com/in/wisdom-ekwugha](https://linkedin.com/in/wisdom-ekwugha)\n"
            f"• GitHub: [github.com/wisdomekwugha](https://github.com/wisdomekwugha)\n"
            f"• Specializes in: AI/ML, NLP, Full-Stack Development\n"
            f"• Location: Lagos, Nigeria\n\n"
            f"**🌐 Connect with Zunto Project:**\n"
            f"• Twitter/X: [@ZuntoProject](https://x.com/ZuntoProject)\n"
            f"• Instagram: [@zuntoproject](https://www.instagram.com/zuntoproject)\n"
            f"• Email: zuntoproject@gmail.com\n\n"
            f"**🌐 Illuminat XO:**\n"
            f"• Twitter/X: [@IlluminatXO](https://x.com/IlluminatXO)\n"
            f"• Email: xoilluminate@gmail.com\n\n"
            f"---\n\n"
            f"Want to know more? Ask me:\n"
            f"• \"What projects has Wisdom worked on?\"\n"
            f"• \"How do you process questions so fast?\"\n"
            f"• \"What AI models do you use?\"\n\n"
            f"Or type **'menu'** to go back to the main options!"
        )

        return response

    def _get_creator_info(self) -> str:
        try:
            self.session.context['last_topic'] = 'creator'
            self.session.save()
            return self._get_cached_creator_info()
        except Exception as e:
            logger.error(f"Creator info error: {e}", exc_info=True)
            return "I was created by Wisdom Ekwugha, an AI Engineer at Illuminat XO. Type 'menu' to see other options."

    def _handle_faq_mode(self, message: str) -> str:
        try:
            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            reply, faq_metadata = self.faq_flow.handle_faq_query(message)

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)
            
            if use_personalization and self._needs_personalization(reply):
                final_reply = self.personalizer.personalize(
                    base_response=reply,
                    confidence=faq_metadata.get('confidence', 0.5),
                    emotion=emotion
                )
            else:
                final_reply = reply

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=faq_metadata.get('confidence', 0.5)
            )

            return final_reply
        except Exception as e:
            logger.error(f"FAQ mode error: {e}", exc_info=True)
            return "I encountered an issue processing your question. Could you try rephrasing it?"

    def _handle_dispute_mode(self, message: str) -> str:
        try:
            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            reply, dispute_metadata = self.dispute_flow.handle_dispute_message(message)

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)
            
            if use_personalization and self._needs_personalization(reply):
                final_reply = self.personalizer.personalize(
                    base_response=reply,
                    confidence=0.9,
                    emotion=emotion,
                    formality='formal'
                )
            else:
                final_reply = reply

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=0.9
            )

            if dispute_metadata.get('complete'):
                self.context_mgr.mark_resolution(success=True)

            return final_reply
        except Exception as e:
            logger.error(f"Dispute mode error: {e}", exc_info=True)
            return "I encountered an issue. Please describe your dispute and I'll help you report it."

    def _handle_feedback_mode(self, message: str) -> str:
        try:
            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            reply, feedback_metadata = self.feedback_flow.handle_feedback_message(message)

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)
            
            if use_personalization and self._needs_personalization(reply):
                final_reply = self.personalizer.personalize(
                    base_response=reply,
                    confidence=0.85,
                    emotion=emotion
                )
            else:
                final_reply = reply

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=0.85
            )

            if feedback_metadata.get('complete'):
                self.context_mgr.mark_resolution(
                    success=feedback_metadata.get('sentiment') != 'negative'
                )

            return final_reply
        except Exception as e:
            logger.error(f"Feedback mode error: {e}", exc_info=True)
            return "Thank you for your feedback! Type 'menu' to return to main options."

    def _handle_chat_mode(self, message: str) -> str:
        try:
            message_lower = message.lower()

            if message_lower in ['menu', 'main menu', 'options', 'back', 'go back']:
                self.session.current_state = STATE_MENU
                self.session.save()
                return self.greeting_flow._build_unified_menu(self.session.user_name)

            is_creator_query = self._is_creator_related(message)
            is_followup = self._is_creator_followup(message)

            if is_creator_query or is_followup:
                logger.info(f"🎨 Creator question detected in chat mode")
                return self._handle_creator_followup(message)

            intent, conf, metadata = self._get_or_classify_intent(message)
            emotion = metadata.get('emotion', 'neutral')

            self.context_mgr.add_message(
                role='user',
                content=message,
                intent=intent.value,
                emotion=emotion
            )

            use_context = getattr(settings, 'PHASE1_CONTEXT_INTEGRATION', True)
            
            result = self.query_processor.process(
                message=message,
                user_name=self.session.user_name or None,
                context=self.session.context if use_context else {}
            )

            use_personalization = getattr(settings, 'PHASE1_RESPONSE_PERSONALIZATION_FIX', True)
            
            if use_personalization and self._needs_personalization(result['reply']):
                hints = self.context_mgr.get_personalization_hints()
                formality = ResponsePersonalizer.detect_formality_preference(message)

                final_reply = self.personalizer.personalize(
                    base_response=result['reply'],
                    confidence=result['confidence'],
                    emotion=emotion,
                    formality=hints.get('formality', formality),
                    add_greeting=True,
                    add_emoji=True
                )
            else:
                final_reply = result['reply']

            self.context_mgr.add_message(
                role='assistant',
                content=final_reply,
                confidence=result['confidence']
            )

            if result['confidence'] >= CONFIDENCE_HIGH:
                self.context_mgr.mark_resolution(success=True)

            if 'last_topic' in self.session.context:
                self.session.context['last_topic'] = None
                self.session.save()

            return final_reply
        except Exception as e:
            logger.error(f"Chat mode error: {e}", exc_info=True)
            return "I encountered an issue. Could you rephrase your question?"

    def _needs_personalization(self, response: str) -> bool:
        try:
            has_greeting = any(g in response.lower()[:50] for g in ['hi ', 'hello', 'hey', 'good morning', 'good afternoon'])
            has_emoji = any(ord(c) > 0x1F300 for c in response)
            has_markdown = '**' in response or '#' in response
            
            return not (has_greeting and has_emoji)
        except Exception as e:
            logger.warning(f"Personalization check failed: {e}")
            return False

    def _is_creator_related(self, message: str) -> bool:
        creator_keywords = [
            'creator', 'developer', 'wisdom', 'who made', 'who built',
            'who created', 'technology', 'ai behind', 'how do you work',
            'made you', 'built you', 'created you'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in creator_keywords)

    def _is_creator_followup(self, message: str) -> bool:
        last_topic = self.session.context.get('last_topic')
        if last_topic != 'creator':
            return False

        followup_patterns = [
            'tell me more', 'more about', 'what else', 'his background',
            'his experience', 'his achievements', 'his projects',
            'more info', 'continue', 'go on', 'elaborate', 'details'
        ]

        message_lower = message.lower()
        return any(pattern in message_lower for pattern in followup_patterns)

    def _handle_creator_followup(self, message: str) -> str:
        try:
            from assistant.ai.creator_info import (
                get_creator_bio,
                get_creator_achievements,
                get_creator_projects
            )

            user_name = self.session.user_name or "there"
            message_lower = message.lower()

            if any(word in message_lower for word in ['project', 'work', 'built', 'portfolio']):
                projects = get_creator_projects()
                response = f"**Wisdom's Recent Projects:**\n\n"
                for proj in projects[:3]:
                    response += f"**{proj['name']}** - {proj['description']}\n"
                    response += f"*Tech:* {', '.join(proj['tech'])}\n\n"

            elif any(word in message_lower for word in ['achievement', 'accomplish', 'success']):
                achievements = get_creator_achievements()
                response = f"**Wisdom's Key Achievements:**\n\n"
                response += "\n".join(f"• {a}" for a in achievements)

            elif any(word in message_lower for word in ['experience', 'background', 'skill']):
                response = get_creator_bio('detailed', user_name)

            else:
                response = (
                    f"I'd be happy to tell you more about Wisdom, {user_name}!\n\n"
                    f"You can ask me:\n"
                    f"• \"What projects has he worked on?\"\n"
                    f"• \"What are his key achievements?\"\n"
                    f"• \"Tell me about his technical skills\"\n"
                    f"• \"How can I contact him?\"\n\n"
                    f"Or type **'menu'** to return to main options!"
                )

            self.session.context['last_topic'] = 'creator'
            self.session.save()

            return response
        except Exception as e:
            logger.error(f"Creator followup error: {e}", exc_info=True)
            return "I'd be happy to tell you more about my creator. Type 'menu' to see other options."

    def get_current_state(self) -> str:
        return self.session.current_state

    def get_user_name(self) -> str:
        return self.session.user_name or "there"

    def get_conversation_summary(self) -> Dict:
        try:
            return self.context_mgr.get_conversation_summary()
        except Exception as e:
            logger.error(f"Conversation summary error: {e}", exc_info=True)
            return {}

    def reset_session(self):
        try:
            self.session.current_state = STATE_GREETING
            self.session.user_name = ''
            self.session.context = {}
            self.session.save()

            self.context_mgr.reset()
            self._message_intent_cache.clear()
            logger.info(f"Session reset: {self.session_id}")
        except Exception as e:
            logger.error(f"Session reset error: {e}", exc_info=True)
