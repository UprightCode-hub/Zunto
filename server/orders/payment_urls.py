# orders/payment_urls.py
from django.urls import path
from .payment_views import (
    InitializePaymentView,
    VerifyPaymentView,
    PaystackWebhookView,
    ProcessRefundView,
    PaymentHistoryView,
    payment_methods,
)

app_name = 'payments'

urlpatterns = [
    # Payment initialization and verification
    path('initialize/<str:order_number>/', InitializePaymentView.as_view(), name='initialize_payment'),
    path('verify/<str:order_number>/', VerifyPaymentView.as_view(), name='verify_payment'),
    
    # Webhook
    path('webhook/paystack/', PaystackWebhookView.as_view(), name='paystack_webhook'),
    
    # Refunds
    path('refunds/<uuid:refund_id>/process/', ProcessRefundView.as_view(), name='process_refund'),
    
    # Payment history
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
    
    # Payment methods
    path('methods/', payment_methods, name='payment_methods'),
]