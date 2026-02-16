# orders/views.py
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
# =================================================================================
             # Send order confirmation email
            # EmailService.send_order_confirmation_email(order)
            
            # # Send notification to sellers
            # for item in order.items.all():
            #     EmailService.send_seller_new_order_email(item)
# ================================================================================
            # Validate all items are available
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
            
            # Get shipping address
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
            
            # Calculate totals
            subtotal = cart.subtotal
            tax_amount = 0  # TODO: Calculate tax
            shipping_fee = 0  # TODO: Calculate shipping
            discount_amount = 0  # TODO: Apply discounts
            total_amount = subtotal + tax_amount + shipping_fee - discount_amount
            
            # Create order
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
            
            # Create order items
            for cart_item in cart.items.all():
                product = cart_item.product
                
                # Get primary image
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
                
                # Reduce product quantity
                product.quantity -= cart_item.quantity
                product.save(update_fields=['quantity'])
            
            # Save shipping address if requested
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
            
            # Clear cart
            cart.clear()

        # Initialize payment if payment method is paystack
            payment_data = None
            if serializer.validated_data['payment_method'] == 'paystack':
                from .paystack_service import PaystackService
                
                # Generate payment reference
                payment_reference = order.generate_payment_reference()
                
                # Get callback URL
                callback_url = f"{request.scheme}://{request.get_host()}/payment/verify/{order.order_number}/"
                
                # Prepare metadata
                metadata = {
                    'order_number': order.order_number,
                    'customer_id': str(order.customer.id),
                    'customer_name': order.customer.get_full_name(),
                    'items_count': order.total_items,
                }
                
                # Initialize payment
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
                    
                    # Create payment record
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
            
        #     # Return order with payment initialization data if needed
        #     if serializer.validated_data['payment_method'] == 'paystack':
        #         # TODO: Initialize Paystack payment
        #         payment_data = {
        #             'authorization_url': None,  # Will be populated by Paystack
        #             'access_code': None,
        #             'reference': order.order_number
        #         }
        #     else:
        #         payment_data = None
            
        #     order_serializer = OrderDetailSerializer(order, context={'request': request})
            
        #     return Response({
        #         'message': 'Order created successfully.',
        #         'order': order_serializer.data,
        #         'payment_data': payment_data
        #     }, status=status.HTTP_201_CREATED)
        
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

        # Check if order can be cancelled
        if not order.can_cancel:
            return Response(
                {"detail": "Order cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate cancellation reason
        serializer = CancelOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update order status
        old_status = order.status
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.save(update_fields=['status', 'cancelled_at'])

        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status='cancelled',
            notes=serializer.validated_data['reason'],
            changed_by=request.user
        )

        # Restore product quantities and update items
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

        # Send cancellation email
        EmailService.send_order_cancelled_email(order, serializer.validated_data['reason'])

        # TODO: Process refund if payment was made
        if old_status == 'paid' or order.payment_status == 'paid':
            # Create refund request
            pass

        return Response({
            'message': 'Order cancelled successfully.',
            'order': OrderDetailSerializer(order, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class SellerOrdersView(generics.ListAPIView):
    """List orders for seller (orders containing their products)"""
    
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Get orders that have items sold by this user
        return Order.objects.filter(
            items__seller=self.request.user
        ).distinct().select_related('customer').prefetch_related('items').order_by('-created_at')


class SellerOrderDetailView(generics.RetrieveAPIView):
    """Get order details for seller"""
    
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'order_number'
    
    def get_queryset(self):
        # Seller can only see orders containing their products
        return Order.objects.filter(
            items__seller=self.request.user
        ).distinct().select_related('customer').prefetch_related(
            'items__product',
            'items__seller',
            'status_history'
        )


class UpdateOrderItemStatusView(APIView):
    """Update order item status (for sellers)"""
    
    permission_classes = [IsSellerOfOrderItem]
    
    def patch(self, request, item_id):
        item = get_object_or_404(
            OrderItem,
            id=item_id,
            seller=request.user
        )
        
        new_status = request.data.get('status')
        
        valid_statuses = ['processing', 'shipped', 'delivered']
        if new_status not in valid_statuses:
            if new_status == 'shipped':
                EmailService.send_order_shipped_email(order)
            elif new_status == 'delivered':
                EmailService.send_order_delivered_email(order)
        
        return Response({
            'message': 'Order item status updated.',
            'item_status': new_status,
            'order_status': order.status
        }, status=status.HTTP_200_OK)

        old_status = item.status
        item.status = new_status
        item.save(update_fields=['status'])
        
        # Update main order status if all items have same status
        order = item.order
        all_items_status = order.items.values_list('status', flat=True).distinct()
        
        if len(all_items_status) == 1:
            # All items have same status, update order
            order.status = new_status
            if new_status == 'shipped':
                order.shipped_at = timezone.now()
            elif new_status == 'delivered':
                order.delivered_at = timezone.now()
                order.payment_status = 'paid'  # Mark as paid on delivery
            order.save()
            
            # Create status history
            OrderStatusHistory.objects.create(
                order=order,
                old_status=old_status,
                new_status=new_status,
                notes=f'Item updated by seller: {request.user.get_full_name()}',
                changed_by=request.user
            )
        
        return Response({
            'message': 'Order item status updated.',
            'item_status': new_status,
            'order_status': order.status
        }, status=status.HTTP_200_OK)


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
        
        # Unset all other defaults
        ShippingAddress.objects.filter(
            user=request.user,
            is_default=True
        ).update(is_default=False)
        
        # Set this as default
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
        
        # Validate order belongs to user
        if order.customer != self.request.user:
            raise serializers.ValidationError('This order does not belong to you.')
        
        # Check if order is paid
        if order.payment_status != 'paid':
            raise serializers.ValidationError('Order must be paid before requesting refund.')
        
        # Check if order can be refunded
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
    
    from django.db.models import Count, Sum, Q
    
    orders = Order.objects.filter(customer=request.user)
    
    stats = {
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'processing_orders': orders.filter(status='processing').count(),
        'shipped_orders': orders.filter(status='shipped').count(),
        'delivered_orders': orders.filter(status='delivered').count(),
        'cancelled_orders': orders.filter(status='cancelled').count(),
        'total_spent': orders.filter(
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def seller_statistics(request):
    """Get sales statistics for seller"""
    
    from django.db.models import Count, Sum, Q
    
    # Get orders containing seller's items
    orders = Order.objects.filter(items__seller=request.user).distinct()
    
    # Get seller's order items
    items = OrderItem.objects.filter(seller=request.user)
    
    stats = {
        'total_orders': orders.count(),
        'pending_items': items.filter(status='pending').count(),
        'processing_items': items.filter(status='processing').count(),
        'shipped_items': items.filter(status='shipped').count(),
        'delivered_items': items.filter(status='delivered').count(),
        'total_sales': items.filter(
            order__payment_status='paid'
        ).aggregate(total=Sum('total_price'))['total'] or 0,
        'total_items_sold': items.filter(
            order__payment_status='paid'
        ).aggregate(total=Sum('quantity'))['total'] or 0,
    }
    
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
    
    # Verify with payment gateway
    reference = request.data.get('reference')
    
    # TODO: Verify with Paystack API
    # For now, just mark as paid
    
    if order.payment_status != 'paid':
        order.payment_status = 'paid'
        order.status = 'processing'
        order.paid_at = timezone.now()
        order.save(update_fields=['payment_status', 'status', 'paid_at'])
        
        # Create payment record
        Payment.objects.create(
            order=order,
            payment_method=order.payment_method,
            amount=order.total_amount,
            status='success',
            gateway_reference=reference,
            paid_at=timezone.now()
        )
        
        # Create status history
        OrderStatusHistory.objects.create(
            order=order,
            old_status='pending',
            new_status='processing',
            notes='Payment verified',
            changed_by=request.user
        )
        
        # TODO: Send order confirmation email
        
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
    
    # Get or create cart
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    added_items = []
    unavailable_items = []
    
    for order_item in order.items.all():
        product = order_item.product
        
        if not product or not product.is_available:
            unavailable_items.append(order_item.product_name)
            continue
        
        # Check stock
        if product.quantity < order_item.quantity:
            unavailable_items.append(f"{order_item.product_name} (only {product.quantity} available)")
            continue
        
        # Add to cart
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': order_item.quantity}
        )
        
        if not item_created:
            # Update quantity
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
