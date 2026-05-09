#server/dashboard/tests.py
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import SellerProfile
from market.models import Category, Product

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
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['dashboard.overview.viewed', 'dashboard.admin.overview.viewed'])

    @patch('dashboard.views.audit_event')
    @patch('dashboard.views.get_abandonment_summary_with_scores')
    def test_dashboard_allows_admin_jwt_without_session_redirect(self, summary_mock, audit_mock):
        summary_mock.return_value = {
            'total_abandoned': 3,
            'total_recovered': 1,
            'abandonment_rate': 33,
            'recovery_rate': 30,
            'avg_abandoned_value': 75,
            'scoring': {'averages': {'composite': 70}},
        }
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        response = self.client.get('/dashboard/?range=week')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('/login/', response.get('Location', ''))
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['dashboard.overview.viewed', 'dashboard.admin.overview.viewed'])

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
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['dashboard.overview.viewed', 'dashboard.admin.overview.viewed'])




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
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['dashboard.company_ops.viewed', 'dashboard.admin.company_ops.viewed'])

    @patch('dashboard.views.audit_event')
    def test_admin_can_suspend_user_from_dashboard(self, audit_mock):
        self.client.login(email='admin-dashboard@example.com', password='pass123')

        response = self.client.patch(
            f'/dashboard/customers/{self.seller_user.id}/admin-update/',
            {'action': 'suspend', 'suspension_reason': 'Policy review'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.seller_user.refresh_from_db()
        self.assertFalse(self.seller_user.is_active)
        self.assertTrue(self.seller_user.is_suspended)
        self.assertEqual(self.seller_user.suspension_reason, 'Policy review')
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertIn('dashboard.admin.user.updated', actions)

    @patch('dashboard.views.audit_event')
    def test_admin_can_approve_seller_application_from_dashboard(self, audit_mock):
        profile = SellerProfile.objects.create(user=self.seller_user, status=SellerProfile.STATUS_PENDING)
        self.client.login(email='admin-dashboard@example.com', password='pass123')

        response = self.client.patch(
            f'/dashboard/sellers/{profile.id}/decision/',
            {'status': 'approved', 'is_verified_seller': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.seller_user.refresh_from_db()
        self.assertEqual(profile.status, SellerProfile.STATUS_APPROVED)
        self.assertTrue(profile.is_verified_seller)
        self.assertTrue(self.seller_user.is_verified_seller)
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertIn('dashboard.admin.seller_application.updated', actions)

    @patch('dashboard.views.audit_event')
    def test_admin_can_moderate_product_from_dashboard(self, audit_mock):
        category = Category.objects.create(name='Dashboard Moderation')
        product = Product.objects.create(
            seller=self.seller_user,
            title='Moderated Product',
            description='Admin dashboard moderation target',
            listing_type='product',
            price='1200.00',
            quantity=1,
            condition='new',
            status='active',
            category=category,
        )
        self.client.login(email='admin-dashboard@example.com', password='pass123')

        response = self.client.patch(
            f'/dashboard/products/{product.id}/admin-update/',
            {'status': 'suspended', 'is_verified': True, 'is_featured': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.status, 'suspended')
        self.assertTrue(product.is_verified)
        self.assertTrue(product.is_verified_product)
        self.assertTrue(product.is_featured)
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertIn('dashboard.admin.product.updated', actions)
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
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['dashboard.sales.viewed', 'dashboard.admin.sales.viewed'])

    @patch('dashboard.views.audit_event')
    def test_analytics_endpoint_emits_paired_audit_events(self, audit_mock):
        self.client.login(email='admin-dashboard-audit@example.com', password='pass123')
        response = self.client.get('/dashboard/analytics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actions = [call.kwargs.get('action') for call in audit_mock.call_args_list]
        self.assertEqual(actions[-2:], ['dashboard.analytics_legacy.viewed', 'dashboard.admin.analytics_legacy.viewed'])
