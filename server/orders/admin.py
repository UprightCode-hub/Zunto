from django.contrib import admin

# Register your models here.
# orders/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Order, OrderItem, OrderStatusHistory, ShippingAddress,
    Payment, Refund, OrderNote
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name','unit_price','get_seller_name', 'total_price']
    fields = ['product', 'product_name', 'seller','get_seller_name', 'quantity', 'unit_price', 'total_price']

    def get_seller_name(self, obj):
        return obj.seller.email if obj.seller else None
    get_seller_name.short_description = 'Seller'


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['old_status', 'new_status', 'notes', 'changed_by', 'created_at']
    can_delete = False


class OrderNoteInline(admin.TabularInline):
    model = OrderNote
    extra = 1
    fields = ['note', 'is_customer_visible', 'created_by']

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['payment_method', 'amount', 'status', 'gateway_reference', 'created_at', 'paid_at']
    can_delete = False
    fields = ['payment_method', 'amount', 'status', 'gateway_reference', 'created_at', 'paid_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer', 'status_badge', 
        'total_amount', 'total_items', 'created_at'
    ]
    list_filter = ['status',  'payment_method', 'created_at']
    search_fields = ['order_number', 'customer__email', 'shipping_phone']
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 'paid_at',
        'shipped_at', 'delivered_at', 'cancelled_at'
    ]
    inlines = [OrderItemInline, OrderStatusHistoryInline, OrderNoteInline, PaymentInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'status', 'payment_method')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax_amount', 'shipping_fee', 'discount_amount', 'total_amount')
        }),
        ('Shipping Information', {
            'fields': (
                'shipping_address_ref', 'shipping_full_name', 'shipping_phone',
                'shipping_address', 'shipping_city', 'shipping_state',
                'shipping_country', 'shipping_postal_code', 'tracking_number'
            )
        }),

        ('Payment', {
            'fields': ('payment_reference',)
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at', 'shipped_at', 'delivered_at', 'cancelled_at')
        }),
    )
    
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'paid': 'blue',
            'processing': 'cyan',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red',
            'refunded': 'gray',
            'failed': 'darkred',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    # def payment_status_badge(self, obj):
    #     colors = {
    #         'pending': 'orange',
    #         'paid': 'green',
    #         'failed': 'red',
    #         'refunded': 'gray',
    #     }
    #     color = colors.get(obj.payment_status, 'gray')
    #     return format_html(
    #         '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
    #         color,
    #         obj.get_payment_status_display()
    #     )
    # payment_status_badge.short_description = 'Payment Status'
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Items'
    
    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
        self.message_user(request, f"{queryset.count()} orders marked as processing.")
    mark_as_processing.short_description = "Mark as Processing"
    
    def mark_as_shipped(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='shipped', shipped_at=timezone.now())
        self.message_user(request, f"{queryset.count()} orders marked as shipped.")
    mark_as_shipped.short_description = "Mark as Shipped"
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f"{queryset.count()} orders marked as delivered.")
    mark_as_delivered.short_description = "Mark as Delivered"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'product_name',  'quantity',
        'unit_price', 'total_price', 'created_at'
    ]
    list_filter = [ 'created_at']
    search_fields = ['order__order_number', 'product_name',]
    readonly_fields = ['total_price', 'created_at']


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'full_name', 'city', 'state', 'is_default', 'created_at']
    list_filter = ['is_default', 'state', 'created_at']
    search_fields = ['user__email', 'full_name', 'phone']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'gateway_reference', 'order', 'payment_method', 'amount',
        'status', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['gateway_reference', 'order__order_number']
    readonly_fields = ['created_at', 'updated_at', 'paid_at']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'amount', 'reason', 'status',
        'created_at', 'processed_at'
    ]
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['order__order_number', 'refund_reference']
    readonly_fields = ['created_at', 'processed_at']
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('order', 'payment', 'amount', 'reason', 'description')
        }),
        ('Status', {
            'fields': ('status', 'admin_notes', 'processed_by')
        }),
        ('Gateway', {
            'fields': ('refund_reference', 'gateway_response')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at')
        }),
    )
    
    actions = ['approve_refunds', 'reject_refunds']
    
    def approve_refunds(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', processed_at=timezone.now(), processed_by=request.user)
        self.message_user(request, f"{queryset.count()} refunds approved.")
    approve_refunds.short_description = "Approve selected refunds"
    
    def reject_refunds(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='failed', processed_at=timezone.now(), processed_by=request.user)
        self.message_user(request, f"{queryset.count()} refunds rejected.")
    reject_refunds.short_description = "Reject selected refunds"


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['order', 'old_status', 'new_status', 'changed_by', 'created_at']
    list_filter = ['old_status', 'new_status', 'created_at']
    search_fields = ['order__order_number']
    readonly_fields = ['created_at']


@admin.register(OrderNote)
class OrderNoteAdmin(admin.ModelAdmin):
    list_display = ['order', 'is_customer_visible', 'created_by', 'created_at']
    list_filter = ['is_customer_visible', 'created_at']
    search_fields = ['order__order_number', 'note']
    readonly_fields = ['created_at']

