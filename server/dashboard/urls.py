from django.urls import path
from .views import (
    DashboardView,
    AnalyticsDashboardView,
    sales_report,
    products_list,
    orders_list,
    customers_list,
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('analytics/', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    path('sales/', sales_report, name='sales_report'),
    path('products/', products_list, name='products_list'),
    path('orders/', orders_list, name='orders_list'),
    path('customers/', customers_list, name='customers_list'),
]