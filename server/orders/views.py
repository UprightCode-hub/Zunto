#server/orders/views.py
from rest_framework import generics, serializers, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from notifications.email_service import EmailService

from .models import (
    Order, OrderItem, OrderStatusHistory, ShippingAddress,
    Payment, Refund
)
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, CheckoutSerializer,
    ShippingAddressSerializer, PaymentSerializer, RefundSerializer,
    CancelOrderSerializer, UpdateOrderStatusSerializer
)
from .permissions import IsOrderOwner, IsSellerOfOrderItem
from cart.models import Cart, CartItem
from market.models import Product
from .commerce import get_ineligible_sellers_for_items, is_managed_order
from core.permissions import IsSellerOrAdmin
from core.audit import audit_event


class CheckoutView(APIView):
    """Create order from cart"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                cart = Cart.objects.select_related('user').prefetch_related(
                    'items__product__seller',
                    'items__product__images'
                ).get(user=request.user)
            except Cart.DoesNotExist:
                return Response({
                    'error': 'Cart not found.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            if cart.is_empty:
                return Response({
                    'error': 'Cart is empty.'
                }, status=status.HTTP_400_BAD_REQUEST)
                                            
                                                               
            
                                            
                                            
                                                                
                                              
            unavailable_items = []
            insufficient_stock = []
            
            for item in cart.items.select_related('product'):
                product = Product.objects.select_for_update().get(id=item.product.id)
                
                if product.status != 'active':
                    unavailable_items.append({
                        'product': product.title,
                        'reason': 'Product is no longer active'
                    })
                    continue
                
                if product.quantity < item.quantity:
                    insufficient_stock.append({
                        'product': product.title,
                        'requested': item.quantity,
                        'available': product.quantity
                    })
            
            if unavailable_items or insufficient_stock:
                return Response({
                    'error': 'Some items in your cart are unavailable.',
                    'unavailable_items': unavailable_items,
                    'insufficient_stock': insufficient_stock
                }, status=status.HTTP_400_BAD_REQUEST)

            blocked_sellers = get_ineligible_sellers_for_items(cart.items.all())
            if blocked_sellers:
                return Response({
                    'error': (
                        'Checkout, shipping, and refunds are only available for verified '
                        'sellers using Zunto managed commerce. Please contact these sellers '
                        'directly in chat or remove their items to continue.'
                    ),
                    'blocked_sellers': blocked_sellers,
                }, status=status.HTTP_400_BAD_REQUEST)
            
                                  
            shipping_address_id = serializer.validated_data.get('shipping_address_id')
            
            if shipping_address_id:
                try:
                    saved_address = ShippingAddress.objects.get(
                        id=shipping_address_id,
                        user=request.user
                    )
                    shipping_data = {
                        'shipping_address': saved_address.address,
                        'shipping_city': saved_address.city,
                        'shipping_state': saved_address.state,
                        'shipping_country': saved_address.country,
                        'shipping_phone': saved_address.phone,
                        'shipping_email': request.user.email,
                    }
                except ShippingAddress.DoesNotExist:
                    return Response({
                        'error': 'Shipping address not found.'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                shipping_data = {
                    'shipping_address': serializer.validated_data['shipping_address'],
                    'shipping_city': serializer.validated_data['shipping_city'],
                    'shipping_state': serializer.validated_data['shipping_state'],
                    'shipping_country': serializer.validated_data.get('shipping_country', 'Nigeria'),
                    'shipping_phone': serializer.validated_data['shipping_phone'],
                    'shipping_email': serializer.validated_data['shipping_email'],
                }
            
                              
            subtotal = cart.subtotal
            tax_amount = 0                       
            shipping_fee = 0                            
            discount_amount = 0                         
            total_amount = subtotal + tax_amount + shipping_fee - discount_amount
            
                          
            order = Order.objects.create(
                customer=request.user,
                subtotal=subtotal,
                tax_amount=tax_amount,
                shipping_fee=shipping_fee,
                discount_amount=discount_amount,
                total_amount=total_amount,
                payment_method=serializer.validated_data['payment_method'],
                notes=serializer.validated_data.get('notes', ''),
                **shipping_data
            )
            
                                
            for cart_item in cart.items.all():
                product = cart_item.product
                
                                   
                primary_image = product.images.filter(is_primary=True).first()
                if not primary_image:
                    primary_image = product.images.first()
                
                product_image_url = ''
                if primary_image:
                    product_image_url = request.build_absolute_uri(primary_image.image.url)
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.title,
                    product_image=product_image_url,
                    seller=product.seller,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.price_at_addition
                )
                
                                         
                product.quantity -= cart_item.quantity
                product.save(update_fields=['quantity'])
            
                                                
            if serializer.validated_data.get('save_address'):
                ShippingAddress.objects.create(
                    user=request.user,
                    label=serializer.validated_data['address_label'],
                    full_name=request.user.get_full_name(),
                    phone=shipping_data['shipping_phone'],
                    address=shipping_data['shipping_address'],
                    city=shipping_data['shipping_city'],
                    state=shipping_data['shipping_state'],
                    country=shipping_data['shipping_country']
                )
            
                        
            cart.clear()

                                                          
            payment_data = None
            if serializer.validated_data['payment_method'] == 'paystack':
                from .paystack_service import PaystackService
                
                                            
                payment_reference = order.generate_payment_reference()
                
                                  
                callback_url = f"{request.scheme}://{request.get_host()}/payment/verify/{order.order_number}/"
                
                                  
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
                    
                                           
                    Payment.objects.create(
                        order=order,
                        payment_method='paystack',
                        amount=order.total_amount,
                        gateway_reference=payment_reference,
                        status='pending',
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                    
                    payment_data = {
                        'authorization_url': data['authorization_url'],
                        'access_code': data['access_code'],
                        'reference': payment_reference
                    }
            
            order_serializer = OrderDetailSerializer(order, context={'request': request})
            
            return Response({
                'message': 'Order created successfully.',
                'order': order_serializer.data,
                'payment_data': payment_data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
            
                                                                       
                                                                           
                                                     
                                  
                                                                                 
                                          
                                                     
                   
                   
                                     
            
                                                                                           
            
                               
                                                           
                                                 
                                              
                                                
        
                                                                                


class MyOrdersView(generics.ListAPIView):
    """List current user's orders"""
    
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Order.objects.filter(
            customer=self.request.user
        ).select_related('customer').prefetch_related('items').order_by('-created_at')


