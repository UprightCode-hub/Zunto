#server/assistant/tests.py
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
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
                                   
    
    def test_no_match(self):
        """Test query with no good match."""
        result = self.retriever.retrieve("asdf qwerty zxcv")
                                                               


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
        data = {}                                    
        
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
        url = '/assistant/api/admin/logs/'
        
                                     
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
                                  
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
                                   
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    @patch('assistant.views.audit_event')
    def test_admin_logs_endpoint_emits_audit_event(self, audit_mock):
        """Admin logs endpoint should emit an audit event."""
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get('/assistant/api/admin/logs/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'assistant.admin.logs.viewed')

    @patch('assistant.views.audit_event')
    def test_admin_reports_endpoint_emits_audit_event(self, audit_mock):
        """Admin reports endpoint should emit an audit event."""
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get('/assistant/api/admin/reports/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'assistant.admin.reports.viewed')

    @patch('assistant.views.audit_event')
    def test_admin_metrics_endpoint_emits_audit_event(self, audit_mock):
        """Admin metrics endpoint should emit an audit event."""
        self.client.force_authenticate(user=self.staff_user)

        response = self.client.get('/assistant/api/admin/metrics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'assistant.admin.metrics.viewed')



    @patch('assistant.views.audit_event')
    def test_staff_close_report_emits_admin_and_domain_audit_events(self, audit_mock):
        owner = User.objects.create_user(username='report-owner', password='ownerpass123')
        report = Report.objects.create(
            user=owner,
            message='Need review',
            severity='high',
            status='pending',
            meta={},
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.post(f'/assistant/api/report/{report.id}/close/', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(audit_mock.call_count, 2)
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions, ['assistant.report.closed', 'assistant.admin.report.closed'])


    @patch('assistant.views.validate_dispute_media_task.delay', side_effect=Exception('queue-down'))
    @patch('assistant.views.audit_event')
    def test_evidence_upload_rejects_when_validation_queue_unavailable(self, audit_mock, _delay_mock):
        owner = User.objects.create_user(username='dispute-owner', password='ownerpass123')
        report = Report.objects.create(
            user=owner,
            message='Dispute report',
            severity='high',
            status='pending',
            report_type='dispute',
            meta={},
        )
        self.client.force_authenticate(user=owner)
        upload = SimpleUploadedFile('proof.png', b'\x89PNG\r\n\x1a\nabc', content_type='image/png')

        response = self.client.post(
            f'/assistant/api/report/{report.id}/evidence/',
            {'file': upload, 'media_type': 'image'},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        media = report.evidence_files.first()
        self.assertIsNotNone(media)
        self.assertEqual(media.validation_status, 'rejected')
        self.assertIn('queue unavailable', media.validation_reason.lower())
        self.assertTrue(media.is_deleted)
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertIn('assistant.report.evidence_validation_enqueue_failed', actions)
        self.assertIn('assistant.report.evidence_uploaded', actions)

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

