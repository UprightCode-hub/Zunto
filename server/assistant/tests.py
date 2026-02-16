from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Report, ConversationLog
from .processors.faq_retriever import FAQRetriever
from .processors.rule_engine import RuleEngine
from .processors.query_processor import QueryProcessor

User = get_user_model()


class FAQRetrieverTests(TestCase):
    """Test FAQ retrieval functionality."""
    
    def setUp(self):
        self.retriever = FAQRetriever.get_instance()
    
    def test_keyword_match(self):
        """Test keyword-based FAQ matching."""
        result = self.retriever.retrieve("How do I track my order?")
        self.assertIsNotNone(result)
        self.assertIn('track', result['answer'].lower())
    
    def test_tfidf_match(self):
        """Test TF-IDF based matching."""
        result = self.retriever.retrieve("Where can I see my shipment status?")
        self.assertIsNotNone(result)
        # Should match tracking FAQ
    
    def test_no_match(self):
        """Test query with no good match."""
        result = self.retriever.retrieve("asdf qwerty zxcv")
        # May or may not return a result depending on threshold


class RuleEngineTests(TestCase):
    """Test rule matching functionality."""
    
    def setUp(self):
        self.engine = RuleEngine.get_instance()
    
    def test_high_severity_fraud(self):
        """Test fraud detection."""
        result = self.engine.evaluate("This seller is scamming me!")
        self.assertIsNotNone(result)
        self.assertEqual(result['severity'], 'high')
        self.assertEqual(result['id'], 'fraud_report')
    
    def test_threat_detection(self):
        """Test threat detection."""
        result = self.engine.evaluate("I'm going to hurt you")
        self.assertIsNotNone(result)
        self.assertEqual(result['severity'], 'critical')
    
    def test_medium_severity(self):
        """Test medium severity rule."""
        result = self.engine.evaluate("My package hasn't arrived yet")
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'not_delivered')
        self.assertEqual(result['severity'], 'medium')
    
    def test_no_rule_match(self):
        """Test message that doesn't match any rule."""
        result = self.engine.evaluate("What's your phone number?")
        self.assertIsNone(result)


class QueryProcessorTests(TestCase):
    """Test main query processing logic."""
    
    def setUp(self):
        self.processor = QueryProcessor()
    
    def test_high_severity_rule_prioritization(self):
        """High-severity rules should always take priority."""
        result = self.processor.process("Seller is scamming me with fake products")
        self.assertIsNotNone(result['rule'])
        self.assertEqual(result['rule']['severity'], 'high')
        self.assertEqual(result['confidence'], 1.0)
        self.assertIn('escalate', result['explanation'].lower())
    
    def test_faq_response(self):
        """FAQ match should be used when no high-priority rule."""
        result = self.processor.process("How do I track my order?")
        self.assertIsNotNone(result['faq'])
        self.assertIn('track', result['reply'].lower())
        self.assertGreater(result['confidence'], 0.5)
    
    def test_fallback_response(self):
        """Should provide fallback when nothing matches."""
        result = self.processor.process("Random unrelated query xyz123")
        self.assertIsNotNone(result['reply'])
        self.assertLess(result['confidence'], 0.7)


class APIEndpointTests(APITestCase):
    """Test REST API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True
        )
    
    def test_ask_endpoint(self):
        """Test main ask endpoint."""
        url = '/assistant/api/ask/'
        data = {'message': 'How do I track my order?'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('reply', response.data)
        self.assertIn('confidence', response.data)
        self.assertIn('explanation', response.data)
    
    def test_ask_endpoint_validation(self):
        """Test input validation."""
        url = '/assistant/api/ask/'
        data = {}  # Missing required 'message' field
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_report_endpoint(self):
        """Test report creation."""
        url = '/assistant/api/report/'
        data = {
            'message': 'Seller is harassing me',
            'severity': 'high'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.count(), 1)
    
    def test_admin_endpoints_require_staff(self):
        """Admin endpoints should require staff permission."""
        url = '/assistant/api/admin/recent-logs/'
        
        # Unauthenticated should fail
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Regular user should fail
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Staff user should succeed
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ModelTests(TestCase):
    """Test database models."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_report_creation(self):
        """Test creating a report."""
        report = Report.objects.create(
            user=self.user,
            message="Test report",
            severity='high',
            status='pending',
            meta={'test': 'data'}
        )
        self.assertEqual(report.user, self.user)
        self.assertEqual(report.severity, 'high')
        self.assertEqual(report.meta['test'], 'data')
    
    def test_conversation_log_creation(self):
        """Test creating a conversation log."""
        log = ConversationLog.objects.create(
            user=self.user,
            message="How do I track my order?",
            final_reply="You can track in My Orders section",
            confidence=0.85,
            explanation="FAQ match"
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.confidence, 0.85)
        self.assertIsNotNone(log.created_at)



class EvidenceAuthorizationTests(APITestCase):
    """Authorization checks for dispute evidence endpoints."""

    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='ownerpass123')
        self.other_user = User.objects.create_user(username='other', password='otherpass123')

    def test_upload_rejects_ownerless_report_for_non_staff(self):
        report = Report.objects.create(
            user=None,
            message='Anonymous dispute',
            report_type='dispute',
            status='pending'
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(f'/assistant/api/report/{report.id}/evidence/', {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_rejects_ownerless_report_for_non_staff(self):
        report = Report.objects.create(
            user=None,
            message='Anonymous dispute',
            report_type='dispute',
            status='pending'
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.get(f'/assistant/api/report/{report.id}/evidence/list/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_allows_report_owner(self):
        report = Report.objects.create(
            user=self.owner,
            message='Owned dispute',
            report_type='dispute',
            status='pending'
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(f'/assistant/api/report/{report.id}/evidence/', {}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file is required', str(response.data.get('error', '')))
