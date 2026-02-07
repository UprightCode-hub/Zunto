from django.contrib import admin
from .models import Cart, CartItem, SavedForLater, CartAbandonment, UserScore


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['price_at_addition', 'added_at', 'updated_at']
    fields = ['product', 'quantity', 'price_at_addition', 'added_at']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_id', 'total_items', 'subtotal', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'session_id']
    readonly_fields = ['created_at', 'updated_at', 'total_items', 'subtotal']
    inlines = [CartItemInline]
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'session_id')
        }),
        ('Statistics', {
            'fields': ('total_items', 'subtotal')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'
    
    def subtotal(self, obj):
        return f"₦{obj.subtotal:,.2f}"
    subtotal.short_description = 'Subtotal'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity', 'price_at_addition', 'total_price', 'added_at']
    list_filter = ['added_at', 'updated_at']
    search_fields = ['cart__user__email', 'product__title']
    readonly_fields = ['price_at_addition', 'added_at', 'updated_at', 'total_price']
    fieldsets = (
        ('Item Information', {
            'fields': ('cart', 'product', 'quantity')
        }),
        ('Pricing', {
            'fields': ('price_at_addition', 'total_price')
        }),
        ('Timestamps', {
            'fields': ('added_at', 'updated_at')
        }),
    )
    
    def total_price(self, obj):
        return f"₦{obj.total_price:,.2f}"
    total_price.short_description = 'Total Price'


@admin.register(SavedForLater)
class SavedForLaterAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'saved_at']
    list_filter = ['saved_at']
    search_fields = ['user__email', 'product__title']
    readonly_fields = ['saved_at']


@admin.register(CartAbandonment)
class CartAbandonmentAdmin(admin.ModelAdmin):
    list_display = [
        'cart', 'user', 'total_items', 'total_value',
        'recovered', 'reminder_sent', 'abandoned_at'
    ]
    list_filter = ['recovered', 'reminder_sent', 'abandoned_at']
    search_fields = ['user__email', 'cart__id']
    readonly_fields = ['abandoned_at', 'recovered_at', 'reminder_sent_at']
    fieldsets = (
        ('Cart Information', {
            'fields': ('cart', 'user', 'total_items', 'total_value')
        }),
        ('Recovery Status', {
            'fields': ('recovered', 'recovered_at', 'reminder_sent', 'reminder_sent_at')
        }),
        ('Timestamp', {
            'fields': ('abandoned_at',)
        }),
    )
    actions = ['mark_as_recovered']
    
    def mark_as_recovered(self, request, queryset):
        from django.utils import timezone
        queryset.update(recovered=True, recovered_at=timezone.now())
        self.message_user(request, f"{queryset.count()} carts marked as recovered.")
    mark_as_recovered.short_description = "Mark selected as recovered"


@admin.register(UserScore)
class UserScoreAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'composite_score', 'score_tier',
        'abandonment_score', 'value_score', 'conversion_score',
        'hesitation_score', 'discount_eligibility', 'last_calculated'
    ]
    list_filter = ['last_calculated', 'discount_eligibility']
    search_fields = ['user__email', 'promo_code']
    readonly_fields = [
        'abandonment_score', 'value_score', 'conversion_score',
        'hesitation_score', 'composite_score', 'last_calculated'
    ]
    ordering = ['-composite_score']
    
    fieldsets = (
        ('Scoring Metrics', {
            'fields': (
                'abandonment_score', 'value_score', 
                'conversion_score', 'hesitation_score', 'composite_score'
            )
        }),
        ('Promo/Discount', {
            'fields': ('discount_eligibility', 'recommended_discount', 'promo_code'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('last_calculated',)
        }),
    )
    
    def score_tier(self, obj):
        return obj.score_tier.replace('_', ' ').title()
    score_tier.short_description = 'Tier'