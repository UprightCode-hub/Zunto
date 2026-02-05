# dashboard/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from cart.analytics import get_abandonment_summary_with_scores


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard overview with high-level metrics"""
    template_name = 'dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        time_range = self.request.GET.get('range', 'week')
        
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
        
        context.update({
            'total_abandoned_carts': abandonment_data['total_abandoned'],
            'total_recovered_carts': abandonment_data['total_recovered'],
            'abandonment_rate': f"{abandonment_data['abandonment_rate']}%",
            'recovery_rate': f"{abandonment_data['recovery_rate']}%",
            'avg_abandoned_value': f"₦{abandonment_data['avg_abandoned_value']:,.2f}",
            'avg_composite_score': score_averages.get('composite', 0),
            'sales_labels': json.dumps(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']),
            'sales_data': json.dumps([4200,3800,5200,4600,6800,7200,5900]),
            'category_labels': json.dumps(['Electronics', 'Clothing', 'Home & Garden', 'Sports']),
            'category_data': json.dumps([35,28,20,17]),
            'orders_labels': json.dumps(['Mon','Tue','Wed','Thu','Fri','Sat','Sun']),
            'orders_data': json.dumps([24,21,32,28,42,48,38]),
            'top_products': [
                {'name':'Wireless Headphones','sales':342,'revenue':'$24,650'},
                {'name':'Smart Watch','sales':298,'revenue':'$21,860'},
                {'name':'Laptop Stand','sales':276,'revenue':'$8,280'},
                {'name':'USB-C Cable','sales':234,'revenue':'$4,680'},
                {'name':'Phone Case','sales':189,'revenue':'$3,780'},
            ],
            'current_range': time_range,
        })
        
        return context


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Deep analytics dashboard with user scoring and cart abandonment insights"""
    template_name = 'dashboard/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        abandonment_data = get_abandonment_summary_with_scores()
        scoring_data = abandonment_data.get('scoring', {})
        
        context.update({
            'score_distribution': scoring_data.get('distribution', {}),
            'value_by_tier': abandonment_data.get('value_by_tier', {}),
            'avg_composite_score': scoring_data.get('averages', {}).get('composite', 0),
            'total_abandoned_carts': abandonment_data['total_abandoned'],
            'total_recovered_carts': abandonment_data['total_recovered'],
            'abandonment_rate': f"{abandonment_data['abandonment_rate']}%",
            'recovery_rate': f"{abandonment_data['recovery_rate']}%",
            'avg_abandoned_value': f"₦{abandonment_data['avg_abandoned_value']:,.2f}",
        })
        
        return context


def sales_report(request):
    """Sales report view"""
    context = {
        'page_title': 'Sales Report'
    }
    return render(request, 'dashboard/sales_report.html', context)


def products_list(request):
    """Products listing view"""
    context = {
        'page_title': 'Products',
    }
    return render(request, 'dashboard/products.html', context)


def orders_list(request):
    """Orders listing view"""
    context = {
        'page_title': 'Orders',
    }
    return render(request, 'dashboard/orders.html', context)


def customers_list(request):
    """Customers listing view"""
    context = {
        'page_title': 'Customers',
    }
    return render(request, 'dashboard/customers.html', context)


def analytics(request):
    """Legacy analytics view"""
    context = {
        'page_title': 'Analytics'
    }
    return render(request, 'dashboard/analytics.html', context)