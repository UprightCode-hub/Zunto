#server/orders/payment_views.py
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .models import Order, Payment, Refund, OrderStatusHistory
from .paystack_service import PaystackService
from .serializers import PaymentSerializer
from .commerce import is_managed_order


class InitializePaymentView(APIView):
    """Initialize payment with Paystack"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, order_number):
        order = get_object_or_404(
            Order,
            order_number=order_number,
            customer=request.user
        )

        if not is_managed_order(order):
            return Response({
                'error': 'Platform payment is only available for Zunto managed-commerce orders.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
                                        
        if order.payment_status == 'paid':
            return Response({
                'error': 'Order has already been paid.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
                                    
        payment_reference = order.generate_payment_reference()
        
                                                      
        callback_url = request.data.get('callback_url') or\
                      f"{request.scheme}://{request.get_host()}/payment/verify/{order_number}/"
        
                          
        metadata = {
            'order_number': order.order_number,
            'customer_id': str(order.customer.id),
            'customer_name': order.customer.get_full_name(),
            'items_count': order.total_items,
        }
        
                                          
        paystack = PaystackService()
        result = paystack.initialize_transaction(
            email=order.customer.email,
            amount=order.total_amount,
            reference=payment_reference,
            callback_url=callback_url,
            metadata=metadata
        )
        
        if result['success']:
            data = result['data']['data']
            
                                             
            payment, created = Payment.objects.get_or_create(
                order=order,
                gateway_reference=payment_reference,
                defaults={
                    'payment_method': 'paystack',
                    'amount': order.total_amount,
                    'status': 'pending',
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')
                }
            )
            
            return Response({
                'message': 'Payment initialized successfully.',
                'data': {
                    'authorization_url': data['authorization_url'],
                    'access_code': data['access_code'],
                    'reference': payment_reference
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to initialize payment.',
                'details': result.get('error', 'Unknown error')
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class VerifyPaymentView(APIView):
    """Verify payment with Paystack"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def get(self, request, order_number):
        order = get_object_or_404(
            Order,
            order_number=order_number,
            customer=request.user
        )

        if not is_managed_order(order):
            return Response({
                'error': 'Platform payment verification is only available for managed-commerce orders.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
                                                                  
        reference = request.query_params.get('reference') or order.payment_reference
        
        if not reference:
            return Response({
                'error': 'Payment reference not found.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
                                          
        paystack = PaystackService()
        result = paystack.verify_transaction(reference)
        
        if not result['success']:
            return Response({
                'error': 'Failed to verify payment.',
                'details': result.get('error', 'Unknown error')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        data = result['data']['data']
        
                                         
        if data['status'] == 'success':
                                   
            payment = Payment.objects.filter(
                order=order,
                gateway_reference=reference
            ).first()
            
            if payment:
                payment.status = 'success'
                payment.paid_at = timezone.now()
                payment.gateway_response = data
                payment.save()
            else:
                                                           
                payment = Payment.objects.create(
                    order=order,
                    payment_method='paystack',
                    amount=order.total_amount,
                    gateway_reference=reference,
                    status='success',
                    paid_at=timezone.now(),
                    gateway_response=data
                )
            
                          
            old_status = order.status
            order.payment_status = 'paid'
            order.status = 'processing'
            order.paid_at = timezone.now()
            order.save(update_fields=['payment_status', 'status', 'paid_at'])
            
                                   
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status='processing',
                notes='Payment verified successfully',
                changed_by=request.user
            )
            
                                                 
            EmailService.send_payment_success_email(order)
            
            return Response({
                'message': 'Payment verified successfully.',
                'order': {
                    'order_number': order.order_number,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'amount_paid': str(order.total_amount)
                }
            }, status=status.HTTP_200_OK)
        
        else:
                            
            payment = Payment.objects.filter(
                order=order,
                gateway_reference=reference
            ).first()
            
            if payment:
                payment.status = 'failed'
                payment.gateway_response = data
                payment.save()
            
            order.payment_status = 'failed'
            order.save(update_fields=['payment_status'])
            
            return Response({
                'error': 'Payment verification failed.',
                'message': data.get('gateway_response', 'Payment was not successful')
            }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhookView(APIView):
    """Handle Paystack webhook events"""
    
    permission_classes = []                                           
    
    @transaction.atomic
    def post(self, request):
                                    
        signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
        
        if not signature:
            return Response({
                'error': 'No signature provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
                                  
        if not PaystackService.verify_webhook_signature(request.body, signature):
            return Response({
                'error': 'Invalid signature'
            }, status=status.HTTP_400_BAD_REQUEST)
        
                            
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return Response({
                'error': 'Invalid JSON'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        event = payload.get('event')
        data = payload.get('data', {})
        
                                      
        if event == 'charge.success':
            return self.handle_charge_success(data)
        
        elif event == 'charge.failed':
            return self.handle_charge_failed(data)
        
        elif event == 'refund.processed':
            return self.handle_refund_processed(data)
        
        elif event == 'refund.failed':
            return self.handle_refund_failed(data)
        
                                             
        return Response({'status': 'received'}, status=status.HTTP_200_OK)
    
    def handle_charge_success(self, data):
        """Handle successful charge"""
        reference = data.get('reference')
        
        try:
            payment = Payment.objects.select_related('order').get(
                gateway_reference=reference
            )
            order = payment.order
            
                            
            payment.status = 'success'
            payment.paid_at = timezone.now()
            payment.gateway_response = data
            payment.save()
            
                          
            if order.payment_status != 'paid':
                old_status = order.status
                order.payment_status = 'paid'
                order.status = 'processing'
                order.paid_at = timezone.now()
                order.save(update_fields=['payment_status', 'status', 'paid_at'])
                
                                       
                OrderStatusHistory.objects.create(
                    order=order,
                    old_status=old_status,
                    new_status='processing',
                    notes='Payment confirmed via webhook'
                )
                
                                                 
            EmailService.send_payment_success_email(order)

            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
        except Payment.DoesNotExist:
            return Response({
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def handle_charge_failed(self, data):
        """Handle failed charge"""
        reference = data.get('reference')
        
        try:
            payment = Payment.objects.select_related('order').get(
                gateway_reference=reference
            )
            order = payment.order
            
                            
            payment.status = 'failed'
            payment.gateway_response = data
            payment.save()
            
                          
            order.payment_status = 'failed'
            order.save(update_fields=['payment_status'])
            
                                                     
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
        except Payment.DoesNotExist:
            return Response({
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def handle_refund_processed(self, data):
        """Handle processed refund"""
        transaction_reference = data.get('transaction_reference')
        
        try:
            payment = Payment.objects.select_related('order').get(
                gateway_reference=transaction_reference
            )
            
                                 
            refund = Refund.objects.filter(
                payment=payment,
                status='pending'
            ).first()
            
            if refund:
                refund.status = 'completed'
                refund.refund_reference = data.get('id')
                refund.gateway_response = data
                refund.processed_at = timezone.now()
                refund.save()
                
                              
                order = payment.order
                order.status = 'refunded'
                order.payment_status = 'refunded'
                order.save(update_fields=['status', 'payment_status'])
                
                                       
                OrderStatusHistory.objects.create(
                    order=order,
                    old_status=order.status,
                    new_status='refunded',
                    notes='Refund processed successfully'
                )
                
                                                      
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
        except Payment.DoesNotExist:
            return Response({
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def handle_refund_failed(self, data):
        """Handle failed refund"""
        transaction_reference = data.get('transaction_reference')
        
        try:
            payment = Payment.objects.get(gateway_reference=transaction_reference)
            
                                 
            refund = Refund.objects.filter(
                payment=payment,
                status='processing'
            ).first()
            
            if refund:
                refund.status = 'failed'
                refund.gateway_response = data
                refund.save()
                
                                                        
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
        except Payment.DoesNotExist:
            return Response({
                'error': 'Payment not found'
            }, status=status.HTTP_404_NOT_FOUND)


class ProcessRefundView(APIView):
    """Process refund through Paystack"""
    
    permission_classes = [permissions.IsAdminUser]
    
    @transaction.atomic
    def post(self, request, refund_id):
        refund = get_object_or_404(Refund, id=refund_id)
        
        if refund.status != 'pending':
            return Response({
                'error': f'Refund is already {refund.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
                     
        payment = refund.payment
        if not payment:
            return Response({
                'error': 'Payment not found for this refund'
            }, status=status.HTTP_404_NOT_FOUND)
        
                                         
        paystack = PaystackService()
        result = paystack.create_refund(
            transaction_reference=payment.gateway_reference,
            amount=refund.amount
        )
        
        if result['success']:
            data = result['data']['data']
            
                           
            refund.status = 'processing'
            refund.refund_reference = data.get('id')
            refund.gateway_response = data
            refund.processed_by = request.user
            refund.save()
            
            return Response({
                'message': 'Refund initiated successfully.',
                'refund': {
                    'id': str(refund.id),
                    'amount': str(refund.amount),
                    'status': refund.status,
                    'reference': refund.refund_reference
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to process refund.',
                'details': result.get('error', 'Unknown error')
            }, status=status.HTTP_400_BAD_REQUEST)


class PaymentHistoryView(APIView):
    """Get payment history for user"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        payments = Payment.objects.filter(
            order__customer=request.user
        ).select_related('order').order_by('-created_at')
        
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_methods(request):
    """Get available payment methods"""
    
    methods = [
        {
            'id': 'paystack',
            'name': 'Paystack',
            'description': 'Pay securely with your card or bank account',
            'logo': '/static/images/paystack.png',
            'enabled': True
        },
        {
            'id': 'bank_transfer',
            'name': 'Bank Transfer',
            'description': 'Transfer directly to our bank account',
            'enabled': True
        },
        {
            'id': 'cash_on_delivery',
            'name': 'Cash on Delivery',
            'description': 'Pay when you receive your order',
            'enabled': True
        },
    ]
    
    return Response(methods)
