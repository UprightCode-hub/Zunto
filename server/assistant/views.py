#server/assistant/views.py
import logging
import time
import uuid
import json
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponse

from assistant.utils.tts_utils import get_tts_service
from assistant.models import ConversationSession, ConversationLog, Report, DisputeMedia
from assistant.processors.conversation_manager import ConversationManager
from assistant.serializers import (
    ConversationSessionSerializer,
    ConversationLogSerializer,
    ReportSerializer,
    DisputeMediaSerializer
)

                   
from assistant.utils.constants import (
    STATE_GREETING,
    ERROR_MSG_EMPTY_MESSAGE,
    ERROR_MSG_PROCESSING_FAILED,
    SUCCESS_MSG_REPORT_SAVED,
    SYSTEM_VERSION
)
from assistant.utils.validators import (
    validate_message,
    validate_chat_request,
    validate_session_id,
    validate_report_data
)
from assistant.services.dispute_storage import dispute_storage
from assistant.tasks import validate_dispute_media_task
from assistant.throttles import (
    AssistantChatAnonThrottle,
    AssistantChatUserThrottle,
    DisputeReportAnonThrottle,
    DisputeReportUserThrottle,
    DisputeEvidenceUploadUserThrottle,
)
from core.audit import audit_event

from assistant.utils.formatters import (
    format_processing_time,
    format_conversation_summary,
    build_error_response
)

logger = logging.getLogger(__name__)


FAQ_FILE_PATH = Path(__file__).resolve().parent / 'data' / 'updated_faq.json'


FAQ_SECTION_RULES = [
    ('account', 'Account & Access', ('account', 'sign up', 'login', 'password', 'verify', 'verification', 'profile')),
    ('buying', 'Buying & Orders', ('buy', 'order', 'checkout', 'payment', 'cancel', 'purchase', 'invoice')),
    ('shipping', 'Shipping & Delivery', ('ship', 'delivery', 'delivered', 'tracking', 'location', 'address')),
    ('returns', 'Returns, Refunds & Disputes', ('refund', 'return', 'dispute', 'complaint', 'damaged', 'wrong item', 'not delivered')),
    ('selling', 'Selling on Zunto', ('sell', 'seller', 'listing', 'promote', 'boost', 'commission', 'withdraw')),
    ('safety', 'Security & Trust', ('scam', 'fraud', 'safe', 'security', 'report', 'suspicious', 'ban')),
]


def _load_faq_records():
    with FAQ_FILE_PATH.open('r', encoding='utf-8') as faq_file:
        payload = json.load(faq_file)
    return payload.get('faqs', [])


def _find_faq_section(question_text):
    text = (question_text or '').lower()
    for section_id, _section_title, triggers in FAQ_SECTION_RULES:
        if any(trigger in text for trigger in triggers):
            return section_id
    return 'general'


def _build_faq_sections(records):
    sections = {
        section_id: {'id': section_id, 'title': section_title, 'faqs': []}
        for section_id, section_title, _triggers in FAQ_SECTION_RULES
    }
    sections['general'] = {'id': 'general', 'title': 'General Marketplace Questions', 'faqs': []}

    for faq in records:
        section_id = _find_faq_section(faq.get('question', ''))
        sections[section_id]['faqs'].append({
            'id': faq.get('id'),
            'question': faq.get('question', ''),
            'answer': faq.get('answer', ''),
        })

    return [section for section in sections.values() if section['faqs']]

def _resolve_assistant_lane(request_data):
    lane = (request_data.get('assistant_lane') or 'inbox').strip().lower()
    if lane in {'customer_service', 'dispute'}:
        return 'customer_service'
    return 'inbox'


def _looks_like_dispute_request(message: str) -> bool:
    text = (message or '').lower()
    keywords = {
        'dispute', 'complaint', 'issue', 'problem', 'refund', 'scam',
        'seller', 'buyer', 'order issue', 'did not receive', 'not delivered',
        'damaged', 'chargeback', 'wrong item', 'fake product'
    }
    return any(keyword in text for keyword in keywords)


