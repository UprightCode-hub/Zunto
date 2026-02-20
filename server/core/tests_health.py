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
    def test_admin_health_response_includes_diagnostics(self, _celery, _cache, _db):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('status'), 'healthy')
        self.assertIn('diagnostics', response.data)
        self.assertIn('celery', response.data.get('diagnostics', {}))
