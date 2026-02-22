from unittest.mock import patch

from django.test import TestCase, override_settings

from core.tasks import monitor_system_health_alerts


class HealthAlertRoutingTaskTests(TestCase):
    @override_settings(
        HEALTH_ALERT_NOTIFY_EMAIL_ENABLED=True,
        HEALTH_ALERT_RECIPIENTS=['ops@example.com'],
        HEALTH_ALERT_NOTIFY_EMAIL_COOLDOWN_SECONDS=600,
    )
    @patch('core.tasks.cache')
    @patch('core.tasks.send_mail')
    @patch('core.tasks.evaluate_health_snapshot')
    def test_unhealthy_snapshot_sends_email_alert(self, snapshot_mock, send_mail_mock, cache_mock):
        snapshot_mock.return_value = {
            'status': 'unhealthy',
            'database': 'ok',
            'cache': 'ok',
            'celery': 'error',
            'queue_depth': 'ok',
            'diagnostics': {
                'alerts': [{'kind': 'celery_active_tasks_high'}],
            },
        }
        cache_mock.get.return_value = None

        result = monitor_system_health_alerts()

        self.assertEqual(result['status'], 'unhealthy')
        self.assertEqual(result['alert_count'], 1)
        self.assertTrue(result['email']['sent'])
        send_mail_mock.assert_called_once()
        cache_mock.set.assert_called_once()

    @override_settings(
        HEALTH_ALERT_NOTIFY_EMAIL_ENABLED=True,
        HEALTH_ALERT_RECIPIENTS=['ops@example.com'],
        HEALTH_ALERT_NOTIFY_EMAIL_COOLDOWN_SECONDS=600,
    )
    @patch('core.tasks.cache')
    @patch('core.tasks.send_mail')
    @patch('core.tasks.evaluate_health_snapshot')
    def test_alert_email_respects_cooldown(self, snapshot_mock, send_mail_mock, cache_mock):
        snapshot_mock.return_value = {
            'status': 'unhealthy',
            'database': 'ok',
            'cache': 'ok',
            'celery': 'error',
            'queue_depth': 'ok',
            'diagnostics': {
                'alerts': [{'kind': 'celery_active_tasks_high'}],
            },
        }
        cache_mock.get.return_value = True

        result = monitor_system_health_alerts()

        self.assertEqual(result['email']['reason'], 'cooldown_active')
        send_mail_mock.assert_not_called()

    @override_settings(HEALTH_ALERT_NOTIFY_EMAIL_ENABLED=False)
    @patch('core.tasks.send_mail')
    @patch('core.tasks.evaluate_health_snapshot')
    def test_healthy_snapshot_skips_email(self, snapshot_mock, send_mail_mock):
        snapshot_mock.return_value = {
            'status': 'healthy',
            'database': 'ok',
            'cache': 'ok',
            'celery': 'ok',
            'queue_depth': 'ok',
            'diagnostics': {
                'alerts': [],
            },
        }

        result = monitor_system_health_alerts()

        self.assertEqual(result['status'], 'healthy')
        self.assertEqual(result['alert_count'], 0)
        self.assertEqual(result['email']['reason'], 'healthy')
        send_mail_mock.assert_not_called()


    @override_settings(
        HEALTH_ALERT_NOTIFY_WEBHOOK_ENABLED=True,
        HEALTH_ALERT_WEBHOOK_URL='https://example.com/hooks/health',
        HEALTH_ALERT_NOTIFY_WEBHOOK_COOLDOWN_SECONDS=180,
    )
    @patch('core.tasks.cache')
    @patch('core.tasks.requests.post')
    @patch('core.tasks.evaluate_health_snapshot')
    def test_unhealthy_snapshot_sends_webhook_alert(self, snapshot_mock, webhook_post_mock, cache_mock):
        snapshot_mock.return_value = {
            'status': 'unhealthy',
            'database': 'ok',
            'cache': 'ok',
            'celery': 'error',
            'queue_depth': 'ok',
            'diagnostics': {
                'alerts': [{'kind': 'celery_active_tasks_high'}],
            },
        }
        cache_mock.get.return_value = None

        result = monitor_system_health_alerts()

        self.assertEqual(result['status'], 'unhealthy')
        self.assertTrue(result['webhook']['sent'])
        webhook_post_mock.assert_called_once()

    @override_settings(
        HEALTH_ALERT_NOTIFY_WEBHOOK_ENABLED=True,
        HEALTH_ALERT_WEBHOOK_URL='https://example.com/hooks/health',
        HEALTH_ALERT_NOTIFY_WEBHOOK_COOLDOWN_SECONDS=180,
    )
    @patch('core.tasks.cache')
    @patch('core.tasks.requests.post')
    @patch('core.tasks.evaluate_health_snapshot')
    def test_webhook_alert_respects_cooldown(self, snapshot_mock, webhook_post_mock, cache_mock):
        snapshot_mock.return_value = {
            'status': 'unhealthy',
            'database': 'ok',
            'cache': 'ok',
            'celery': 'error',
            'queue_depth': 'ok',
            'diagnostics': {
                'alerts': [{'kind': 'celery_active_tasks_high'}],
            },
        }
        cache_mock.get.return_value = True

        result = monitor_system_health_alerts()

        self.assertEqual(result['webhook']['reason'], 'cooldown_active')
        webhook_post_mock.assert_not_called()


    @override_settings(
        HEALTH_ALERT_NOTIFY_EMAIL_ENABLED=True,
        HEALTH_ALERT_RECIPIENTS=['ops@example.com'],
    )
    @patch('core.tasks.send_mail', side_effect=RuntimeError('smtp down'))
    @patch('core.tasks.evaluate_health_snapshot')
    def test_email_delivery_failure_returns_nonfatal_result(self, snapshot_mock, _send_mail_mock):
        snapshot_mock.return_value = {
            'status': 'unhealthy',
            'database': 'ok',
            'cache': 'ok',
            'celery': 'error',
            'queue_depth': 'ok',
            'diagnostics': {'alerts': [{'kind': 'celery_active_tasks_high'}]},
        }

        result = monitor_system_health_alerts()

        self.assertEqual(result['status'], 'unhealthy')
        self.assertFalse(result['email']['sent'])
        self.assertEqual(result['email']['reason'], 'delivery_failed')

    @override_settings(
        HEALTH_ALERT_NOTIFY_WEBHOOK_ENABLED=True,
        HEALTH_ALERT_WEBHOOK_URL='https://example.com/hooks/health',
    )
    @patch('core.tasks.requests.post')
    @patch('core.tasks.evaluate_health_snapshot')
    def test_webhook_delivery_failure_returns_nonfatal_result(self, snapshot_mock, webhook_post_mock):
        import requests

        snapshot_mock.return_value = {
            'status': 'unhealthy',
            'database': 'ok',
            'cache': 'ok',
            'celery': 'error',
            'queue_depth': 'ok',
            'diagnostics': {'alerts': [{'kind': 'celery_active_tasks_high'}]},
        }
        webhook_post_mock.side_effect = requests.RequestException('connection failed')

        result = monitor_system_health_alerts()

        self.assertEqual(result['status'], 'unhealthy')
        self.assertFalse(result['webhook']['sent'])
        self.assertEqual(result['webhook']['reason'], 'delivery_failed')
