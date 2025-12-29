# orders/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Order, OrderItem, OrderStatusHistory, ShippingAddress,
    Payment, Refund, OrderNote
)
from cart.models import Cart

User = get_user_model()


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""
    seller_name = serializers.SerializerMethodField()
    # status = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name',  'product_image',
            'seller', 'seller_name', 'quantity', 'unit_price', 'total_price',
            'status', 'created_at'
        ]
        read_only_fields = fields
    def get_seller_name(self, obj):
        if obj.seller:
            return obj.seller.username  # or obj.seller.get_full_name()
        return None

    # def get_status(self, obj):
    #     # If status is coming from the parent Order, e.g., obj.order.status
    #     return getattr(obj.order, 'status', None) 


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for order status history"""
    
    changed_by_name = serializers.CharField(
        source='changed_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = OrderStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'notes',
            'changed_by', 'changed_by_name', 'created_at'
        ]
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    """Serializer for order list view"""
    
    customer_name = serializers.CharField(
        source='customer.get_full_name',
        read_only=True
    )
    total_items = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name',
            'status', 'payment_status', 'payment_method',
            'total_items', 'total_amount', 'created_at'
        ]
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializer for order detail view"""
    
    customer_name = serializers.CharField(
        source='customer.get_full_name',
        read_only=True
    )
    customer_email = serializers.CharField(
        source='customer.email',
        read_only=True
    )
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'customer_email',
            'status', 'payment_status', 'payment_method', 'payment_reference',
            'subtotal', 'tax_amount', 'shipping_fee', 'discount_amount', 'total_amount',
            'shipping_address', 'shipping_city', 'shipping_state', 'shipping_country',
            'shipping_phone', 'shipping_email', 'notes', 'tracking_number',
            'items', 'status_history', 'total_items', 'can_cancel', 'is_paid',
            'created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at', 'cancelled_at'
        ]
        read_only_fields = fields


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout"""
    
    # Shipping address (can be new or use saved address)
    shipping_address_id = serializers.UUIDField(required=False)
    
    # Or provide new shipping details
    shipping_address = serializers.CharField(required=False)
    shipping_city = serializers.CharField(required=False)
    shipping_state = serializers.CharField(required=False)
    shipping_country = serializers.CharField(default='Nigeria')
    shipping_phone = serializers.CharField(required=False)
    shipping_email = serializers.EmailField(required=False)
    
    # Payment
    payment_method = serializers.ChoiceField(
        choices=['paystack', 'bank_transfer', 'cash_on_delivery', 'wallet']
    )
    
    # Additional
    notes = serializers.CharField(required=False, allow_blank=True)
    save_address = serializers.BooleanField(default=False)
    address_label = serializers.CharField(required=False)
    
    def validate(self, attrs):
        # Must provide either shipping_address_id or full shipping details
        if not attrs.get('shipping_address_id'):
            required_fields = [
                'shipping_address', 'shipping_city', 'shipping_state',
                'shipping_phone', 'shipping_email'
            ]
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError({
                        field: f"{field.replace('_', ' ').title()} is required."
                    })
        
        # If save_address is True, address_label is required
        if attrs.get('save_address') and not attrs.get('address_label'):
            raise serializers.ValidationError({
                'address_label': 'Address label is required when saving address.'
            })
        
        return attrs


class ShippingAddressSerializer(serializers.ModelSerializer):
    """Serializer for shipping addresses"""
    
    class Meta:
        model = ShippingAddress
        fields = [
            'id', 'label', 'full_name', 'phone', 'address',
            'city', 'state', 'country', 'postal_code',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'payment_method', 'amount',
            'currency', 'status', 'gateway_reference',
            'created_at', 'paid_at'
        ]
        read_only_fields = fields


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refunds"""
    
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'order', 'order_number', 'payment', 'amount',
            'reason', 'description', 'status', 'refund_reference',
            'admin_notes', 'created_at', 'processed_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'status', 'refund_reference',
            'admin_notes', 'processed_at', 'created_at'
        ]


class CancelOrderSerializer(serializers.Serializer):
    """Serializer for cancelling orders"""
    
    reason = serializers.CharField(required=True)


class UpdateOrderStatusSerializer(serializers.Serializer):
    """Serializer for updating order status"""
    
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)