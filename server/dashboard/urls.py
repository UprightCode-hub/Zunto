from django.urls import path
from .views import (
    DashboardAPI,
    AnalyticsDashboardAPI,
    sales_report_api,
    products_list_api,
    orders_list_api,
    customers_list_api,
)

urlpatterns = [
    path('', DashboardAPI.as_view(), name='dashboard'),
    path('analytics/', AnalyticsDashboardAPI.as_view(), name='analytics_dashboard'),
    path('sales/', sales_report_api, name='sales_report'),
    path('products/', products_list_api, name='products_list'),
    path('orders/', orders_list_api, name='orders_list'),
    path('customers/', customers_list_api, name='customers_list'),
]