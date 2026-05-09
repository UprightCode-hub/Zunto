#server/dashboard/urls.py
from django.urls import path
from .views import (
    DashboardAPI,
    AnalyticsDashboardAPI,
    sales_report_api,
    products_list_api,
    orders_list_api,
    customers_list_api,
    user_admin_update_api,
    seller_applications_api,
    seller_application_decision_api,
    product_admin_update_api,
    company_admin_operations_api,
)

urlpatterns = [
    path('', DashboardAPI.as_view(), name='dashboard'),
    path('analytics/', AnalyticsDashboardAPI.as_view(), name='analytics_dashboard'),
    path('sales/', sales_report_api, name='sales_report'),
    path('products/', products_list_api, name='products_list'),
    path('products/<uuid:product_id>/admin-update/', product_admin_update_api, name='product_admin_update'),
    path('orders/', orders_list_api, name='orders_list'),
    path('customers/', customers_list_api, name='customers_list'),
    path('customers/<uuid:user_id>/admin-update/', user_admin_update_api, name='user_admin_update'),
    path('sellers/', seller_applications_api, name='seller_applications'),
    path('sellers/<uuid:profile_id>/decision/', seller_application_decision_api, name='seller_application_decision'),
    path('company-ops/', company_admin_operations_api, name='company_admin_operations'),
]
