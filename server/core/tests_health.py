#server/core/tests_health.py
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


User = get_user_model()


class HealthCheckEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            email='admin-health@example.com',
            password='TestPass123!',
            role='admin',
            is_verified=True,
        )

    def test_public_health_response_is_minimal(self):
        response = self.client.get('/health/')
        self.assertIn(response.status_code, [200, 503])
        self.assertEqual(set(response.data.keys()), {'status'})

    @patch('core.views._check_database_health', return_value=('ok', None))
    @patch('core.views._check_cache_health', return_value=('ok', None))
    @patch('core.views._check_celery_health', return_value=('ok', {'workers': ['w1'], 'active_tasks': 0, 'scheduled_tasks': 0, 'reserved_tasks': 0}))
    @patch('core.views._check_queue_depth_health', return_value=('ok', {'queues': {'celery': 0}, 'threshold': 500}))
    def test_admin_health_response_includes_diagnostics(self, _queue, _celery, _cache, _db):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('status'), 'healthy')
        self.assertIn('diagnostics', response.data)
        self.assertIn('celery', response.data.get('diagnostics', {}))

    @patch('core.views._check_database_health', return_value=('ok', None))
    @patch('core.views._check_cache_health', return_value=('ok', None))
    @patch('core.views._check_celery_health', return_value=('ok', {'workers': ['w1'], 'active_tasks': 150, 'scheduled_tasks': 250, 'reserved_tasks': 150}))
    @patch('core.views._check_queue_depth_health', return_value=('ok', {'queues': {'celery': 0}, 'threshold': 500}))
    def test_admin_health_response_includes_celery_alerts_when_threshold_crossed(self, _queue, _celery, _cache, _db):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        diagnostics = response.data.get('diagnostics', {})
        self.assertIn('alerts', diagnostics)
        alert_kinds = {item.get('kind') for item in diagnostics.get('alerts', [])}
        self.assertIn('celery_active_tasks_high', alert_kinds)
        self.assertIn('celery_scheduled_tasks_high', alert_kinds)
        self.assertIn('celery_reserved_tasks_high', alert_kinds)


    @patch('core.views._check_database_health', return_value=('ok', None))
    @patch('core.views._check_cache_health', return_value=('ok', None))
    @patch('core.views._check_celery_health', return_value=('ok', {'workers': ['w1'], 'active_tasks': 0, 'scheduled_tasks': 0, 'reserved_tasks': 0}))
    @patch('core.views._check_queue_depth_health', return_value=('error', {'queues': {'celery': 900}, 'threshold': 500}))
    def test_admin_health_response_includes_redis_queue_alerts_when_threshold_crossed(self, _queue, _celery, _cache, _db):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        diagnostics = response.data.get('diagnostics', {})
        self.assertIn('queue_depth', diagnostics)
        alert_kinds = {item.get('kind') for item in diagnostics.get('alerts', [])}
        self.assertIn('redis_queue_depth_high', alert_kinds)
