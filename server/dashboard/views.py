# dashboard/views.py (COMPLETE FILE)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from cart.analytics import get_abandonment_summary


class DashboardView(LoginRequiredMixin, TemplateView):
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
        
        abandonment_data = get_abandonment_summary()
        
        context.update({
            'total_abandoned_carts': abandonment_data['total_abandoned'],
            'total_recovered_carts': abandonment_data['total_recovered'],
            'abandonment_rate': f"{abandonment_data['abandonment_rate']}%",
            'recovery_rate': f"{abandonment_data['recovery_rate']}%",
            'avg_abandoned_value': f"₦{abandonment_data['avg_abandoned_value']:,.2f}",
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


def sales_report(request):
    context = {
        'page_title': 'Sales Report'
    }
    return render(request, 'dashboard/sales_report.html', context)


def products_list(request):
    context = {
        'page_title': 'Products',
    }
    return render(request, 'dashboard/products.html', context)


def orders_list(request):
    context = {
        'page_title': 'Orders',
    }
    return render(request, 'dashboard/orders.html', context)


def customers_list(request):
    context = {
        'page_title': 'Customers',
    }
    return render(request, 'dashboard/customers.html', context)


def analytics(request):
    context = {
        'page_title': 'Analytics'
    }
    return render(request, 'dashboard/analytics.html', context)