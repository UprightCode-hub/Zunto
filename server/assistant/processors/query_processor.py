#server/assistant/processors/query_processor.py
import logging
import time
from typing import Dict, Tuple, Optional, List, Any

from django.conf import settings

from assistant.models import ConversationSession, ConversationLog
from assistant.processors.rule_engine import RuleEngine
from assistant.processors.rag_retriever import RAGRetriever
from assistant.processors.local_model import LocalModelAdapter
from assistant.utils.constants import ConfidenceConfig
from assistant.utils import metrics

logger = logging.getLogger(__name__)


class QueryProcessor:

    def __init__(self):
        self.rule_engine = RuleEngine.get_instance()
        self.rag_retriever = RAGRetriever.get_instance()
        self.llm = LocalModelAdapter.get_instance()

        logger.info("QueryProcessor initialized with 3-tier system")

    def process(
        self,
        message: str,
        session_id: Optional[str] = None,
        user_name: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict:
        start_time = time.time()
        metrics.incr('requests.total')

        try:
            return self._process_internal(message, session_id, user_name, context, start_time)
        except Exception as e:
            logger.error(f"QueryProcessor critical error: {e}", exc_info=True)
            metrics.incr('errors.total')
            processing_time = int((time.time() - start_time) * 1000)
            metrics.observe_ms('request_latency', processing_time)
            
            return {
                'reply': (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try rephrasing your question or contact our support team for assistance."
                ),
                'confidence': 0.0,
                'source': 'error_fallback',
                'metadata': {
                    'error': str(e),
                    'processing_time_ms': processing_time
                },
                'rule_hit': None,
                'faq_hit': None,
                'llm_response': None
            }

    def _process_internal(
        self,
        message: str,
        session_id: Optional[str],
        user_name: Optional[str],
        context: Optional[Dict],
        start_time: float
    ) -> Dict:
        context = context or {}

        logger.info(f"Processing query: {message[:50]}...")

        result = {
            'reply': '',
            'confidence': 0.0,
            'source': 'unknown',
            'metadata': {},
            'rule_hit': None,
            'faq_hit': None,
            'llm_response': None
        }

        rule_result = self._check_rules(message, context)
        if rule_result['matched']:
            result['reply'] = rule_result['response']
            result['confidence'] = 1.0
            result['source'] = 'rule_engine'
            result['rule_hit'] = rule_result['rule']
            result['metadata'] = {
                'rule_id': rule_result['rule']['id'],
                'severity': rule_result['rule']['severity']
            }

            logger.info(f"✅ Rule matched: {rule_result['rule']['id']}")
            self._log_conversation(session_id, message, result)
            metrics.incr('routing.rule_engine')
            processing_time = int((time.time() - start_time) * 1000)
            metrics.observe_ms('request_latency', processing_time)
            result['metadata']['processing_time_ms'] = processing_time
            return result

        use_context = getattr(settings, 'PHASE1_CONTEXT_INTEGRATION', True)
        rag_context = context if use_context else {}
        
        rag_results = self._search_faqs_multiple(message, user_name, rag_context)
        top_result = rag_results[0] if rag_results else {
            'question': '',
            'answer': '',
            'confidence': 0.0,
            'method': 'none',
            'context_boost': 0.0
        }
        
        use_unified_confidence = getattr(settings, 'PHASE1_UNIFIED_CONFIDENCE', True)
        
        if use_unified_confidence:
            should_use_rag = self._should_use_rag(top_result, rag_results)
        else:
            should_use_rag = top_result['confidence'] >= ConfidenceConfig.RAG['high']
        
        if should_use_rag:
            result['reply'] = top_result['answer']
            result['confidence'] = top_result['confidence']
            result['source'] = 'rag_retriever'
            result['faq_hit'] = {
                'question': top_result['question'],
                'answer': top_result['answer'],
                'score': top_result['confidence'],
                'method': top_result['method']
            }
            result['metadata'] = {
                'matched_question': top_result['question'],
                'search_method': top_result['method'],
                'context_boost': top_result.get('context_boost', 0.0),
                'routing_decision': 'rag_direct'
            }

            logger.info(f"✅ FAQ matched with {top_result['confidence']:.2f} confidence")
            self._log_conversation(session_id, message, result)
            metrics.incr('routing.rag_direct')
            metrics.incr('faq.hit')
            processing_time = int((time.time() - start_time) * 1000)
            metrics.observe_ms('request_latency', processing_time)
            result['metadata']['processing_time_ms'] = processing_time
            return result

        use_llm_context = getattr(settings, 'PHASE1_LLM_CONTEXT_ENRICHMENT', True)
        
        llm_result = self._query_llm(
            message=message,
            context=context if use_llm_context else {},
            user_name=user_name,
            rag_results=rag_results if use_llm_context else None,
            rule_result=rule_result if use_llm_context else None
        )
        
        result['reply'] = llm_result['response']
        result['confidence'] = llm_result['confidence']
        result['source'] = 'llm'
        result['llm_response'] = llm_result['response']
        result['metadata'] = {
            'tokens': llm_result.get('tokens', 0),
            'time_ms': llm_result.get('time_ms', 0),
            'model': llm_result.get('model', 'unknown'),
            'context_provided': llm_result.get('context_provided', {}),
            'rag_references_used': llm_result.get('rag_references_used', []),
            'routing_decision': 'llm_fallback',
            'llm_error': llm_result.get('llm_error'),
            'fallback_used': llm_result.get('fallback_used', False),
            'prompt_estimated_tokens': llm_result.get('context_provided', {}).get('prompt_estimated_tokens', 0),
            'dropped_context_sections': llm_result.get('context_provided', {}).get('dropped_sections', []),
        }

        logger.info(f"✅ LLM response with {llm_result['confidence']:.2f} confidence")
        self._log_conversation(session_id, message, result)

        if llm_result.get('fallback_used'):
            metrics.incr('routing.llm_fallback')
        else:
            metrics.incr('routing.llm_direct')
        if llm_result.get('llm_error'):
            metrics.incr('llm.errors')

        processing_time = int((time.time() - start_time) * 1000)
        metrics.observe_ms('request_latency', processing_time)
        result['metadata']['processing_time_ms'] = processing_time
        return result

    def _should_use_rag(self, top_result: Dict, rag_results: List[Dict]) -> bool:
        """Adaptive routing: direct RAG for high confidence or stable medium-confidence lead."""
        top_conf = top_result.get('confidence', 0.0)
        if top_conf >= ConfidenceConfig.RAG['high']:
            return True

        if top_conf < ConfidenceConfig.RAG['medium']:
            return False

        second_conf = rag_results[1].get('confidence', 0.0) if len(rag_results) > 1 else 0.0
        separation = top_conf - second_conf
        return separation >= 0.08

    def _check_rules(self, message: str, context: Dict) -> Dict:
        try:
            rule_match = self.rule_engine.match(message)

            if rule_match:
                if self.rule_engine.should_block(rule_match):
                    response = self.rule_engine.get_blocked_response(rule_match)
                else:
                    response = rule_match.get('description', 'Your message has been flagged for review.')

                return {
                    'matched': True,
                    'response': response,
                    'rule': {
                        'id': rule_match.get('id', 'unknown'),
                        'action': rule_match.get('action', 'escalate'),
                        'severity': rule_match.get('severity', 'medium'),
                        'matched_phrase': rule_match.get('matched_phrase', '')
                    }
                }

            return {'matched': False}

        except Exception as e:
            logger.error(f"Rule engine error: {e}", exc_info=True)
            return {'matched': False}

    def _search_faqs_multiple(
        self, 
        query: str, 
        user_name: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        try:
            results = self.rag_retriever.search(query, k=3)

            if not results:
                return []

            processed_results = []
            for match in results:
                base_score = match['score']
                
                if context:
                    boosted_score, boost_amount = self._apply_context_boost(base_score, context)
                else:
                    boosted_score = base_score
                    boost_amount = 0.0

                answer = match['answer']
                if user_name and '{user_name}' not in answer:
                    if not any(greeting in answer.lower() for greeting in ['hi', 'hello', 'hey']):
                        answer = f"Hi {user_name}! {answer}"
                elif user_name:
                    answer = answer.replace('{user_name}', user_name)

                keywords = match.get('keywords', []) or []
                processed_results.append({
                    'id': match.get('id', ''),
                    'question': match['question'],
                    'answer': answer,
                    'confidence': boosted_score,
                    'method': 'faiss_semantic_search',
                    'context_boost': boost_amount,
                    'category': keywords[0] if keywords else 'general',
                    'policy_type': 'faq'
                })

            return processed_results

        except Exception as e:
            logger.error(f"RAG retriever error: {e}", exc_info=True)
            return []

    def _apply_context_boost(self, base_score: float, context: Dict) -> Tuple[float, float]:
        try:
            boost = 0.0
            
            sentiment_data = context.get('sentiment', {})
            current_sentiment = sentiment_data.get('current', 'neutral')
            
            escalation_data = context.get('escalation', {})
            escalation_level = escalation_data.get('level', 0)
            
            if current_sentiment in ['frustrated', 'angry'] or escalation_level >= 2:
                boost += 0.10
                logger.debug(f"Context boost: frustrated/escalated user (+0.10)")
            
            history = context.get('history', [])
            if len(history) > 5:
                boost += 0.05
                logger.debug(f"Context boost: long conversation (+0.05)")
            
            boosted_score = min(base_score + boost, 1.0)
            
            if boost > 0:
                logger.info(f"Context boost applied: {base_score:.3f} -> {boosted_score:.3f} (+{boost:.3f})")
            
            return boosted_score, boost
        except Exception as e:
            logger.warning(f"Context boost calculation failed: {e}")
            return base_score, 0.0

    def _query_llm(
        self,
        message: str,
        context: Dict,
        user_name: Optional[str] = None,
        rag_results: Optional[List[Dict]] = None,
        rule_result: Optional[Dict] = None
    ) -> Dict:
        try:
            system_prompt, context_info = self._build_enriched_system_prompt(
                message=message,
                context=context,
                user_name=user_name,
                rag_results=rag_results,
                rule_result=rule_result
            )

            start_time = time.time()
            llm_max_output_tokens = int(getattr(settings, 'LLM_MAX_OUTPUT_TOKENS', 500))
            llm_output = self.llm.generate(
                prompt=message,
                system_prompt=system_prompt,
                max_tokens=llm_max_output_tokens,
                temperature=0.7
            )
            time_ms = int((time.time() - start_time) * 1000)

            metrics.observe_ms('llm_latency', time_ms)
            llm_error = llm_output.get('error') if isinstance(llm_output, dict) else None
            if llm_error:
                fallback = self._build_llm_error_fallback(message=message, rag_results=rag_results)
                return {
                    'response': fallback['response'],
                    'confidence': fallback['confidence'],
                    'tokens': 0,
                    'time_ms': int((time.time() - start_time) * 1000),
                    'model': self.llm.model_name,
                    'context_provided': context_info,
                    'rag_references_used': fallback.get('rag_references_used', []),
                    'llm_error': llm_error,
                    'fallback_used': True,
                }

            response_text = llm_output.get('response', '') if isinstance(llm_output, dict) else str(llm_output)
            confidence = self._estimate_llm_confidence(response_text, message)

            rag_ids = []
            if rag_results:
                rag_ids = [r.get('id', '') for r in rag_results if r.get('id')]

            output_tokens = llm_output.get('tokens_generated', len(response_text.split())) if isinstance(llm_output, dict) else len(response_text.split())
            metrics.incr('llm.tokens', int(output_tokens or 0))

            return {
                'response': response_text,
                'confidence': confidence,
                'tokens': output_tokens,
                'time_ms': int((llm_output.get('generation_time', 0) or 0) * 1000) if isinstance(llm_output, dict) else time_ms,
                'model': llm_output.get('model', self.llm.model_name) if isinstance(llm_output, dict) else self.llm.model_name,
                'context_provided': context_info,
                'rag_references_used': rag_ids
            }

        except Exception as e:
            logger.error(f"LLM generation error: {e}", exc_info=True)
            return {
                'response': (
                    "I apologize, but I'm having trouble generating a response right now. "
                    "Please try again or contact our support team."
                ),
                'confidence': 0.0,
                'tokens': 0,
                'time_ms': 0,
                'model': 'error',
                'context_provided': {},
                'rag_references_used': []
            }

    def _build_enriched_system_prompt(
        self,
        message: str,
        context: Dict,
        user_name: Optional[str] = None,
        rag_results: Optional[List[Dict]] = None,
        rule_result: Optional[Dict] = None
    ) -> Tuple[str, Dict]:
        context_info = {
            'conversation_history': False,
            'rag_attempts': False,
            'user_sentiment': 'neutral',
            'escalation_level': 0,
            'context_sections': [],
        }

        metadata_info = context.get('metadata', {}) if isinstance(context, dict) else {}
        sentiment_data = context.get('sentiment', {}) if isinstance(context, dict) else {}
        escalation_data = context.get('escalation', {}) if isinstance(context, dict) else {}
        history = context.get('history', []) if isinstance(context, dict) else []

        current_sentiment = sentiment_data.get('current', 'neutral')
        escalation_level = escalation_data.get('level', 0)
        context_info['user_sentiment'] = current_sentiment
        context_info['escalation_level'] = escalation_level

        sections: Dict[str, List[str]] = {}
        sections['system_role'] = [
            'SYSTEM_ROLE:',
            'assistant=zunto_marketplace_support; style=clear_friendly_concise; '
            'scope=orders,payments,shipping,refunds,disputes',
        ]

        if user_name:
            sections['user_profile'] = ['USER_PROFILE:', f'display_name={user_name}']

        product_packets = self._build_product_context_packets(context)
        if product_packets:
            product_lines = ['PRODUCT_CONTEXT:']
            for idx, packet in enumerate(product_packets, 1):
                product_lines.append(f'PRODUCT_PACKET_{idx}: {packet}')
            sections['product_context'] = product_lines
            context_info['product_packets'] = len(product_packets)

        sections['conversation_state'] = [
            'CONVERSATION_STATE:',
            (
                f'sentiment={current_sentiment}; escalation_level={escalation_level}; '
                f"empathy_required={'yes' if current_sentiment in ['frustrated', 'angry'] else 'no'}"
            ),
        ]

        short_summary = metadata_info.get('short_memory_summary', {})
        if short_summary:
            sections['memory_summary'] = ['MEMORY_SUMMARY:', str(short_summary)]

        if len(history) >= 2:
            context_info['conversation_history'] = True
            recent_messages = history[-2:]
            recent_lines = ['RECENT_TURNS:']
            for msg in recent_messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:120]
                recent_lines.append(f'{role}={content}')
            sections['recent_turns'] = recent_lines

        if rag_results and len(rag_results) > 0:
            context_info['rag_attempts'] = True
            rag_lines = ['RETRIEVAL_EVIDENCE:']
            for i, result in enumerate(rag_results[:3], 1):
                packet = {
                    'id': result.get('id', ''),
                    'category': result.get('category', 'general'),
                    'policy_type': result.get('policy_type', 'faq'),
                    'similarity_score': round(result.get('confidence', 0.0), 4),
                    'question': result.get('question', ''),
                    'answer': result.get('answer', '')[:220],
                }
                rag_lines.append(f'FAQ_PACKET_{i}: {packet}')
            sections['retrieval_evidence'] = rag_lines

        if rule_result and rule_result.get('matched'):
            rule = rule_result.get('rule', {})
            sections['safety_policy'] = [
                'SAFETY_POLICY:',
                f"rule_id={rule.get('id', 'unknown')}; severity={rule.get('severity', 'medium')}",
            ]

        message_count = metadata_info.get('message_count', 0)
        if message_count > 5:
            sections['context_directive'] = ['CONTEXT_DIRECTIVE: maintain_response_consistency=yes']

        section_priority = [
            'system_role',
            'product_context',
            'retrieval_evidence',
            'conversation_state',
            'memory_summary',
            'recent_turns',
            'user_profile',
            'safety_policy',
            'context_directive',
        ]

        max_prompt_tokens = int(getattr(settings, 'LLM_MAX_PROMPT_TOKENS', 900))
        used_chars = 0
        prompt_parts: List[str] = []
        dropped_sections: List[str] = []

        for section_name in section_priority:
            lines = sections.get(section_name)
            if not lines:
                continue
            section_text = '\n'.join(lines)
            projected_tokens = (used_chars + len(section_text)) // 4
            if projected_tokens > max_prompt_tokens and section_name not in {'system_role', 'product_context'}:
                dropped_sections.append(section_name)
                continue

            prompt_parts.extend(lines)
            used_chars += len(section_text)
            context_info['context_sections'].append(section_name)

        context_info['prompt_estimated_tokens'] = max(1, used_chars // 4)
        context_info['prompt_max_tokens'] = max_prompt_tokens
        context_info['dropped_sections'] = dropped_sections

        final_prompt = '\n'.join(prompt_parts)
        return final_prompt, context_info

    def _build_product_context_packets(self, context: Dict) -> List[Dict[str, Any]]:
        # Build deterministic product packets from DB-backed product IDs only.
        candidate_ids: List[Any] = []
        metadata = context.get('metadata', {}) if isinstance(context, dict) else {}

        for key in ('product_id', 'product_ids'):
            value = context.get(key) if isinstance(context, dict) else None
            if value is None:
                value = metadata.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                candidate_ids.extend(value)
            else:
                candidate_ids.append(value)

        normalized_ids: List[int] = []
        for raw_id in candidate_ids:
            try:
                normalized_ids.append(int(raw_id))
            except (TypeError, ValueError):
                logger.debug(f"Skipping non-numeric product identifier: {raw_id}")

        if not normalized_ids:
            return []

        try:
            from market.models import Product

            products = Product.objects.filter(id__in=normalized_ids).select_related('seller', 'category')
            packets: List[Dict[str, Any]] = []
            for product in products:
                packets.append({
                    'id': int(product.id),
                    'name': product.title,
                    'price': str(product.price),
                    'stock': int(product.stock_quantity),
                    'attributes': {
                        'category': getattr(product.category, 'name', ''),
                        'condition': getattr(product, 'condition', ''),
                        'location': getattr(product, 'location', ''),
                    },
                    'policy_flags': {
                        'is_active': bool(product.is_active),
                        'is_approved': bool(product.is_approved),
                    },
                })
            return packets
        except Exception as exc:
            logger.warning(f"Failed to build product context packets: {exc}")
            return []

    def _estimate_llm_confidence(self, response: str, query: str) -> float:
        try:
            confidence = 0.7

            word_count = len(response.split())
            if word_count < 10:
                confidence -= 0.2
            elif word_count > 200:
                confidence -= 0.1

            hedging_phrases = [
                "i think", "maybe", "probably", "i'm not sure",
                "it seems", "perhaps", "might be"
            ]
            if any(phrase in response.lower() for phrase in hedging_phrases):
                confidence -= 0.15

            query_terms = set(query.lower().split())
            response_terms = set(response.lower().split())
            overlap = len(query_terms.intersection(response_terms))
            if overlap >= 2:
                confidence += 0.1

            return max(0.0, min(1.0, confidence))
        except Exception as e:
            logger.warning(f"Confidence estimation failed: {e}")
            return 0.5

    def _log_conversation(
        self,
        session_id: Optional[str],
        message: str,
        result: Dict
    ):
        if not session_id:
            return

        try:
            session_obj = None
            try:
                session_obj = ConversationSession.objects.get(session_id=session_id)
            except ConversationSession.DoesNotExist:
                logger.warning(f"Session not found: {session_id}")

            ConversationLog.objects.create(
                session=session_obj,
                anonymous_session_id=session_id,
                message=message,
                rule_hit=result.get('rule_hit'),
                faq_hit=result.get('faq_hit'),
                llm_response=result.get('llm_response'),
                llm_meta=result.get('metadata') if result['source'] == 'llm' else None,
                final_reply=result['reply'],
                confidence=result['confidence'],
                explanation=f"Source: {result['source']}",
                processing_time_ms=result['metadata'].get('processing_time_ms', 0)
            )

            logger.debug(f"Conversation logged for session {session_id[:8]}")

        except Exception as e:
            logger.error(f"Failed to log conversation: {e}", exc_info=True)

    def get_stats(self) -> Dict:
        try:
            from django.db.models import Count, Avg
            from django.utils import timezone
            from datetime import timedelta

            since = timezone.now() - timedelta(hours=24)
            logs = ConversationLog.objects.filter(created_at__gte=since)
            total_queries = logs.count()

            if total_queries == 0:
                return {
                    'total_queries': 0,
                    'avg_confidence': 0.0,
                    'avg_processing_time_ms': 0,
                    'source_distribution': {}
                }

            avg_confidence = logs.aggregate(Avg('confidence'))['confidence__avg'] or 0.0
            avg_time = logs.aggregate(Avg('processing_time_ms'))['processing_time_ms__avg'] or 0

            rule_hits = logs.exclude(rule_hit__isnull=True).count()
            faq_hits = logs.exclude(faq_hit__isnull=True).count()
            llm_hits = logs.exclude(llm_response__isnull=True).count()

            return {
                'total_queries': total_queries,
                'avg_confidence': round(avg_confidence, 2),
                'avg_processing_time_ms': int(avg_time),
                'source_distribution': {
                    'rule_engine': rule_hits,
                    'rag_retriever': faq_hits,
                    'llm': llm_hits
                },
                'period': '24h'
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {'error': str(e)}


def process_query(message: str, session_id: Optional[str] = None, **kwargs) -> Dict:
    processor = QueryProcessor()
    return processor.process(message, session_id=session_id, **kwargs)