def _customer_service_redirect_message() -> str:
    return (
        "For disputes, please use the Customer Service button (top-right or Settings). "
        "The regular assistant cannot process dispute workflows."
    )


def _build_title_from_first_message(message, product_name=None):
    snippet = (message or '').strip()[:80].strip()
    if len(snippet) >= 8:
        return snippet
    return f"Conversation about {product_name or 'support'}"


def _handle_ephemeral_chat(message: str, lane: str):
    """Logged-out assistant flow: temporary session, no DB writes."""
    if lane == 'customer_service':
        if not _looks_like_dispute_request(message):
            return {
                'reply': "Customer Service mode handles disputes only. Please describe the dispute (what happened, product/order, and timeline).",
                'state': 'dispute_mode',
                'confidence': 0.9,
                'escalated': False,
                'metadata': {
                    'assistant_lane': lane,
                    'persistence': 'temporary',
                    'expires_after_minutes': 15,
                    'conversation_title': _build_title_from_first_message(message),
                    'mode': 'dispute_only'
                }
            }

        return {
            'reply': (
                "You're in Customer Service mode. Please share your dispute details: "
                "what happened, which product/order is affected, and the timeline. "
                "You can also upload screenshots and OPUS/WAV audio evidence after opening the dispute."
            ),
            'state': 'dispute_mode',
            'confidence': 0.95,
            'escalated': False,
            'metadata': {
                'assistant_lane': lane,
                'persistence': 'temporary',
                'expires_after_minutes': 15,
                'conversation_title': _build_title_from_first_message(message),
                'mode': 'dispute_only'
            }
        }

    if _looks_like_dispute_request(message):
        return {
            'reply': _customer_service_redirect_message(),
            'state': 'chat_mode',
            'confidence': 0.95,
            'escalated': False,
            'metadata': {
                'assistant_lane': lane,
                'persistence': 'temporary',
                'expires_after_minutes': 15,
                'conversation_title': _build_title_from_first_message(message),
                'mode': 'redirect_to_customer_service'
            }
        }

    processor = QueryProcessor()
    result = processor.process(
        message=message,
        session_id=None,
        user_name=None,
        context={}
    )

    reply = result.get('reply') or ERROR_MSG_PROCESSING_FAILED

    return {
        'reply': reply,
        'state': 'chat_mode',
        'confidence': result.get('confidence', 0.5),
        'escalated': False,
        'metadata': {
            'assistant_lane': lane,
            'persistence': 'temporary',
            'expires_after_minutes': 15,
            'conversation_title': _build_title_from_first_message(message),
            'processing_time_ms': result.get('metadata', {}).get('processing_time_ms', 0)
        }
    }




