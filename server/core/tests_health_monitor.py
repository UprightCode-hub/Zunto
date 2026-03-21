#server/core/tests_health_monitor.py
from unittest.mock import patch

from django.test import TestCase

from core.health_monitor import evaluate_health_snapshot


class HealthMonitorSnapshotTests(TestCase):
    @patch('core.health_monitor._check_database_health', return_value=('ok', None))
    @patch('core.health_monitor._check_cache_health', return_value=('ok', None))
    @patch('core.health_monitor._check_celery_health', return_value=('ok', {'workers': ['w1'], 'active_tasks': 0, 'scheduled_tasks': 0, 'reserved_tasks': 0}))
    @patch('core.health_monitor._check_queue_depth_health', return_value=('ok', {'queues': {'celery': 0}, 'threshold': 500}))
    @patch('core.health_monitor._celery_alerts_from_details', return_value=[])
    def test_snapshot_healthy_without_alerts(self, *_mocks):
        snapshot = evaluate_health_snapshot()
        self.assertEqual(snapshot['status'], 'healthy')
        self.assertEqual(snapshot['diagnostics']['alerts'], [])

    @patch('core.health_monitor._check_database_health', return_value=('ok', None))
    @patch('core.health_monitor._check_cache_health', return_value=('ok', None))
    @patch('core.health_monitor._check_celery_health', return_value=('ok', {'workers': ['w1'], 'active_tasks': 150, 'scheduled_tasks': 0, 'reserved_tasks': 0}))
    @patch('core.health_monitor._check_queue_depth_health', return_value=('error', {'queues': {'celery': 900}, 'threshold': 500}))
    @patch('core.health_monitor._celery_alerts_from_details', return_value=[{'kind': 'celery_active_tasks_high'}])
    def test_snapshot_includes_celery_and_queue_alerts(self, *_mocks):
        snapshot = evaluate_health_snapshot()
        self.assertEqual(snapshot['status'], 'unhealthy')
        kinds = {a.get('kind') for a in snapshot['diagnostics']['alerts']}
        self.assertIn('celery_active_tasks_high', kinds)
        self.assertIn('redis_queue_depth_high', kinds)
