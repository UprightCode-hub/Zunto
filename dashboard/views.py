from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin


# Import your models - adjust these imports based on your actual models
# from .models import Order, Product, Customer, OrderItem


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Time range
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

        # Sample stats
        context.update({
            'total_revenue': '$45,280',
            'total_orders': '1,284',
            'total_customers': '892',
            'total_products': '324',
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
    """
    Detailed sales report view
    """
    # Add your sales report logic here
    context = {
        'page_title': 'Sales Report'
    }
    return render(request, 'dashboard/sales_report.html', context)



def products_list(request):
    """
    Products management view
    """
    # products = Product.objects.all().order_by('-created_at')
    
    context = {
        'page_title': 'Products',
        # 'products': products
    }
    return render(request, 'dashboard/products.html', context)



def orders_list(request):
    """
    Orders management view
    """
    # orders = Order.objects.all().order_by('-created_at')
    
    context = {
        'page_title': 'Orders',
        # 'orders': orders
    }
    return render(request, 'dashboard/orders.html', context)



def customers_list(request):
    """
    Customers management view
    """
    # customers = Customer.objects.all().order_by('-date_joined')
    
    context = {
        'page_title': 'Customers',
        # 'customers': customers
    }
    return render(request, 'dashboard/customers.html', context)



def analytics(request):
    """
    Advanced analytics view
    """
    context = {
        'page_title': 'Analytics'
    }
    return render(request, 'dashboard/analytics.html', context)