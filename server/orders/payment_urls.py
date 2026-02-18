#server/orders/payment_urls.py
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
                                             
    path('initialize/<str:order_number>/', InitializePaymentView.as_view(), name='initialize_payment'),
    path('verify/<str:order_number>/', VerifyPaymentView.as_view(), name='verify_payment'),
    
             
    path('webhook/paystack/', PaystackWebhookView.as_view(), name='paystack_webhook'),
    
             
    path('refunds/<uuid:refund_id>/process/', ProcessRefundView.as_view(), name='process_refund'),
    
                     
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
    
                     
    path('methods/', payment_methods, name='payment_methods'),
]
