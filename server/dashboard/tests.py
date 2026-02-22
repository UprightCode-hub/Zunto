#server/dashboard/tests.py
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class DashboardAccessTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email='admin-dashboard@example.com',
            password='pass123',
            first_name='Admin',
            last_name='User',
            is_staff=True,
            role='admin',
        )
        self.staff_user = User.objects.create_user(
            email='staff-dashboard@example.com',
            password='pass123',
            first_name='Staff',
            last_name='User',
            is_staff=True,
            role='seller',
        )
        self.seller_user = User.objects.create_user(
            email='seller-dashboard@example.com',
            password='pass123',
            first_name='Seller',
            last_name='User',
            role='seller',
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_dashboard_rejects_non_admin_user(self):
        self.client.login(email='seller-dashboard@example.com', password='pass123')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('dashboard.views.audit_event')
    @patch('dashboard.views.get_abandonment_summary_with_scores')
    def test_dashboard_allows_admin_and_emits_audit(self, summary_mock, audit_mock):
        summary_mock.return_value = {
            'total_abandoned': 5,
            'total_recovered': 2,
            'abandonment_rate': 50,
            'recovery_rate': 40,
            'avg_abandoned_value': 100,
            'scoring': {'averages': {'composite': 75}},
        }
        self.client.login(email='admin-dashboard@example.com', password='pass123')

        response = self.client.get('/dashboard/?range=week')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('range_start', response.json())
        self.assertIn('range_end', response.json())
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'dashboard.admin.overview.viewed')

    @patch('dashboard.views.audit_event')
    @patch('dashboard.views.get_abandonment_summary_with_scores')
    def test_staff_user_allowed_and_emits_audit(self, summary_mock, audit_mock):
        summary_mock.return_value = {
            'total_abandoned': 1,
            'total_recovered': 1,
            'abandonment_rate': 10,
            'recovery_rate': 90,
            'avg_abandoned_value': 50,
            'scoring': {'averages': {'composite': 80}},
        }
        self.client.login(email='staff-dashboard@example.com', password='pass123')

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        audit_mock.assert_called_once()
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'dashboard.admin.overview.viewed')




    @patch('dashboard.views.audit_event')
    def test_company_ops_endpoint_requires_admin(self, audit_mock):
        self.client.login(email='seller-dashboard@example.com', password='pass123')

        response = self.client.get('/dashboard/company-ops/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        audit_mock.assert_not_called()

    @patch('dashboard.views.audit_event')
    def test_company_ops_endpoint_returns_queue_summary(self, audit_mock):
        self.client.login(email='admin-dashboard@example.com', password='pass123')

        response = self.client.get('/dashboard/company-ops/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('product_reports', response.json())
        self.assertIn('refunds', response.json())
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'dashboard.admin.company_ops.viewed')
class DashboardEndpointAuditTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email='admin-dashboard-audit@example.com',
            password='pass123',
            first_name='Admin',
            last_name='Audit',
            is_staff=True,
            role='admin',
        )

    @patch('dashboard.views.audit_event')
    def test_sales_endpoint_emits_audit(self, audit_mock):
        self.client.login(email='admin-dashboard-audit@example.com', password='pass123')
        response = self.client.get('/dashboard/sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(audit_mock.call_args.kwargs['action'], 'dashboard.admin.sales.viewed')
