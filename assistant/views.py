import time
import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Report, ConversationLog
from .serializers import (
    AskRequestSerializer,
    AskResponseSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    ConversationLogSerializer
)
from .processors.query_processor import QueryProcessor
from .permissions import IsStaffUser

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def ask_assistant(request):
    """
    Main endpoint for asking the assistant a question.
    
    POST /assistant/api/ask/
    {
        "message": "How do I request a refund?",
        "user_id": 123,  // optional
        "session_id": "abc123"  // optional for anonymous users
    }
    """
    start_time = time.time()
    
    # Validate input
    serializer = AskRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid request', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    message = serializer.validated_data['message']
    user_id = serializer.validated_data.get('user_id')
    session_id = serializer.validated_data.get('session_id', '')
    
    # Get user if authenticated
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"User ID {user_id} not found")
    
    # If no session_id provided, generate one
    if not session_id and not user:
        import uuid
        session_id = str(uuid.uuid4())
    
    try:
        # Process the query
        processor = QueryProcessor()
        result = processor.process(message)
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Save to conversation log
        log = ConversationLog.objects.create(
            user=user,
            session_id=session_id,
            message=message,
            rule_hit=result.get('rule'),
            faq_hit=result.get('faq'),
            llm_response=result.get('llm', {}).get('text', ''),
            llm_meta=result.get('llm', {}).get('meta'),
            final_reply=result['reply'],
            confidence=result['confidence'],
            explanation=result['explanation'],
            processing_time_ms=processing_time_ms
        )
        
        # Return response
        response_data = {
            'faq': result.get('faq'),
            'rule': result.get('rule'),
            'llm': result.get('llm'),
            'reply': result['reply'],
            'confidence': result['confidence'],
            'explanation': result['explanation']
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error processing assistant query: {e}", exc_info=True)
        return Response(
            {
                'error': 'Failed to process query',
                'reply': 'I apologize, but I encountered an error. Please try again or contact support.',
                'confidence': 0.0,
                'explanation': 'System error occurred'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_report(request):
    """
    Create a report for issues requiring human review.
    
    POST /assistant/api/report/
    {
        "message": "User threatened me",
        "severity": "high",  // optional
        "meta": {"conversation_id": 123}  // optional
    }
    """
    serializer = ReportCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid request', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get user if authenticated
    user = request.user if request.user.is_authenticated else None
    
    # Create report
    report = serializer.save(user=user)
    
    # Return created report
    response_serializer = ReportSerializer(report)
    return Response(
        response_serializer.data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([IsStaffUser])
def recent_logs(request):
    """
    Get recent conversation logs (admin only).
    
    GET /assistant/api/admin/recent-logs/?limit=50&user_id=123
    """
    limit = int(request.query_params.get('limit', 50))
    user_id = request.query_params.get('user_id')
    
    queryset = ConversationLog.objects.all()
    
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    logs = queryset[:limit]
    serializer = ConversationLogSerializer(logs, many=True)
    
    return Response({
        'count': len(logs),
        'logs': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsStaffUser])
def recent_reports(request):
    """
    Get recent reports (admin only).
    
    GET /assistant/api/admin/recent-reports/?limit=50&status=pending
    """
    limit = int(request.query_params.get('limit', 50))
    status_filter = request.query_params.get('status')
    
    queryset = Report.objects.all()
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    reports = queryset[:limit]
    serializer = ReportSerializer(reports, many=True)
    
    return Response({
        'count': len(reports),
        'reports': serializer.data
    })


# ==> Zunto-src/assistant/urls.py <==
from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    # Public endpoints
    path('api/ask/', views.ask_assistant, name='ask'),
    path('api/report/', views.create_report, name='report'),
    
    # Admin endpoints
    path('api/admin/recent-logs/', views.recent_logs, name='recent_logs'),
    path('api/admin/recent-reports/', views.recent_reports, name='recent_reports'),
]


# ==> Zunto-src/assistant/processors/__init__.py <==
"""
Assistant processing modules.

- faq_retriever: FAQ matching using keyword and TF-IDF
- rule_engine: Rule-based decision making
- local_model: Optional local LLM integration
- query_processor: Main orchestration logic
"""


# ==> Zunto-src/assistant/processors/faq_retriever.py <==
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

# Default thresholds
KEYWORD_SCORE_THRESHOLD = 0.4
TFIDF_SIMILARITY_THRESHOLD = 0.25


class FAQRetriever:
    """
    FAQ retrieval using keyword matching and TF-IDF similarity.
    Singleton pattern for efficiency.
    """
    
    _instance = None
    
    def __init__(self, faq_path: Optional[str] = None):
        """Initialize FAQ retriever with data file."""
        if faq_path is None:
            # Default path relative to this file
            base_dir = Path(__file__).parent.parent
            faq_path = base_dir / 'data' / 'faq.json'
        
        self.faq_path = Path(faq_path)
        self.faqs: List[Dict] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.faq_vectors = None
        
        # Load FAQ data
        self._load_faqs()
        
        # Initialize TF-IDF if we have FAQs
        if self.faqs:
            self._init_tfidf()
    
    @classmethod
    def get_instance(cls, faq_path: Optional[str] = None):
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(faq_path)
        return cls._instance
    
    def _load_faqs(self):
        """Load FAQ data from JSON file."""
        if not self.faq_path.exists():
            logger.warning(f"FAQ file not found: {self.faq_path}")
            return
        
        try:
            with open(self.faq_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.faqs = data.get('faqs', [])
            
            logger.info(f"Loaded {len(self.faqs)} FAQs from {self.faq_path}")
        except Exception as e:
            logger.error(f"Failed to load FAQs: {e}")
            self.faqs = []
    
    def _init_tfidf(self):
        """Initialize TF-IDF vectorizer and compute FAQ vectors."""
        try:
            # Combine question and keywords for better matching
            corpus = []
            for faq in self.faqs:
                text = faq['question']
                if 'keywords' in faq:
                    text += ' ' + ' '.join(faq['keywords'])
                corpus.append(text.lower())
            
            # Create vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 2),
                stop_words='english'
            )
            
            # Fit and transform FAQ corpus
            self.faq_vectors = self.vectorizer.fit_transform(corpus)
            
            logger.info(f"Initialized TF-IDF with {self.faq_vectors.shape[0]} FAQs")
        except Exception as e:
            logger.error(f"Failed to initialize TF-IDF: {e}")
            self.vectorizer = None
            self.faq_vectors = None
    
    def _keyword_match(self, query: str) -> Optional[Dict]:
        """
        Match query against FAQ keywords.
        Returns: {faq, score, method} or None
        """
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        best_match = None
        best_score = 0.0
        
        for faq in self.faqs:
            if 'keywords' not in faq:
                continue
            
            # Calculate keyword overlap
            faq_keywords = set(kw.lower() for kw in faq['keywords'])
            overlap = query_words & faq_keywords
            
            if overlap:
                score = len(overlap) / max(len(query_words), len(faq_keywords))
                
                if score > best_score:
                    best_score = score
                    best_match = faq
        
        if best_match and best_score >= KEYWORD_SCORE_THRESHOLD:
            return {
                'faq': best_match,
                'score': best_score,
                'method': 'keyword'
            }
        
        return None
    
    def _tfidf_match(self, query: str) -> Optional[Dict]:
        """
        Match query using TF-IDF similarity.
        Returns: {faq, score, method} or None
        """
        if self.vectorizer is None or self.faq_vectors is None:
            return None
        
        try:
            # Transform query
            query_vector = self.vectorizer.transform([query.lower()])
            
            # Compute similarities
            similarities = cosine_similarity(query_vector, self.faq_vectors)[0]
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            
            if best_score >= TFIDF_SIMILARITY_THRESHOLD:
                return {
                    'faq': self.faqs[best_idx],
                    'score': float(best_score),
                    'method': 'tfidf'
                }
        except Exception as e:
            logger.error(f"TF-IDF matching failed: {e}")
        
        return None
    
    def retrieve(self, query: str) -> Optional[Dict]:
        """
        Retrieve best matching FAQ for query.
        
        Args:
            query: User's question
        
        Returns:
            {
                'id': int,
                'question': str,
                'answer': str,
                'score': float,
                'method': 'keyword' | 'tfidf'
            } or None
        """
        if not query or not self.faqs:
            return None
        
        # Try keyword matching first (faster and more precise)
        result = self._keyword_match(query)
        
        # Fall back to TF-IDF if no keyword match
        if result is None:
            result = self._tfidf_match(query)
        
        # Format result
        if result:
            faq = result['faq']
            return {
                'id': faq.get('id', 0),
                'question': faq['question'],
                'answer': faq['answer'],
                'score': result['score'],
                'method': result['method']
            }
        
        return None