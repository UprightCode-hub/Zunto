# orders/urls.py
from django.urls import path
from .views import (
    CheckoutView,
    MyOrdersView,
    OrderDetailView,
    CancelOrderView,
    SellerOrdersView,
    SellerOrderDetailView,
    UpdateOrderItemStatusView,
    ShippingAddressListCreateView,
    ShippingAddressDetailView,
    SetDefaultAddressView,
    RequestRefundView,
    MyRefundsView,
    order_statistics,
    seller_statistics,
    verify_payment,
    reorder,
)

app_name = 'orders'

urlpatterns = [
    # Checkout
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    
    # Customer Orders
    path('my-orders/', MyOrdersView.as_view(), name='my_orders'),
    path('orders/<str:order_number>/', OrderDetailView.as_view(), name='order_detail'),
    path('orders/<str:order_number>/cancel/', CancelOrderView.as_view(), name='cancel_order'),
    path('orders/<str:order_number>/verify-payment/', verify_payment, name='verify_payment'),
    path('orders/<str:order_number>/reorder/', reorder, name='reorder'),
    path('statistics/', order_statistics, name='order_statistics'),
    
    # Seller Orders
    path('seller/orders/', SellerOrdersView.as_view(), name='seller_orders'),
    path('seller/orders/<str:order_number>/', SellerOrderDetailView.as_view(), name='seller_order_detail'),
    path('seller/items/<uuid:item_id>/update-status/', UpdateOrderItemStatusView.as_view(), name='update_item_status'),
    path('seller/statistics/', seller_statistics, name='seller_statistics'),
    
    # Shipping Addresses
    path('addresses/', ShippingAddressListCreateView.as_view(), name='address_list_create'),
    path('addresses/<uuid:pk>/', ShippingAddressDetailView.as_view(), name='address_detail'),
    path('addresses/<uuid:address_id>/set-default/', SetDefaultAddressView.as_view(), name='set_default_address'),
    
    # Refunds
    path('refunds/request/', RequestRefundView.as_view(), name='request_refund'),
    path('refunds/', MyRefundsView.as_view(), name='my_refunds'),
]