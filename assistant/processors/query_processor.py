"""
Query Processor - Main orchestrator for the hybrid assistant.
Flow: RuleEngine → RAGRetriever → LocalModelAdapter
"""
import logging
import time
from typing import Dict, Optional
from .rule_engine import RuleEngine, BLOCK_THRESHOLD
from .rag_retriever import RAGRetriever, FAQ_MATCH_THRESHOLD
from .local_model import LocalModelAdapter, NoModelAvailable

logger = logging.getLogger(__name__)

# LLM Configuration
LLM_MAX_TOKENS = 256
LLM_TEMPERATURE = 0.2
LLM_TIMEOUT = 10.0  # seconds


class QueryProcessor:
    """
    Main query processor coordinating all assistant components.
    """
    
    def __init__(self):
        """Initialize all components."""
        logger.info("Initializing QueryProcessor...")
        
        # Initialize components
        self.rule_engine = RuleEngine.get_instance()
        self.rag = RAGRetriever.get_instance()
        
        # Initialize LLM (optional - gracefully degrades if unavailable)
        try:
            self.llm = LocalModelAdapter.get_instance()
            logger.info(f"LLM available: {self.llm.is_available()}")
        except Exception as e:
            logger.warning(f"LLM initialization failed: {e}")
            self.llm = None
        
        # Validate RAG index
        if not self.rag.is_ready():
            logger.error(
                "⚠️  RAG index not found! Please run: python scripts/build_rag_index.py"
            )
            raise RuntimeError(
                "RAG index not built. Run 'python scripts/build_rag_index.py' first."
            )
        
        logger.info("✅ QueryProcessor initialized successfully")
    
    def _sanitize_input(self, message: str) -> str:
        """Sanitize user input."""
        if not message:
            return ""
        # Truncate to safe length
        max_len = 2048
        return message[:max_len].strip()
    
    def _build_llm_prompt(self, message: str, faqs: list, rule: Optional[Dict] = None) -> str:
        """
        Build prompt for LLM with context from FAQs and rules.
        
        Args:
            message: User's query
            faqs: List of relevant FAQs
            rule: Matched rule (if any)
        
        Returns:
            str: Formatted prompt
        """
        # System context
        system_prompt = """You are a helpful Zunto marketplace assistant. 
Answer briefly (2-3 sentences max), professionally, and based on the provided FAQ context.
If the question isn't covered by FAQs, provide helpful general guidance for marketplace issues.

GUIDELINES:
- Be friendly and professional
- Keep answers concise
- Direct legal/medical questions to professionals
- Never help with illegal activities
- Focus on: buying, selling, payments, refunds, disputes, shipping"""
        
        # Add safety note if rule matched
        safety_note = ""
        if rule and rule.get('severity') in ['high', 'critical']:
            safety_note = f"\n⚠️ SAFETY ALERT: This query matches '{rule['id']}' rule. Prioritize user safety in your response."
        
        # Add FAQ context
        faq_context = ""
        if faqs:
            faq_context = "\n\n📚 RELEVANT FAQ CONTEXT:\n"
            for i, faq in enumerate(faqs[:3], 1):  # Top 3 FAQs
                faq_context += f"\nQ{i}: {faq['question']}\nA{i}: {faq['answer']}\n"
        
        # Build final prompt
        prompt = f"""{system_prompt}{safety_note}{faq_context}

USER QUERY: {message}

ASSISTANT:"""
        
        return prompt
    
    def _calculate_combined_confidence(self, rule: Optional[Dict], faqs: list, llm_used: bool) -> float:
        """
        Calculate combined confidence score.
        
        Logic:
        - Rule match: Use rule confidence as base
        - FAQ match: Use FAQ score as base
        - LLM: Add default confidence
        - Combine using weighted average
        """
        scores = []
        
        if rule:
            scores.append(rule['confidence'])
        
        if faqs:
            scores.append(faqs[0]['score'])
        
        if llm_used:
            scores.append(0.6)  # Default LLM confidence
        
        if not scores:
            return 0.5  # Fallback
        
        return sum(scores) / len(scores)
    
    def process(self, message: str) -> Dict:
        """
        Process user query through the hybrid pipeline.
        
        Args:
            message: User's input message
        
        Returns:
            {
                'reply': str,
                'confidence': float,
                'explanation': str,
                'rule': dict | None,
                'faq': dict | None,
                'llm': dict | None
            }
        """
        start_time = time.time()
        
        # Sanitize input
        clean_message = self._sanitize_input(message)
        if not clean_message:
            return {
                'reply': "I didn't receive a valid message. Could you please try again?",
                'confidence': 0.0,
                'explanation': 'empty_input',
                'rule': None,
                'faq': None,
                'llm': None
            }
        
        # STEP 1: Check rules (safety first!)
        rule = self.rule_engine.match(clean_message)
        
        # Block immediately if critical rule matched
        if rule and self.rule_engine.should_block(rule):
            logger.warning(f"🚫 BLOCKED: Rule '{rule['id']}' with confidence {rule['confidence']:.2f}")
            return {
                'reply': self.rule_engine.get_blocked_response(rule),
                'confidence': rule['confidence'],
                'explanation': 'rule_block',
                'rule': rule,
                'faq': None,
                'llm': None
            }
        
        # STEP 2: Retrieve relevant FAQs
        faqs = self.rag.search(clean_message, k=5)
        top_faq = faqs[0] if faqs else None
        
        # STEP 3: Generate LLM response (with context)
        llm_result = None
        reply_text = ""
        
        if self.llm and self.llm.is_available():
            try:
                prompt = self._build_llm_prompt(clean_message, faqs, rule)
                
                llm_output = self.llm.generate(
                    user_message=prompt,
                    max_tokens=LLM_MAX_TOKENS,
                    temperature=LLM_TEMPERATURE
                )
                
                reply_text = llm_output['response']
                llm_result = {
                    'model_filename': 'mistral-7b-openorca.Q4_0.gguf',
                    'model_path': self.llm.get_model_info().get('model_path', 'unknown'),
                    'model_type': llm_output['model_type'],
                    'generation_time': llm_output['generation_time'],
                    'tokens_generated': llm_output['tokens_generated']
                }
                
            except NoModelAvailable:
                logger.warning("LLM not available, using FAQ fallback")
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
        
        # FALLBACK: Use FAQ answer if LLM failed or unavailable
        if not reply_text and top_faq and top_faq['score'] >= FAQ_MATCH_THRESHOLD:
            reply_text = top_faq['answer']
            logger.info("Using FAQ answer as fallback")
        
        # FINAL FALLBACK: Generic response
        if not reply_text:
            reply_text = (
                "I apologize, but I don't have enough information to answer that question. "
                "Please contact our support team for assistance, or try rephrasing your question."
            )
        
        # Calculate confidence
        confidence = self._calculate_combined_confidence(rule, faqs, llm_result is not None)
        
        # Determine explanation
        if rule and llm_result:
            explanation = "rule_then_rag_llm"
        elif llm_result:
            explanation = "rag_then_llm"
        elif top_faq:
            explanation = "rag_only"
        else:
            explanation = "fallback"
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"✅ Query processed in {processing_time:.3f}s (explanation: {explanation})")
        
        return {
            'reply': reply_text,
            'confidence': confidence,
            'explanation': explanation,
            'rule': rule,
            'faq': top_faq,
            'llm': llm_result
        }