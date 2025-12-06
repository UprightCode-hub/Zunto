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
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render

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
        
        # Log conversation (legacy compatibility)
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
    """
    try:
        ConversationLog.objects.create(
            user_id=user_id,
            session_id=session_id,
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
        
        # Log for analytics
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
Add these views to your assistant/views.py file
These handle the web interface and documentation pages
"""


@api_view(['GET'])
@permission_classes([AllowAny])
def chat_interface(request):
    """
    Main landing page - Professional AI Assistant Interface
    This is the page you'll share on LinkedIn via ngrok
    """
    context = {
        'creator_name': 'Wisdom Ekwugha',
        'ai_name': 'Gigi - Zunto Assistant',
        'tagline': 'Your Intelligent E-commerce Support Companion',
        'version': '2.0 Premium Edition',
        'linkedin_url': 'https://www.linkedin.com/in/wisdom-ekwugha',  # Update with your actual LinkedIn
        'github_url': 'https://github.com/wisdomekwugha',  # Update with your actual GitHub
        'email': 'wisdom@zunto.com',  # Update with your email
    }
    return render(request, 'assistant/chat_interface.html', context)


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