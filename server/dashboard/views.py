# dashboard/views.py

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import timedelta
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from cart.analytics import get_abandonment_summary_with_scores


@method_decorator(login_required, name='dispatch')
class DashboardAPI(View):
    """API for main dashboard overview"""

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
                'labels': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
                'data': [4200,3800,5200,4600,6800,7200,5900]
            },
            'categories': {
                'labels': ['Electronics', 'Clothing', 'Home & Garden', 'Sports'],
                'data': [35,28,20,17]
            },
            'orders': {
                'labels': ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
                'data': [24,21,32,28,42,48,38]
            },
            'top_products': [
                {'name':'Wireless Headphones','sales':342,'revenue':24650},
                {'name':'Smart Watch','sales':298,'revenue':21860},
                {'name':'Laptop Stand','sales':276,'revenue':8280},
                {'name':'USB-C Cable','sales':234,'revenue':4680},
                {'name':'Phone Case','sales':189,'revenue':3780},
            ],
            'current_range': time_range
        }

        return JsonResponse(data)


@method_decorator(login_required, name='dispatch')
class AnalyticsDashboardAPI(View):
    """API for analytics dashboard"""

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

        return JsonResponse(data)


@login_required
def sales_report_api(request):
    """API endpoint for sales report"""
    data = {
        'page_title': 'Sales Report',
        # Add your actual report data here
    }
    return JsonResponse(data)


@login_required
def products_list_api(request):
    """API endpoint for products list"""
    data = {
        'page_title': 'Products',
        # Add products data here
    }
    return JsonResponse(data)


@login_required
def orders_list_api(request):
    """API endpoint for orders list"""
    data = {
        'page_title': 'Orders',
        # Add orders data here
    }
    return JsonResponse(data)


@login_required
def customers_list_api(request):
    """API endpoint for customers list"""
    data = {
        'page_title': 'Customers',
        # Add customers data here
    }
    return JsonResponse(data)


@login_required
def analytics_api(request):
    """API endpoint for legacy analytics"""
    data = {
        'page_title': 'Analytics',
        # Add analytics data here
    }
    return JsonResponse(data)