class OrderDetailView(generics.RetrieveAPIView):
    """Get order details"""
    
    serializer_class = OrderDetailSerializer
    permission_classes = [IsOrderOwner]
    lookup_field = 'order_number'
    
    def get_queryset(self):
        return Order.objects.select_related('customer').prefetch_related(
            'items__product',
            'items__seller',
            'status_history'
        )


class CancelOrderView(APIView):
    """Cancel an order"""
    
    permission_classes = [IsOrderOwner]
    
    @transaction.atomic
    def post(self, request, order_number):
        order = Order.objects.select_for_update().get(
            order_number=order_number,
            customer=request.user
        )

                                         
        if not order.can_cancel:
            return Response(
                {"detail": "Order cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

                                      
        serializer = CancelOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                             
        old_status = order.status
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.save(update_fields=['status', 'cancelled_at'])

                               
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status='cancelled',
            notes=serializer.validated_data['reason'],
            changed_by=request.user
        )

                                                     
        products_to_update = []
        items_to_update = []

        for item in order.items.all():
            if item.product:
                item.product.quantity += item.quantity
                products_to_update.append(item.product)
            item.status = 'cancelled'
            items_to_update.append(item)

        Product.objects.bulk_update(products_to_update, ['quantity'])
        OrderItem.objects.bulk_update(items_to_update, ['status'])

                                 
        EmailService.send_order_cancelled_email(order, serializer.validated_data['reason'])

                                                  
        if old_status == 'paid' or order.payment_status == 'paid':
                                   
            pass

        return Response({
            'message': 'Order cancelled successfully.',
            'order': OrderDetailSerializer(order, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class SellerOrdersView(generics.ListAPIView):
    """List orders for seller (orders containing their products)"""
    
    serializer_class = OrderListSerializer
    permission_classes = [IsSellerOrAdmin]
    
    def get_queryset(self):
        queryset = Order.objects.select_related('customer').prefetch_related('items').order_by('-created_at')
        if self.request.user.is_staff:
            return queryset.distinct()
        return queryset.filter(items__seller=self.request.user).distinct()


class SellerOrderDetailView(generics.RetrieveAPIView):
    """Get order details for seller"""
    
    serializer_class = OrderDetailSerializer
    permission_classes = [IsSellerOrAdmin]
    lookup_field = 'order_number'
    
    def get_queryset(self):
                                                              
        queryset = Order.objects.select_related('customer').prefetch_related(
            'items__product',
            'items__seller',
            'status_history'
        )
        if self.request.user.is_staff:
            return queryset.distinct()
        return queryset.filter(items__seller=self.request.user).distinct()


class UpdateOrderItemStatusView(APIView):
    """Update order item status (for sellers)"""

    permission_classes = [IsSellerOrAdmin, IsSellerOfOrderItem]

    def patch(self, request, item_id):
        item_qs = OrderItem.objects.filter(id=item_id)
        if not request.user.is_staff:
            item_qs = item_qs.filter(seller=request.user)
        item = get_object_or_404(item_qs)

        new_status = request.data.get('status')
        allowed_statuses = {choice[0] for choice in OrderItem.STATUS_CHOICES if choice[0] != 'pending'}
        if new_status not in allowed_statuses:
            return Response(
                {'error': f"Invalid status. Allowed values: {', '.join(sorted(allowed_statuses))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_item_status = item.status
        item.status = new_status
        item.save(update_fields=['status'])

        order = item.order
        item_statuses = list(order.items.values_list('status', flat=True).distinct())
        old_order_status = order.status

        if len(item_statuses) == 1 and item_statuses[0] == 'shipped':
            order.status = 'shipped'
            order.shipped_at = timezone.now()
            order.save(update_fields=['status', 'shipped_at'])
            EmailService.send_order_shipped_email(order)
        elif len(item_statuses) == 1 and item_statuses[0] == 'cancelled':
            order.status = 'cancelled'
            order.cancelled_at = timezone.now()
            order.save(update_fields=['status', 'cancelled_at'])
        else:
            order.status = 'processing'
            order.save(update_fields=['status'])

        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_order_status,
            new_status=order.status,
            notes=(
                f'Item {item.id} updated by {request.user.get_full_name() or request.user.email}: '
                f'{old_item_status} -> {new_status}'
            ),
            changed_by=request.user,
        )
        audit_event(
            request,
            action='orders.item.status_updated',
            extra={
                'order_id': str(order.id),
                'order_number': order.order_number,
                'order_item_id': str(item.id),
                'item_old_status': old_item_status,
                'item_new_status': item.status,
                'order_old_status': old_order_status,
                'order_new_status': order.status,
            },
        )

        return Response(
            {
                'message': 'Order item status updated.',
                'item_status': item.status,
                'order_status': order.status,
            },
            status=status.HTTP_200_OK,
        )


class ShippingAddressListCreateView(generics.ListCreateAPIView):
    """List and create shipping addresses"""
    
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user)


class ShippingAddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, and delete shipping address"""
    
    serializer_class = ShippingAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ShippingAddress.objects.filter(user=self.request.user)


class SetDefaultAddressView(APIView):
    """Set shipping address as default"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, address_id):
        address = get_object_or_404(
            ShippingAddress,
            id=address_id,
            user=request.user
        )
        
                                  
        ShippingAddress.objects.filter(
            user=request.user,
            is_default=True
        ).update(is_default=False)
        
                             
        address.is_default = True
        address.save(update_fields=['is_default'])
        
        return Response({
            'message': 'Default address updated.',
            'address': ShippingAddressSerializer(address).data
        }, status=status.HTTP_200_OK)


class RequestRefundView(generics.CreateAPIView):
    """Request refund for order"""
    
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        order = serializer.validated_data['order']
        
                                        
        if order.customer != self.request.user:
            raise serializers.ValidationError('This order does not belong to you.')
        
                                
        if order.payment_status != 'paid':
            raise serializers.ValidationError('Order must be paid before requesting refund.')
        
                                        
        if order.status in ['cancelled', 'refunded']:
            raise serializers.ValidationError('Order has already been cancelled or refunded.')

        if not is_managed_order(order):
            raise serializers.ValidationError(
                'Refunds are available only for orders sold through Zunto managed commerce.'
            )
        
        serializer.save()


class MyRefundsView(generics.ListAPIView):
    """List user's refund requests"""
    
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Refund.objects.filter(
            order__customer=self.request.user
        ).select_related('order', 'payment').order_by('-created_at')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_statistics(request):
    """Get order statistics for user"""

    from django.db.models import Count, Q, Sum

    orders = Order.objects.filter(customer=request.user)
    stats = orders.aggregate(
        total_orders=Count('id'),
        pending_orders=Count('id', filter=Q(status='pending')),
        processing_orders=Count('id', filter=Q(status='processing')),
        shipped_orders=Count('id', filter=Q(status='shipped')),
        delivered_orders=Count('id', filter=Q(status='delivered')),
        cancelled_orders=Count('id', filter=Q(status='cancelled')),
        total_spent=Sum('total_amount', filter=Q(payment_status='paid')),
    )
    stats['total_spent'] = stats.get('total_spent') or 0

    return Response(stats)


@api_view(['GET'])
@permission_classes([IsSellerOrAdmin])
def seller_statistics(request):
    """Get sales statistics for seller"""

    from django.db.models import Count, Q, Sum

    if request.user.is_staff:
        orders = Order.objects.all()
        items = OrderItem.objects.all()
    else:
        orders = Order.objects.filter(items__seller=request.user)
        items = OrderItem.objects.filter(seller=request.user)

    order_counts = orders.aggregate(total_orders=Count('id', distinct=True))
    item_stats = items.aggregate(
        pending_items=Count('id', filter=Q(status='pending')),
        shipped_items=Count('id', filter=Q(status='shipped')),
        cancelled_items=Count('id', filter=Q(status='cancelled')),
        total_sales=Sum('total_price', filter=Q(order__payment_status='paid')),
        total_items_sold=Sum('quantity', filter=Q(order__payment_status='paid')),
    )

    stats = {
        'total_orders': order_counts.get('total_orders') or 0,
        'pending_items': item_stats.get('pending_items') or 0,
        'shipped_items': item_stats.get('shipped_items') or 0,
        'cancelled_items': item_stats.get('cancelled_items') or 0,
        'total_sales': item_stats.get('total_sales') or 0,
        'total_items_sold': item_stats.get('total_items_sold') or 0,
    }

    audit_event(request, action='orders.seller.statistics_viewed', extra={'is_staff': request.user.is_staff})
    return Response(stats)



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_payment(request, order_number):
    """Verify payment for order (Paystack webhook)"""
    
    order = get_object_or_404(Order, order_number=order_number, customer=request.user)

    if not is_managed_order(order):
        return Response({
            'error': 'Payment verification is only available for Zunto managed-commerce orders.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
                                 
    reference = request.data.get('reference')
    
                                    
                                
    
    if order.payment_status != 'paid':
        order.payment_status = 'paid'
        order.status = 'processing'
        order.paid_at = timezone.now()
        order.save(update_fields=['payment_status', 'status', 'paid_at'])
        
                               
        Payment.objects.create(
            order=order,
            payment_method=order.payment_method,
            amount=order.total_amount,
            status='success',
            gateway_reference=reference,
            paid_at=timezone.now()
        )
        
                               
        OrderStatusHistory.objects.create(
            order=order,
            old_status='pending',
            new_status='processing',
            notes='Payment verified',
            changed_by=request.user
        )
        
                                             
        
        return Response({
            'message': 'Payment verified successfully.',
            'order': OrderDetailSerializer(order, context={'request': request}).data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'message': 'Payment already verified.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reorder(request, order_number):
    """Add items from previous order to cart"""
    
    order = get_object_or_404(
        Order,
        order_number=order_number,
        customer=request.user
    )
    
                        
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    added_items = []
    unavailable_items = []
    
    for order_item in order.items.all():
        product = order_item.product
        
        if not product or not product.is_available:
            unavailable_items.append(order_item.product_name)
            continue
        
                     
        if product.quantity < order_item.quantity:
            unavailable_items.append(f"{order_item.product_name} (only {product.quantity} available)")
            continue
        
                     
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': order_item.quantity}
        )
        
        if not item_created:
                             
            new_quantity = cart_item.quantity + order_item.quantity
            if new_quantity <= product.quantity:
                cart_item.quantity = new_quantity
                cart_item.save()
                added_items.append(product.title)
            else:
                unavailable_items.append(f"{product.title} (insufficient stock)")
        else:
            added_items.append(product.title)
    
    return Response({
        'message': 'Items added to cart.',
        'added_items': added_items,
        'unavailable_items': unavailable_items
    }, status=status.HTTP_200_OK)
