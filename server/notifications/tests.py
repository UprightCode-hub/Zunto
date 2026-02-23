#server/notifications/tests.py
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import EmailLog, EmailTemplate

User = get_user_model()


class NotificationAdminAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='notifications-admin@example.com',
            password='TestPass123!',
            role='admin',
            is_staff=True,
            is_verified=True,
        )
        self.user = User.objects.create_user(
            email='notifications-user@example.com',
            password='TestPass123!',
            role='buyer',
            is_verified=True,
        )
        self.template = EmailTemplate.objects.create(
            name='Welcome',
            template_type='welcome',
            subject='Welcome subject',
            html_content='<p>Hello</p>',
            text_content='Hello',
            is_active=True,
        )
        EmailLog.objects.create(
            template=self.template,
            recipient_email='recipient@example.com',
            recipient_name='Recipient',
            subject='Email 1',
            status='sent',
        )

    @patch('notifications.views.audit_event')
    def test_admin_templates_list_emits_audit_event(self, audit_mock):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/notifications/templates/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['notifications.email_templates.viewed', 'notifications.admin.email_templates.viewed'])

    @patch('notifications.views.audit_event')
    def test_admin_statistics_emits_audit_event(self, audit_mock):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/notifications/statistics/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['notifications.email_statistics.viewed', 'notifications.admin.email_statistics.viewed'])

    def test_non_admin_cannot_access_admin_notification_endpoints(self):
        self.client.force_authenticate(user=self.user)

        templates_response = self.client.get('/api/notifications/templates/')
        stats_response = self.client.get('/api/notifications/statistics/')

        self.assertEqual(templates_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(stats_response.status_code, status.HTTP_403_FORBIDDEN)