@api_view(['GET'])
@permission_classes([AllowAny])
def faq_sections(request):
    try:
        faq_records = _load_faq_records()
        sections = _build_faq_sections(faq_records)
        return Response({
            'count': len(faq_records),
            'sections': sections,
        }, status=status.HTTP_200_OK)
    except FileNotFoundError:
        logger.error('FAQ file not found at %s', FAQ_FILE_PATH)
        return Response({'detail': 'FAQ data is not available right now.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as exc:
        logger.error('FAQ endpoint error: %s', exc, exc_info=True)
        return Response({'detail': 'Unable to load FAQs right now.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AssistantChatUserThrottle])
def chat_endpoint(request):
    """
    Main chat endpoint.
    
    Request body:
    {
        "message": str,
        "session_id": str (optional),
        "user_id": int (optional)
    }
    
    Response:
    {
        "reply": str,
        "session_id": str,
        "state": str,
        "confidence": float,
        "escalated": bool,
        "metadata": {
            "processing_time_ms": int,
            "user_name": str,
            "conversation_summary": dict
        }
    }
    """
    start_time = time.time()
    
    try:
                                       
        is_valid, error, sanitized_data = validate_chat_request(request.data)
        
        if not is_valid:
            logger.warning(f"Invalid request: {error}")
            return Response(
                {
                    'error': error,
                    'reply': ERROR_MSG_EMPTY_MESSAGE
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
                                
        message = sanitized_data['message']
        cookie_session = request.COOKIES.get('assistant_temp_session')
        session_id = sanitized_data.get('session_id') or cookie_session or str(uuid.uuid4())
        user_id = sanitized_data.get('user_id')
        assistant_lane = _resolve_assistant_lane(request.data)

        if 'session_id' not in sanitized_data:
            logger.info(f"New session created: {session_id[:8]}")

                                                              
        user_id = request.user.id

                                                                 
        conv_manager = ConversationManager(session_id, user_id, assistant_lane=assistant_lane)
        
        logger.info(
            f"Processing message [session={session_id[:8]}, "
            f"state={conv_manager.get_current_state()}]: {message[:50]}..."
        )
        
                                                
        reply = conv_manager.process_message(message)
        
                                               
        summary = conv_manager.get_conversation_summary()
        
                              
        is_escalated = conv_manager.context_mgr.is_escalated()
        if is_escalated:
            logger.warning(
                f"🚨 ESCALATED: Session {session_id[:8]} - "
                f"User: {summary.get('user_name', 'unknown')}"
            )
        
                                   
        processing_time = int((time.time() - start_time) * 1000)
        
                        
        response_data = {
            'reply': reply,
            'session_id': session_id,
            'state': conv_manager.get_current_state(),
            'confidence': summary.get('satisfaction_score', 0.5),
            'escalated': is_escalated,
            'metadata': {
                'processing_time_ms': processing_time,
                'processing_time_display': format_processing_time(processing_time),
                'user_name': conv_manager.get_user_name(),
                'message_count': summary.get('message_count', 0),
                'sentiment': summary.get('sentiment', 'neutral'),
                'escalation_level': summary.get('escalation_level', 0),
                'assistant_lane': assistant_lane,
                'persistence': 'persistent',
                'conversation_title': conv_manager.session.conversation_title
            }
        }
        
                                                                 
        _log_conversation(
            user_id=user_id,
            session_id=session_id,
            message=message,
            reply=reply,
            confidence=summary.get('satisfaction_score', 0.5),
            processing_time_ms=processing_time
        )
        
        logger.info(
            f"Response generated in {processing_time}ms "
            f"[state={response_data['state']}, escalated={is_escalated}]"
        )
        
        audit_event(request, action='assistant.chat.persistent', session_id=session_id, extra={'assistant_lane': assistant_lane})
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        
        processing_time = int((time.time() - start_time) * 1000)
        
                                               
        error_message = build_error_response('processing_failed', include_help=True)
        
                                       
        return Response(
            {
                'error': 'An error occurred while processing your message',
                'reply': error_message,
                'session_id': session_id if 'session_id' in locals() else str(uuid.uuid4()),
                'state': 'error',
                'metadata': {
                    'processing_time_ms': processing_time,
                    'error_type': type(e).__name__
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tts_endpoint(request):
    """
    Text-to-Speech endpoint for assistant messages.
    
    POST /assistant/api/tts/
    
    Request body:
    {
        "text": str (required) - Text to convert to speech,
        "voice": str (optional) - Voice: alloy, echo, fable, onyx, nova, shimmer,
        "speed": float (optional) - Speed: 0.25 to 4.0 (default: 1.0),
        "use_cache": bool (optional) - Use cached audio (default: true)
    }
    
    Response:
        - Success: audio/mpeg stream
        - Error: JSON error message
    """
    start_time = time.time()
    
    try:
                          
        text = request.data.get('text', '').strip()
        
        if not text:
            return Response(
                {
                    'error': 'Text is required',
                    'reply': 'Please provide text to convert to speech'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
                                 
        voice = request.data.get('voice')
        speed = request.data.get('speed')
        use_cache = request.data.get('use_cache', True)
        
                        
        valid_voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
        if voice and voice not in valid_voices:
            return Response(
                {
                    'error': f'Invalid voice. Choose from: {", ".join(valid_voices)}',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
                        
        if speed is not None:
            try:
                speed = float(speed)
                if not (0.25 <= speed <= 4.0):
                    return Response(
                        {'error': 'Speed must be between 0.25 and 4.0'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Speed must be a number'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
                         
        tts_service = get_tts_service()
        
                         
        success, audio_bytes, error_msg = tts_service.generate_speech(
            text=text,
            voice=voice,
            speed=speed,
            use_cache=use_cache
        )
        
        if not success:
            logger.error(f"TTS generation failed: {error_msg}")
            return Response(
                {
                    'error': error_msg or 'Failed to generate speech',
                    'reply': 'Sorry, I could not generate audio for this message'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
                                   
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"TTS generated in {processing_time}ms "
            f"({len(audio_bytes)} bytes, cached={use_cache})"
        )
        
                                       
        response = HttpResponse(audio_bytes, content_type='audio/mpeg')
        response['Content-Disposition'] = 'inline; filename="speech.mp3"'
        response['X-Processing-Time-Ms'] = str(processing_time)
        response['X-Audio-Size-Bytes'] = str(len(audio_bytes))
        response['Cache-Control'] = 'public, max-age=604800'          
        
        return response
    
    except Exception as e:
        logger.error(f"TTS endpoint error: {e}", exc_info=True)
        processing_time = int((time.time() - start_time) * 1000)
        
        return Response(
            {
                'error': 'An error occurred while generating speech',
                'reply': 'Sorry, I could not generate audio at this time',
                'metadata': {
                    'processing_time_ms': processing_time,
                    'error_type': type(e).__name__
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def tts_health(request):
    """
    TTS health check endpoint.
    
    GET /assistant/api/tts/health/
    
    Response:
    {
        "status": "healthy" | "unhealthy",
        "api_key_configured": bool,
        "cache_enabled": bool,
        "model": str,
        "default_voice": str
    }
    """
    try:
        tts_service = get_tts_service()
        cache_stats = tts_service.get_cache_stats()
        
        is_healthy = bool(tts_service.api_key)
        
        return Response(
            {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'api_key_configured': is_healthy,
                'cache_enabled': cache_stats['cache_enabled'],
                'model': cache_stats['model'],
                'default_voice': cache_stats['default_voice'],
                'cache_timeout_seconds': cache_stats['cache_timeout_seconds']
            },
            status=status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    except Exception as e:
        logger.error(f"TTS health check error: {e}", exc_info=True)
        return Response(
            {
                'status': 'unhealthy',
                'error': str(e)
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )



def _log_conversation(
    user_id: int,
    session_id: str,
    message: str,
    reply: str,
    confidence: float,
    processing_time_ms: int
):
    """
    Log conversation to database for analytics.
    Legacy compatibility function.
    
    FIXED: Now handles UUID session_id correctly by using anonymous_session_id field.
    """
    try:
                                                                                
        ConversationLog.objects.create(
            user_id=user_id,
            anonymous_session_id=session_id,                                                   
            message=message,
            final_reply=reply,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            explanation='premium_ai_system'
        )
    except Exception as e:
        logger.error(f"Failed to log conversation: {e}")


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_status(request, session_id):
    """
    Get current session status and conversation summary.
    
    GET /api/chat/session/<session_id>/
    
    Response:
    {
        "session_id": str,
        "state": str,
        "user_name": str,
        "message_count": int,
        "duration_minutes": int,
        "sentiment": str,
        "satisfaction_score": float,
        "escalation_level": int,
        "is_active": bool,
        "formatted_summary": str
    }
    """
    try:
                                  
        is_valid, error = validate_session_id(session_id)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
                     
        try:
            session = ConversationSession.objects.get(session_id=session_id)
        except ConversationSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
                                           
        conv_manager = ConversationManager(session_id)
        summary = conv_manager.get_conversation_summary()
        
                           
        summary['is_active'] = session.is_active()
        summary['session_id'] = session_id
        summary['state'] = session.current_state
        
                                    
        summary['formatted_summary'] = format_conversation_summary(summary)
        
        return Response(summary, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Session status error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to retrieve session status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_session(request, session_id):
    """
    Reset session to initial state.
    
    POST /api/chat/session/<session_id>/reset/
    
    Response:
    {
        "message": str,
        "session_id": str,
        "state": str
    }
    """
    try:
                                  
        is_valid, error = validate_session_id(session_id)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
                                      
        conv_manager = ConversationManager(session_id)
        conv_manager.reset_session()
        
        logger.info(f"Session reset: {session_id[:8]}")
        
        return Response(
            {
                'message': 'Session reset successfully',
                'session_id': session_id,
                'state': STATE_GREETING
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Session reset error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to reset session'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_sessions(request):
    """
    List all sessions for authenticated user.
    Requires authentication.
    
    GET /api/chat/sessions/
    
    Response:
    {
        "sessions": [
            {
                "session_id": str,
                "state": str,
                "user_name": str,
                "message_count": int,
                "last_activity": str,
                "is_active": bool,
                "formatted_summary": str
            }
        ]
    }
    """
    try:
                             
        if request.user.is_authenticated:
            sessions = ConversationSession.objects.filter(
                user=request.user,
                is_persistent=True
            ).order_by('-last_activity')[:20]
        else:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
                                           
        session_list = []
        for session in sessions:
            try:
                conv_manager = ConversationManager(session.session_id)
                summary = conv_manager.get_conversation_summary()
                summary['session_id'] = session.session_id
                summary['last_activity'] = session.last_activity.isoformat()
                summary['is_active'] = session.is_active()
                
                                            
                summary['formatted_summary'] = format_conversation_summary(summary)
                summary['assistant_lane'] = session.assistant_lane
                summary['conversation_title'] = session.conversation_title

                session_list.append(summary)
            except Exception as e:
                logger.error(f"Failed to get summary for session {session.session_id}: {e}")
                                            
                session_list.append({
                    'session_id': session.session_id,
                    'state': session.current_state,
                    'user_name': session.user_name,
                    'last_activity': session.last_activity.isoformat(),
                    'is_active': session.is_active(),
                    'assistant_lane': session.assistant_lane,
                    'conversation_title': session.conversation_title
                })
        
        return Response(
            {'sessions': session_list},
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"List sessions error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to retrieve sessions'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint for monitoring.
    
    GET /api/chat/health/
    
    Response:
    {
        "status": "healthy",
        "version": str,
        "components": {
            "query_processor": bool,
            "rag_retriever": bool,
            "llm": bool,
            "ai_modules": bool
        }
    }
    """
    try:
        from assistant.processors.query_processor import QueryProcessor
        from assistant.ai import get_module_info
        from assistant.flows import get_module_info as get_flows_info
        
                               
        query_processor = QueryProcessor()
        
        components = {
            'query_processor': True,
            'rag_retriever': query_processor.rag.is_ready(),
            'llm': query_processor.llm.is_available() if query_processor.llm else False,
            'ai_modules': True,
            'flow_modules': True,
            'utils': True       
        }
        
                          
        ai_info = get_module_info()
        flows_info = get_flows_info()
        
        return Response(
            {
                'status': 'healthy' if all(components.values()) else 'degraded',
                'version': SYSTEM_VERSION,
                'components': components,
                'ai_version': ai_info['version'],
                'flows_version': flows_info['version']
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return Response(
            {
                'status': 'unhealthy',
                'error': str(e)
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


                                         
@csrf_exempt
@require_http_methods(["POST"])
def legacy_chat_endpoint(request):
    """
    Legacy chat endpoint for backward compatibility.
    Redirects to new chat_endpoint.
    
    DEPRECATED: Use /api/chat/ instead.
    """
    import json
    
    try:
        data = json.loads(request.body)
        
                                         
        class FakeRequest:
            def __init__(self, data, user):
                self.data = data
                self.user = user
        
        fake_request = FakeRequest(data, request.user)
        
                           
        response = chat_endpoint(fake_request)
        
                                                    
        return JsonResponse(response.data, status=response.status_code)
    
    except Exception as e:
        logger.error(f"Legacy endpoint error: {e}")
        return JsonResponse(
            {'error': str(e)},
            status=500
        )


"""
Legacy View Functions - Backward compatibility for existing API clients.
"""

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_assistant(request):
    """
    Legacy endpoint: Simple Q&A without conversation context.
    
    DEPRECATED: Use /api/chat/ for full conversational experience.
    """
    start_time = time.time()
    
    try:
        from assistant.processors.query_processor import QueryProcessor
        
        question = request.data.get('question', '').strip()
        user_id = request.user.id if request.user.is_authenticated else None
        
                               
        is_valid, error = validate_message(question)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
                                      
        query_processor = QueryProcessor()
        result = query_processor.process(question)
        
        processing_time = int((time.time() - start_time) * 1000)
        
                                           
        if user_id:
            _log_conversation(
                user_id=user_id,
                session_id='legacy_ask',
                message=question,
                reply=result['reply'],
                confidence=result['confidence'],
                processing_time_ms=processing_time
            )
        
        return Response(
            {
                'answer': result['reply'],
                'confidence': result['confidence'],
                'processing_time_ms': processing_time,
                'processing_time_display': format_processing_time(processing_time)
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Ask assistant error: {e}", exc_info=True)
        processing_time = int((time.time() - start_time) * 1000)
        
        return Response(
            {
                'error': 'Failed to process question',
                'answer': ERROR_MSG_PROCESSING_FAILED,
                'processing_time_ms': processing_time
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([DisputeReportUserThrottle])
def create_report(request):
    """
    Legacy endpoint: Create a dispute/scam report.
    """
    try:
        user_id = request.user.id if request.user.is_authenticated else None
        report_type = request.data.get('report_type', 'dispute')
        description = request.data.get('description', '').strip()
        
                           
        report_data = {
            'message': description,
            'report_type': report_type,
            'category': request.data.get('category', ''),
            'meta': {
                'seller_name': request.data.get('seller_name', ''),
                'order_id': request.data.get('order_id', ''),
                'evidence_note': request.data.get('evidence', ''),
            }
        }
        
                                   
        is_valid, error = validate_report_data(report_data)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
                       
        report_data['status'] = 'pending'
        
        if user_id:
            report_data['user_id'] = user_id
        
        report = Report.objects.create(**report_data)
        
        logger.info(f"Report created: ID={report.id}, Type={report_type}")
        audit_event(request, action='assistant.report.created', extra={'report_id': report.id, 'report_type': report_type})
        
        return Response(
            {
                'message': SUCCESS_MSG_REPORT_SAVED,
                'report_id': report.id,
                'status': report.status
            },
            status=status.HTTP_201_CREATED
        )
    
    except Exception as e:
        logger.error(f"Create report error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to create report'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([DisputeEvidenceUploadUserThrottle])
def upload_report_evidence(request, report_id):
    """Upload evidence (max 5 images, 1 audio) for dispute reports."""
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

    if report.report_type != 'dispute':
        return Response({'error': 'Evidence uploads are only supported for dispute reports.'}, status=status.HTTP_400_BAD_REQUEST)

    if request.user.is_authenticated and report.user_id and report.user_id != request.user.id and not request.user.is_staff:
        return Response({'error': 'You do not have permission to upload evidence to this report.'}, status=status.HTTP_403_FORBIDDEN)

    uploaded_file = request.FILES.get('file')
    media_type = (request.data.get('media_type') or '').strip().lower()

    if not uploaded_file:
        return Response({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)

    if media_type not in {'image', 'audio'}:
        return Response({'error': "media_type must be 'image' or 'audio'"}, status=status.HTTP_400_BAD_REQUEST)

    mime_type = getattr(uploaded_file, 'content_type', '') or ''
    file_size = getattr(uploaded_file, 'size', 0) or 0

    max_image_mb = 5
    max_audio_mb = 15

    if media_type == 'image':
        image_count = report.evidence_files.filter(media_type='image', is_deleted=False).count()
        if image_count >= 5:
            return Response({'error': 'Maximum 5 image evidence files allowed per dispute.'}, status=status.HTTP_400_BAD_REQUEST)
        if not mime_type.startswith('image/'):
            return Response({'error': 'Invalid image content type.'}, status=status.HTTP_400_BAD_REQUEST)
        if file_size > max_image_mb * 1024 * 1024:
            return Response({'error': f'Image evidence must be <= {max_image_mb}MB.'}, status=status.HTTP_400_BAD_REQUEST)

    if media_type == 'audio':
        allowed_audio = {'audio/ogg', 'audio/opus', 'audio/wav', 'audio/x-wav', 'audio/wave'}
        if mime_type not in allowed_audio:
            return Response({'error': 'Audio evidence must be OPUS or WAV.'}, status=status.HTTP_400_BAD_REQUEST)
        if file_size > max_audio_mb * 1024 * 1024:
            return Response({'error': f'Audio evidence must be <= {max_audio_mb}MB.'}, status=status.HTTP_400_BAD_REQUEST)
        existing_audio = report.evidence_files.filter(media_type='audio', is_deleted=False).count()
        if existing_audio >= 1:
            return Response({'error': 'Only one audio evidence file is allowed per dispute.'}, status=status.HTTP_400_BAD_REQUEST)

    media = DisputeMedia(
        report=report,
        media_type=media_type,
        file=uploaded_file,
        original_filename=uploaded_file.name[:255],
        mime_type=mime_type,
        file_size=file_size,
        uploaded_by=request.user if request.user.is_authenticated else None,
    )
    media.source_storage = dispute_storage.backend_name
    media.storage_key = dispute_storage.build_storage_key(uploaded_file.name)
    media.refresh_retention()
    media.validation_status = DisputeMedia.VALIDATION_PENDING
    media.save()

    try:
        validate_dispute_media_task.delay(media.id)
    except Exception:
                                                                 
        logger.exception('Failed to enqueue dispute media validation task')

    audit_event(request, action='assistant.report.evidence_uploaded', extra={'report_id': report.id, 'media_id': media.id, 'media_type': media_type})
    serializer = DisputeMediaSerializer(media, context={'request': request})
    return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_report_evidence(request, report_id):
    """List evidence files for a dispute report."""
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.user.is_authenticated and report.user_id and report.user_id != request.user.id and not request.user.is_staff:
        return Response({'error': 'You do not have permission to view evidence for this report.'}, status=status.HTTP_403_FORBIDDEN)

    limit = min(int(request.GET.get('limit', 20)), 100)
    files = report.evidence_files.filter(is_deleted=False, validation_status=DisputeMedia.VALIDATION_APPROVED).order_by('-created_at')[:limit]
    serializer = DisputeMediaSerializer(files, many=True, context={'request': request})

    return Response({'report_id': report.id, 'evidence_files': serializer.data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_report(request, report_id):
    """Resolve/close report and set media retention to 90 days."""
    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

    if not request.user.is_authenticated or (not request.user.is_staff and report.user_id != request.user.id):
        return Response({'error': 'You do not have permission to close this report.'}, status=status.HTTP_403_FORBIDDEN)

    if report.status not in {'resolved', 'closed'}:
        report.status = 'resolved'
        report.resolved_at = timezone.now()
        update_fields = ['status', 'resolved_at']
        if request.user.is_staff:
            report.resolved_by = request.user
            update_fields.append('resolved_by')
        report.save(update_fields=update_fields)

    updated = 0
    for evidence in report.evidence_files.filter(is_deleted=False):
        evidence.refresh_retention()
        evidence.save(update_fields=['retention_expires_at', 'updated_at'])
        updated += 1

    audit_event(request, action='assistant.report.closed', extra={'report_id': report.id, 'retention_files_updated': updated})
    return Response({
        'report_id': report.id,
        'status': report.status,
        'resolved_at': report.resolved_at,
        'retention_files_updated': updated
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def recent_logs(request):
    """Admin endpoint: Get recent conversation logs."""
    try:
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        limit = min(int(request.GET.get('limit', 50)), 200)
        user_id = request.GET.get('user_id')
        
        queryset = ConversationLog.objects.all().order_by('-created_at')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        logs = queryset[:limit]
        serializer = ConversationLogSerializer(logs, many=True)
        
        return Response(
            {
                'logs': serializer.data,
                'count': queryset.count()
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Recent logs error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to retrieve logs'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def recent_reports(request):
    """Admin endpoint: Get recent reports."""
    try:
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        limit = min(int(request.GET.get('limit', 50)), 200)
        status_filter = request.GET.get('status')
        
        queryset = Report.objects.all().order_by('-created_at')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        reports = queryset[:limit]
        serializer = ReportSerializer(reports, many=True)
        
        return Response(
            {
                'reports': serializer.data,
                'count': queryset.count()
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.error(f"Recent reports error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to retrieve reports'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


                                  
chat = chat_endpoint


"""
Web Interface Views - For local testing only
PRODUCTION NOTE: In production, use React/Next.js frontend via Render
"""


@api_view(['GET'])
@permission_classes([AllowAny])
def api_documentation(request):
    """
    API Documentation page for developers
    Shows all available endpoints and how to use them
    """
    endpoints = [
        {
            'endpoint': '/assistant/api/chat/',
            'method': 'POST',
            'description': 'Main chat endpoint for conversational AI',
            'auth': 'Optional',
            'example': {
                'message': 'Hello, I need help',
                'session_id': 'optional-uuid',
                'user_id': 'optional-int'
            }
        },
        {
            'endpoint': '/assistant/api/chat/session/<session_id>/',
            'method': 'GET',
            'description': 'Get session status and conversation summary',
            'auth': 'Optional',
        },
        {
            'endpoint': '/assistant/api/chat/health/',
            'method': 'GET',
            'description': 'System health check',
            'auth': 'None',
        },
        {
            'endpoint': '/assistant/api/ask/',
            'method': 'POST',
            'description': 'Simple Q&A without conversation context (Legacy)',
            'auth': 'Optional',
        },
    ]
    
    return Response({
        'title': 'Zunto AI Assistant API Documentation',
        'version': SYSTEM_VERSION,
        'creator': 'Wisdom Ekwugha',
        'endpoints': endpoints,
        'base_url': request.build_absolute_uri('/assistant/'),
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def about_page(request):
    """About page endpoint."""
    return Response({
        'project': 'Zunto AI Assistant',
        'version': SYSTEM_VERSION,
        'creator': {
            'name': 'Wisdom Ekwugha',
            'role': 'AI Engineer & Full-Stack Developer',
            'linkedin': 'https://www.linkedin.com/in/wisdom-ekwugha',
            'github': 'https://github.com/wisdomekwugha',
        },
        'description': 'An intelligent conversational AI assistant for e-commerce support, '
                      'featuring advanced NLP, sentiment analysis, and escalation detection.',
        'features': [
            'Real-time conversational AI',
            'Context-aware responses',
            'Sentiment analysis',
            'Automatic escalation detection',
            'FAQ retrieval system',
            'Dispute resolution flow',
            'Multi-session management',
            'Advanced analytics',
        ],
        'tech_stack': [
            'Django REST Framework',
            'Python NLP Libraries',
            'FAISS Vector Database',
            'WebSocket Support',
            'PostgreSQL/SQLite',
        ],
        'year': '2024',
    }, status=status.HTTP_200_OK)


                                           
                                                          
@csrf_exempt                          
def chat_interface(request):
    """
    LOCAL TESTING ONLY: Serve simple chat.html
    
    PRODUCTION: This will be replaced with React frontend on Render.
    The React app will call the /assistant/api/chat/ endpoint.
    """
    return render(request, 'assistant/chat.html')
