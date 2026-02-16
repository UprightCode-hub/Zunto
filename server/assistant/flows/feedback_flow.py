#server/assistant/flows/feedback_flow.py
"""Feedback flow for collecting and categorizing user feedback."""
import logging
from typing import Dict, Optional, Tuple
from assistant.models import Report

logger = logging.getLogger(__name__)


class FeedbackFlow:
    """Feedback collection flow with sentiment analysis."""
    
                    
    TYPE_PRAISE = 'praise'
    TYPE_COMPLAINT = 'complaint'
    TYPE_SUGGESTION = 'suggestion'
    TYPE_BUG_REPORT = 'bug'
    TYPE_GENERAL = 'general'
    
                    
    STEP_COLLECT_FEEDBACK = 'collecting_feedback'
    STEP_FOLLOW_UP = 'follow_up'
    STEP_COMPLETE = 'complete'
    
                       
    CATEGORY_KEYWORDS = {
        TYPE_PRAISE: ['great', 'good', 'excellent', 'love', 'amazing', 'perfect', 
                      'wonderful', 'helpful', 'thank', 'appreciate', 'awesome'],
        TYPE_COMPLAINT: ['bad', 'terrible', 'worst', 'awful', 'hate', 'disappointed',
                        'frustrated', 'angry', 'annoying', 'useless', 'poor'],
        TYPE_SUGGESTION: ['suggest', 'should', 'could', 'would be nice', 'recommend',
                         'feature', 'improve', 'add', 'wish', 'hope'],
        TYPE_BUG_REPORT: ['bug', 'error', 'broken', 'crash', 'not working', 'issue',
                         'problem', 'glitch', 'fail', 'doesnt work', "doesn't work"]
    }
    
                       
    FEEDBACK_INTRO = """Thank you {name}! 💭 Your feedback helps us improve Zunto.

Please share your thoughts:
- What do you like about Zunto?
- What could be better?
- Any suggestions or features you'd like to see?
- Any issues you've encountered?

Tell me anything - I'm here to listen! 😊"""
    
    POSITIVE_RESPONSE = """Thank you so much for the kind words, {name}! 🙏✨

{custom_message}

We're thrilled to hear you're enjoying Zunto! Your support motivates our team to keep improving.

Is there anything else you'd like to share or any questions I can help with?"""
    
    NEGATIVE_RESPONSE = """Thank you for sharing this, {name}. I'm sorry to hear about your experience. 😔

{custom_message}

Your feedback is valuable and will help us improve. Our team takes all concerns seriously.

Would you like to:
1️⃣ Report this as a formal issue (we'll prioritize it)
2️⃣ Share more details
3️⃣ Return to main menu

Type 1, 2, 3, or continue sharing your thoughts."""
    
    SUGGESTION_RESPONSE = """Great suggestion, {name}! 💡

{custom_message}

We love hearing ideas from our users. Your suggestion will be reviewed by our product team.

Do you have any other suggestions or feedback to share?"""
    
    BUG_RESPONSE = """Thank you for reporting this, {name}! 🐛

{custom_message}

This sounds like a technical issue. I'll make sure our development team sees this.

Can you provide any additional details?
- When did this happen?
- What were you trying to do?
- Does it happen every time?

Or type "done" if you've shared everything."""
    
    COMPLETION_MESSAGE = """Your feedback has been recorded! ✅

**Feedback ID:** #{feedback_id}

{custom_closing}

What would you like to do next?

1️⃣ **Ask FAQ Questions** - Get quick answers
2️⃣ **Report an Issue** - Need more help?
3️⃣ **Share More Feedback** - Have more to say?

Type 1, 2, 3, or describe what you need!"""
    
    def __init__(self, session, context_manager=None, intent_classifier=None):
        """
        Initialize feedback flow.
        
        Args:
            session: ConversationSession instance
            context_manager: Optional ContextManager for sentiment tracking
            intent_classifier: Optional intent classifier for emotion detection
        """
        self.session = session
        self.context_manager = context_manager
        self.intent_classifier = intent_classifier
        self.name = session.user_name or "there"
        
                                   
        self.context = session.context or {}
        if 'feedback' not in self.context:
            self.context['feedback'] = {
                'step': self.STEP_COLLECT_FEEDBACK,
                'messages': [],
                'type': None,
                'sentiment': 'neutral',
                'follow_up_count': 0
            }
    
    def enter_feedback_mode(self) -> str:
        """
        Enter feedback mode and show intro.
        
        Returns:
            Intro message
        """
                              
        self.session.current_state = 'feedback_mode'
        self.context['feedback']['step'] = self.STEP_COLLECT_FEEDBACK
        self._save_context()
        
                          
        if self.context_manager:
            self.context_manager.mark_mode_used('feedback_mode')
            self.context_manager.mark_topic_discussed('feedback')
        
        logger.info(f"User {self.name} entered feedback mode")
        
        return self.FEEDBACK_INTRO.format(name=self.name)
    
    def handle_feedback_message(self, message: str, emotion: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Handle feedback message with sentiment analysis.
        
        Args:
            message: User's feedback
        
        Returns:
            (reply_text, metadata)
            metadata: {
                'step': str,
                'complete': bool,
                'feedback_type': str,
                'sentiment': str,
                'feedback_id': int (if complete)
            }
        """
        current_step = self.context['feedback']['step']
        msg_lower = message.lower().strip()
        
                                            
        if msg_lower in ['menu', 'exit', 'back', 'done', 'finish']:
            return self._save_and_complete()
        
                             
        if current_step == self.STEP_COLLECT_FEEDBACK:
            return self._handle_initial_feedback(message, emotion)
        
        elif current_step == self.STEP_FOLLOW_UP:
            return self._handle_follow_up(message)
        
        else:
                      
            return self._save_and_complete()
    
    def _handle_initial_feedback(self, message: str, emotion: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Handle initial feedback collection with sentiment analysis.
        """
                                
        self.context['feedback']['messages'].append(message)
        
                                            
        feedback_type = self._detect_feedback_type(message)
        sentiment = self._detect_sentiment(message, emotion=emotion)
        
        self.context['feedback']['type'] = feedback_type
        self.context['feedback']['sentiment'] = sentiment
        self.context['feedback']['step'] = self.STEP_FOLLOW_UP
        self._save_context()
        
        logger.info(
            f"Feedback collected: type={feedback_type}, sentiment={sentiment}, "
            f"length={len(message)} chars"
        )
        
                                                                   
        reply, metadata = self._generate_typed_response(message, feedback_type, sentiment)
        
        return reply, metadata
    
    def _handle_follow_up(self, message: str) -> Tuple[str, Dict]:
        """
        Handle follow-up feedback or additional details.
        """
        msg_lower = message.lower().strip()
        
                                                                  
        if msg_lower in ['1', 'report', 'formal', 'issue']:
                                     
            return self._escalate_to_dispute()
        
        elif msg_lower in ['2', 'more', 'details', 'share more']:
                                   
            self.context['feedback']['messages'].append(message)
            self.context['feedback']['follow_up_count'] += 1
            self._save_context()
            
            return (
                f"Thank you for the additional details, {self.name}. "
                "Is there anything else you'd like to add? "
                "(Or type 'done' to finish)",
                {
                    'step': self.STEP_FOLLOW_UP,
                    'complete': False,
                    'action': 'collecting_more'
                }
            )
        
        elif msg_lower in ['3', 'menu', 'done', 'finish', 'no', 'nope', "that's all"]:
                               
            return self._save_and_complete()
        
                                                      
        elif any(kw in msg_lower for kw in ['yes', 'yeah', 'yep', 'sure', 'more']):
            return (
                "Go ahead, I'm listening! What else would you like to share?",
                {
                    'step': self.STEP_FOLLOW_UP,
                    'complete': False,
                    'action': 'prompt_more'
                }
            )
        
        else:
                                       
            self.context['feedback']['messages'].append(message)
            self.context['feedback']['follow_up_count'] += 1
            self._save_context()
            
            return (
                f"Thank you for sharing that, {self.name}! "
                "Anything else you'd like to add? (Type 'done' when finished)",
                {
                    'step': self.STEP_FOLLOW_UP,
                    'complete': False,
                    'action': 'collected_more'
                }
            )
    
    def _detect_feedback_type(self, message: str) -> str:
        """Detect feedback type from keywords."""
        msg_lower = message.lower()
        
                                     
        type_scores = {}
        for fb_type, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in msg_lower)
            if score > 0:
                type_scores[fb_type] = score
        
                                        
        if type_scores:
            return max(type_scores, key=type_scores.get)
        
        return self.TYPE_GENERAL
    
    def _detect_sentiment(self, message: str, emotion: Optional[str] = None) -> str:
        """
        Detect sentiment using intent_classifier if available,
        otherwise use keyword-based detection.
        """
                                                                     
        if emotion:
            if emotion in ['happy', 'excited']:
                return 'positive'
            elif emotion in ['angry', 'frustrated', 'sad']:
                return 'negative'
            return 'neutral'

                                                                                      
        if self.intent_classifier:
            try:
                from assistant.ai.intent_classifier import classify_intent
                _, _, metadata = classify_intent(message, self.session.context)
                detected_emotion = metadata.get('emotion', 'neutral')

                if detected_emotion in ['happy', 'excited']:
                    return 'positive'
                elif detected_emotion in ['angry', 'frustrated', 'sad']:
                    return 'negative'
                else:
                    return 'neutral'
            except Exception as e:
                logger.warning(f"Intent classifier failed: {e}")
        
                                           
        msg_lower = message.lower()
        positive_count = sum(1 for kw in self.CATEGORY_KEYWORDS[self.TYPE_PRAISE] if kw in msg_lower)
        negative_count = sum(1 for kw in self.CATEGORY_KEYWORDS[self.TYPE_COMPLAINT] if kw in msg_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _generate_typed_response(
        self, 
        message: str, 
        feedback_type: str, 
        sentiment: str
    ) -> Tuple[str, Dict]:
        """
        Generate response based on feedback type and sentiment.
        """
                                            
        if feedback_type == self.TYPE_PRAISE:
            custom_msg = "It means a lot to us that you took the time to share positive feedback!"
            template = self.POSITIVE_RESPONSE
        
        elif feedback_type == self.TYPE_COMPLAINT:
            custom_msg = "We appreciate you bringing this to our attention. We're committed to making things right."
            template = self.NEGATIVE_RESPONSE
        
        elif feedback_type == self.TYPE_SUGGESTION:
            custom_msg = "We're always looking for ways to make Zunto better, and user ideas like yours are invaluable!"
            template = self.SUGGESTION_RESPONSE
        
        elif feedback_type == self.TYPE_BUG_REPORT:
            custom_msg = "Bug reports help us maintain a smooth experience for everyone. We'll investigate this promptly."
            template = self.BUG_RESPONSE
        
        else:           
            custom_msg = "We appreciate you taking the time to share your thoughts with us!"
            template = self.POSITIVE_RESPONSE                                
        
                         
        reply = template.format(
            name=self.name,
            custom_message=custom_msg
        )
        
        metadata = {
            'step': self.STEP_FOLLOW_UP,
            'complete': False,
            'feedback_type': feedback_type,
            'sentiment': sentiment
        }
        
        return reply, metadata
    
    def _escalate_to_dispute(self) -> Tuple[str, Dict]:
        """
        Escalate negative feedback to dispute flow.
        """
                                         
        feedback_text = " ".join(self.context['feedback']['messages'])
        
        report = Report.objects.create(
            user=self.session.user,
            message=feedback_text,
            report_type='complaint',
            severity='medium',
            category='feedback_escalation',
            meta={
                'session_id': self.session.session_id,
                'user_name': self.name,
                'feedback_type': self.context['feedback']['type'],
                'escalated_from': 'feedback_mode'
            }
        )
        
        logger.info(f"Feedback escalated to report #{report.id}")
        
                                
        self.session.current_state = 'dispute_mode'
        self.context['dispute'] = {
            'step': 'show_contact',
            'description': feedback_text,
            'category': 'complaint',
            'escalated_from_feedback': True,
            'original_report_id': report.id
        }
        self._save_context()
        
        reply = f"""I've logged this as a priority issue (Report #{report.id}). 📋

Let me help you contact our support team for faster resolution.

📞 **Our Support Channels:**

🐦 **Twitter/X:** @ZuntoSupport
📧 **Email:** support@zunto.com
💬 **WhatsApp:** +234-XXX-XXX-XXXX

Would you like me to help you draft a professional message?
Type: **email**, **twitter**, **whatsapp**, or **no**"""
        
        return reply, {
            'step': 'escalated',
            'complete': True,
            'report_id': report.id,
            'action': 'escalated_to_dispute'
        }
    
    def _save_and_complete(self) -> Tuple[str, Dict]:
        """
        Save feedback to database and complete flow.
        """
        feedback_data = self.context['feedback']
        feedback_text = " ".join(feedback_data['messages'])
        
                                               
        severity_map = {
            'positive': 'low',
            'neutral': 'low',
            'negative': 'medium'
        }
        severity = severity_map.get(feedback_data['sentiment'], 'low')
        
                               
        if feedback_data['type'] == self.TYPE_COMPLAINT:
            report_type = 'complaint'
        elif feedback_data['type'] == self.TYPE_SUGGESTION:
            report_type = 'suggestion'
        else:
            report_type = 'feedback'
        
                          
        report = Report.objects.create(
            user=self.session.user,
            message=feedback_text,
            report_type=report_type,
            severity=severity,
            category=feedback_data['type'],
            meta={
                'session_id': self.session.session_id,
                'user_name': self.name,
                'sentiment': feedback_data['sentiment'],
                'follow_up_count': feedback_data['follow_up_count']
            }
        )
        
        logger.info(
            f"Feedback saved: Report #{report.id} "
            f"(type={report_type}, sentiment={feedback_data['sentiment']})"
        )
        
                                            
        if self.context_manager:
            self.context_manager.mark_resolution(success=True)
        
                                                 
        if feedback_data['sentiment'] == 'positive':
            custom_closing = "We're grateful for your support! 🙏"
        elif feedback_data['sentiment'] == 'negative':
            custom_closing = "We're committed to making your experience better. Thank you for your patience."
        else:
            custom_closing = "Your input helps us grow. Thank you!"
        
                       
        self.session.current_state = 'menu'
        self.context['feedback'] = {'step': self.STEP_COMPLETE}
        self._save_context()
        
        reply = self.COMPLETION_MESSAGE.format(
            feedback_id=report.id,
            custom_closing=custom_closing
        )
        
        return reply, {
            'step': 'complete',
            'complete': True,
            'feedback_id': report.id,
            'sentiment': feedback_data['sentiment']
        }
    
    def _save_context(self):
        """Persist context to session."""
        self.session.context = self.context
        self.session.save(update_fields=['context', 'current_state', 'updated_at'])

