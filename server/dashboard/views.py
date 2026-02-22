#server/dashboard/views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from cart.analytics import get_abandonment_summary_with_scores
from core.audit import audit_event
from market.models import ProductReport, ProductVideo
from orders.models import Refund
from reviews.models import ReviewFlag


def _is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, 'is_staff', False) or getattr(user, 'role', None) == 'admin')


def _admin_forbidden_response():
    return JsonResponse({'detail': 'Admin access required.'}, status=403)


class AdminDashboardAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not _is_admin_user(request.user):
            return _admin_forbidden_response()
        return super().dispatch(request, *args, **kwargs)


class DashboardAPI(AdminDashboardAccessMixin, View):
    """API for main dashboard overview."""

    def get(self, request, *args, **kwargs):
        time_range = request.GET.get('range', 'week')
        today = timezone.now()

        if time_range == 'day':
            start_date = today - timedelta(days=1)
        elif time_range == 'week':
            start_date = today - timedelta(days=7)
        elif time_range == 'month':
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=365)

        abandonment_data = get_abandonment_summary_with_scores()
        scoring_data = abandonment_data.get('scoring', {})
        score_averages = scoring_data.get('averages', {})

        data = {
            'total_abandoned_carts': abandonment_data['total_abandoned'],
            'total_recovered_carts': abandonment_data['total_recovered'],
            'abandonment_rate': abandonment_data['abandonment_rate'],
            'recovery_rate': abandonment_data['recovery_rate'],
            'avg_abandoned_value': abandonment_data['avg_abandoned_value'],
            'avg_composite_score': score_averages.get('composite', 0),
            'sales': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'data': [4200, 3800, 5200, 4600, 6800, 7200, 5900],
            },
            'categories': {
                'labels': ['Electronics', 'Clothing', 'Home & Garden', 'Sports'],
                'data': [35, 28, 20, 17],
            },
            'orders': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'data': [24, 21, 32, 28, 42, 48, 38],
            },
            'top_products': [
                {'name': 'Wireless Headphones', 'sales': 342, 'revenue': 24650},
                {'name': 'Smart Watch', 'sales': 298, 'revenue': 21860},
                {'name': 'Laptop Stand', 'sales': 276, 'revenue': 8280},
                {'name': 'USB-C Cable', 'sales': 234, 'revenue': 4680},
                {'name': 'Phone Case', 'sales': 189, 'revenue': 3780},
            ],
            'current_range': time_range,
            'range_start': start_date.isoformat(),
            'range_end': today.isoformat(),
        }

        audit_event(request, action='dashboard.admin.overview.viewed', extra={'range': time_range})
        return JsonResponse(data)


class AnalyticsDashboardAPI(AdminDashboardAccessMixin, View):
    """API for analytics dashboard."""

    def get(self, request, *args, **kwargs):
        abandonment_data = get_abandonment_summary_with_scores()
        scoring_data = abandonment_data.get('scoring', {})

        data = {
            'score_distribution': scoring_data.get('distribution', {}),
            'value_by_tier': abandonment_data.get('value_by_tier', {}),
            'avg_composite_score': scoring_data.get('averages', {}).get('composite', 0),
            'total_abandoned_carts': abandonment_data['total_abandoned'],
            'total_recovered_carts': abandonment_data['total_recovered'],
            'abandonment_rate': abandonment_data['abandonment_rate'],
            'recovery_rate': abandonment_data['recovery_rate'],
            'avg_abandoned_value': abandonment_data['avg_abandoned_value'],
        }

        audit_event(request, action='dashboard.admin.analytics.viewed')
        return JsonResponse(data)


@login_required
def sales_report_api(request):
    """API endpoint for sales report."""
    if not _is_admin_user(request.user):
        return _admin_forbidden_response()

    audit_event(request, action='dashboard.admin.sales.viewed')
    return JsonResponse({'page_title': 'Sales Report'})


@login_required
def products_list_api(request):
    """API endpoint for products list."""
    if not _is_admin_user(request.user):
        return _admin_forbidden_response()

    audit_event(request, action='dashboard.admin.products.viewed')
    return JsonResponse({'page_title': 'Products'})


@login_required
def orders_list_api(request):
    """API endpoint for orders list."""
    if not _is_admin_user(request.user):
        return _admin_forbidden_response()

    audit_event(request, action='dashboard.admin.orders.viewed')
    return JsonResponse({'page_title': 'Orders'})


@login_required
def customers_list_api(request):
    """API endpoint for customers list."""
    if not _is_admin_user(request.user):
        return _admin_forbidden_response()

    audit_event(request, action='dashboard.admin.customers.viewed')
    return JsonResponse({'page_title': 'Customers'})


@login_required
def analytics_api(request):
    """API endpoint for legacy analytics."""
    if not _is_admin_user(request.user):
        return _admin_forbidden_response()

    audit_event(request, action='dashboard.admin.analytics_legacy.viewed')
    return JsonResponse({'page_title': 'Analytics'})


@login_required
def company_admin_operations_api(request):
    """Company-admin operational queue summary (frontend ops center)."""
    if not _is_admin_user(request.user):
        return _admin_forbidden_response()

    payload = {
        'product_reports': {
            'pending': ProductReport.objects.filter(status='pending').count(),
            'reviewing': ProductReport.objects.filter(status='reviewing').count(),
        },
        'review_flags': {
            'pending': ReviewFlag.objects.filter(status='pending').count(),
            'reviewing': ReviewFlag.objects.filter(status='reviewing').count(),
        },
        'refunds': {
            'pending': Refund.objects.filter(status='pending').count(),
            'processing': Refund.objects.filter(status='processing').count(),
        },
        'product_videos': {
            'pending_scan': ProductVideo.objects.filter(security_scan_status=ProductVideo.SCAN_PENDING).count(),
            'quarantined': ProductVideo.objects.filter(security_scan_status=ProductVideo.SCAN_QUARANTINED).count(),
        },
    }

    audit_event(request, action='dashboard.admin.company_ops.viewed', extra={'queues': payload})
    return JsonResponse(payload)
