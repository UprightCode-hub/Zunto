"""
Assistant Views - REFACTORED with premium AI system and utils.
Handles /api/chat/ endpoint with modular conversation management.

NEW FEATURES:
- Premium ConversationManager with AI modules
- Enhanced logging with context tracking
- Escalation detection and flagging
- Rich conversation analytics
- Improved error handling
- Utils integration for validation and formatting

BACKWARD COMPATIBLE: All existing clients continue to work.
"""
import logging
import time
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.http import HttpResponse

from assistant.utils.tts_utils import get_tts_service
from assistant.models import ConversationSession, ConversationLog, Report
from assistant.processors.conversation_manager import ConversationManager
from assistant.serializers import (
    ConversationSessionSerializer,
    ConversationLogSerializer,
    ReportSerializer
)

# NEW: Import utils
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
from assistant.utils.formatters import (
    format_processing_time,
    format_conversation_summary,
    build_error_response
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat_endpoint(request):
    """
    Main chat endpoint with premium AI processing.
    
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
        # NEW: Comprehensive validation
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
        
        # Extract validated data
        message = sanitized_data['message']
        session_id = sanitized_data.get('session_id') or str(uuid.uuid4())
        user_id = sanitized_data.get('user_id')
        
        if 'session_id' not in sanitized_data:
            logger.info(f"New session created: {session_id[:8]}")
        
        # Get authenticated user if available
        if request.user.is_authenticated:
            user_id = request.user.id
        
        # Initialize conversation manager (with premium modules!)
        conv_manager = ConversationManager(session_id, user_id)
        
        logger.info(
            f"Processing message [session={session_id[:8]}, "
            f"state={conv_manager.get_current_state()}]: {message[:50]}..."
        )
        
        # Process message through premium system
        reply = conv_manager.process_message(message)
        
        # Get conversation summary for metadata
        summary = conv_manager.get_conversation_summary()
        
        # Check for escalation
        is_escalated = conv_manager.context_mgr.is_escalated()
        if is_escalated:
            logger.warning(
                f"🚨 ESCALATED: Session {session_id[:8]} - "
                f"User: {summary.get('user_name', 'unknown')}"
            )
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Build response
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
                'escalation_level': summary.get('escalation_level', 0)
            }
        }
        
        # Log conversation (legacy compatibility) - FIXED VERSION
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
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # NEW: Use formatter for error response
        error_message = build_error_response('processing_failed', include_help=True)
        
        # Return friendly error message
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
@permission_classes([AllowAny])
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
        # Validate request
        text = request.data.get('text', '').strip()
        
        if not text:
            return Response(
                {
                    'error': 'Text is required',
                    'reply': 'Please provide text to convert to speech'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get optional parameters
        voice = request.data.get('voice')
        speed = request.data.get('speed')
        use_cache = request.data.get('use_cache', True)
        
        # Validate voice
        valid_voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
        if voice and voice not in valid_voices:
            return Response(
                {
                    'error': f'Invalid voice. Choose from: {", ".join(valid_voices)}',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate speed
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
        
        # Get TTS service
        tts_service = get_tts_service()
        
        # Generate speech
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
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"TTS generated in {processing_time}ms "
            f"({len(audio_bytes)} bytes, cached={use_cache})"
        )
        
        # Return audio as HTTP response
        response = HttpResponse(audio_bytes, content_type='audio/mpeg')
        response['Content-Disposition'] = 'inline; filename="speech.mp3"'
        response['X-Processing-Time-Ms'] = str(processing_time)
        response['X-Audio-Size-Bytes'] = str(len(audio_bytes))
        response['Cache-Control'] = 'public, max-age=604800'  # 7 days
        
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
        # FIXED: Use anonymous_session_id for UUID strings instead of session_id
        ConversationLog.objects.create(
            user_id=user_id,
            anonymous_session_id=session_id,  # Changed from session_id to anonymous_session_id
            message=message,
            final_reply=reply,
            confidence=confidence,
            processing_time_ms=processing_time_ms,
            explanation='premium_ai_system'
        )
    except Exception as e:
        logger.error(f"Failed to log conversation: {e}")


@api_view(['GET'])
@permission_classes([AllowAny])
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
        # NEW: Validate session ID
        is_valid, error = validate_session_id(session_id)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get session
        try:
            session = ConversationSession.objects.get(session_id=session_id)
        except ConversationSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Initialize manager to get summary
        conv_manager = ConversationManager(session_id)
        summary = conv_manager.get_conversation_summary()
        
        # Add active status
        summary['is_active'] = session.is_active()
        summary['session_id'] = session_id
        summary['state'] = session.current_state
        
        # NEW: Add formatted summary
        summary['formatted_summary'] = format_conversation_summary(summary)
        
        return Response(summary, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Session status error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to retrieve session status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
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
        # NEW: Validate session ID
        is_valid, error = validate_session_id(session_id)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize manager and reset
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
        # Get user's sessions
        if request.user.is_authenticated:
            sessions = ConversationSession.objects.filter(
                user=request.user
            ).order_by('-last_activity')[:20]
        else:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Build session list with summaries
        session_list = []
        for session in sessions:
            try:
                conv_manager = ConversationManager(session.session_id)
                summary = conv_manager.get_conversation_summary()
                summary['session_id'] = session.session_id
                summary['last_activity'] = session.last_activity.isoformat()
                summary['is_active'] = session.is_active()
                
                # NEW: Add formatted summary
                summary['formatted_summary'] = format_conversation_summary(summary)
                
                session_list.append(summary)
            except Exception as e:
                logger.error(f"Failed to get summary for session {session.session_id}: {e}")
                # Add basic info as fallback
                session_list.append({
                    'session_id': session.session_id,
                    'state': session.current_state,
                    'user_name': session.user_name,
                    'last_activity': session.last_activity.isoformat(),
                    'is_active': session.is_active()
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
        
        # Check core components
        query_processor = QueryProcessor()
        
        components = {
            'query_processor': True,
            'rag_retriever': query_processor.rag.is_ready(),
            'llm': query_processor.llm.is_available() if query_processor.llm else False,
            'ai_modules': True,
            'flow_modules': True,
            'utils': True  # NEW
        }
        
        # Get version info
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


# LEGACY ENDPOINT: Backward compatibility
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
        
        # Create DRF-style request object
        class FakeRequest:
            def __init__(self, data, user):
                self.data = data
                self.user = user
        
        fake_request = FakeRequest(data, request.user)
        
        # Call new endpoint
        response = chat_endpoint(fake_request)
        
        # Convert to JsonResponse for legacy clients
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
@permission_classes([AllowAny])
def ask_assistant(request):
    """
    Legacy endpoint: Simple Q&A without conversation context.
    
    DEPRECATED: Use /api/chat/ for full conversational experience.
    """
    start_time = time.time()
    
    try:
        from assistant.processors.query_processor import QueryProcessor
        
        question = request.data.get('question', '').strip()
        user_id = request.data.get('user_id')
        
        # NEW: Validate message
        is_valid, error = validate_message(question)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process with query processor
        query_processor = QueryProcessor()
        result = query_processor.process(question)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log for analytics - FIXED VERSION
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
@permission_classes([AllowAny])
def create_report(request):
    """
    Legacy endpoint: Create a dispute/scam report.
    """
    try:
        user_id = request.data.get('user_id')
        report_type = request.data.get('report_type', 'dispute')
        description = request.data.get('description', '').strip()
        
        # Build report data
        report_data = {
            'message': description,
            'report_type': report_type,
            'seller_name': request.data.get('seller_name', ''),
            'order_id': request.data.get('order_id', ''),
            'evidence': request.data.get('evidence', '')
        }
        
        # NEW: Validate report data
        is_valid, error = validate_report_data(report_data)
        if not is_valid:
            return Response(
                {'error': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create report
        report_data['description'] = description
        report_data['status'] = 'pending'
        
        if user_id:
            report_data['user_id'] = user_id
        
        report = Report.objects.create(**report_data)
        
        logger.info(f"Report created: ID={report.id}, Type={report_type}")
        
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
        
        queryset = ConversationLog.objects.all().order_by('-timestamp')
        
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


# Alias for backward compatibility
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
    """
    About page with information about the AI system
    """
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


# LOCAL TESTING ONLY: Simple HTML interface
# PRODUCTION: Remove this and use React frontend on Render
@csrf_exempt  # Only for local testing
def chat_interface(request):
    """
    LOCAL TESTING ONLY: Serve simple chat.html
    
    PRODUCTION: This will be replaced with React frontend on Render.
    The React app will call the /assistant/api/chat/ endpoint.
    """
    return render(request, 'assistant/chat.html')