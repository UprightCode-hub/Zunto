from django.shortcuts import render

def analytics_dashboard(request):
    return render(request, "Analytic/Analytics dashboard.html")




# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required
# from django.db.models import Sum, Count, Avg, F
# from datetime import datetime, timedelta
# from market.models import Product, Order, OrderItem
# from accounts.models import User
# from cart.models import Cart, CartAbandonment

# @login_required
# def analytics_view(request):
#     """Analytics dashboard view with comprehensive metrics"""
    
#     # Get date range from request or default to last 7 days
#     date_range = request.GET.get('range', '7')
#     end_date = datetime.now()
    
#     if date_range == '7':
#         start_date = end_date - timedelta(days=7)
#     elif date_range == '30':
#         start_date = end_date - timedelta(days=30)
#     elif date_range == '90':
#         start_date = end_date - timedelta(days=90)
#     else:  # year
#         start_date = end_date - timedelta(days=365)
    
#     # Calculate Key Metrics
#     orders = Order.objects.filter(created_at__gte=start_date)
#     total_orders = orders.count()
#     total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
#     # Conversion Rate (purchases / total sessions)
#     # You'll need to implement session tracking
#     total_sessions = 12450  # Replace with actual session count
#     conversion_rate = (total_orders / total_sessions * 100) if total_sessions > 0 else 0
    
#     # Average Order Value
#     avg_order_value = orders.aggregate(Avg('total_amount'))['total_amount__avg'] or 0
    
#     # Customer Retention (returning customers / total customers)
#     total_customers = User.objects.filter(date_joined__gte=start_date).count()
#     returning_customers = orders.values('user').annotate(
#         order_count=Count('id')
#     ).filter(order_count__gt=1).count()
#     retention_rate = (returning_customers / total_customers * 100) if total_customers > 0 else 0
    
#     # Cart Abandonment Rate
#     total_carts = Cart.objects.filter(created_at__gte=start_date).count()
#     abandoned_carts = CartAbandonment.objects.filter(abandoned_at__gte=start_date).count()
#     abandonment_rate = (abandoned_carts / total_carts * 100) if total_carts > 0 else 0
    
#     # Revenue Trend (last 12 months)
#     revenue_by_month = []
#     for i in range(12, 0, -1):
#         month_start = end_date - timedelta(days=30*i)
#         month_end = end_date - timedelta(days=30*(i-1))
#         month_revenue = Order.objects.filter(
#             created_at__gte=month_start,
#             created_at__lt=month_end
#         ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
#         revenue_by_month.append(int(month_revenue))
    
#     # Traffic Sources (you'll need to implement tracking)
#     traffic_sources = {
#         'organic': 45,
#         'direct': 28,
#         'social': 18,
#         'referral': 9
#     }
    
#     # Customer Acquisition (weekly data)
#     new_customers_weekly = []
#     returning_customers_weekly = []
#     for i in range(4, 0, -1):
#         week_start = end_date - timedelta(weeks=i)
#         week_end = end_date - timedelta(weeks=i-1)
        
#         new = User.objects.filter(
#             date_joined__gte=week_start,
#             date_joined__lt=week_end
#         ).count()
#         new_customers_weekly.append(new)
        
#         # Returning customers who made orders this week
#         returning = orders.filter(
#             created_at__gte=week_start,
#             created_at__lt=week_end
#         ).values('user').annotate(
#             user_order_count=Count('id')
#         ).filter(user_order_count__gt=1).count()
#         returning_customers_weekly.append(returning)
    
#     # Product Performance Scores (0-100)
#     product_performance = {
#         'sales': 85,
#         'reviews': 72,
#         'returns': 35,
#         'margins': 68,
#         'views': 90,
#         'conversions': 78
#     }
    
#     # Sales Funnel Data
#     funnel_data = {
#         'visitors': 12450,
#         'product_views': 8240,
#         'add_to_cart': 2890,
#         'checkout': 1650,
#         'purchase': 945
#     }
    
#     # Top Performing Channels
#     top_channels = [
#         {
#             'name': 'Email Marketing',
#             'conversions': 3250,
#             'revenue': 89500,
#             'change': 12.5
#         },
#         {
#             'name': 'Google Ads',
#             'conversions': 2890,
#             'revenue': 76200,
#             'change': 8.3
#         },
#         {
#             'name': 'Social Media',
#             'conversions': 2145,
#             'revenue': 54800,
#             'change': 15.7
#         },
#         {
#             'name': 'Affiliate Partners',
#             'conversions': 1680,
#             'revenue': 42100,
#             'change': -2.4
#         }
#     ]
    
#     # Geographic Performance
#     geo_performance = [
#         {
#             'country': '🇺🇸 United States',
#             'sessions': 4250,
#             'conversion_rate': 3.8,
#             'revenue': 124500,
#             'change': 12.3
#         },
#         {
#             'country': '🇬🇧 United Kingdom',
#             'sessions': 2840,
#             'conversion_rate': 3.2,
#             'revenue': 76200,
#             'change': 8.7
#         },
#         {
#             'country': '🇨🇦 Canada',
#             'sessions': 1920,
#             'conversion_rate': 2.9,
#             'revenue': 54800,
#             'change': 5.2
#         },
#         {
#             'country': '🇦🇺 Australia',
#             'sessions': 1560,
#             'conversion_rate': 3.5,
#             'revenue': 48900,
#             'change': 9.1
#         },
#         {
#             'country': '🇩🇪 Germany',
#             'sessions': 1340,
#             'conversion_rate': 2.7,
#             'revenue': 38200,
#             'change': -1.8
#         }
#     ]
    
#     context = {
#         # Key Metrics
#         'conversion_rate': round(conversion_rate, 2),
#         'avg_order_value': round(avg_order_value, 2),
#         'retention_rate': round(retention_rate, 1),
#         'abandonment_rate': round(abandonment_rate, 1),
        
#         # Chart Data
#         'revenue_trend': revenue_by_month,
#         'traffic_sources': traffic_sources,
#         'new_customers_weekly': new_customers_weekly,
#         'returning_customers_weekly': returning_customers_weekly,
#         'product_performance': product_performance,
        
#         # Lists
#         'funnel_data': funnel_data,
#         'top_channels': top_channels,
#         'geo_performance': geo_performance,
        
#         # Date range
#         'selected_range': date_range,
#         'start_date': start_date,
#         'end_date': end_date,
#     }
    
#     return render(request, 'dashboard/analytics.html', context)