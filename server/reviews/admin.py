# reviews/admin.py
from django.contrib import admin
from .models import (
    ProductReview, SellerReview, ReviewResponse,
    ReviewHelpful, ReviewImage, ReviewFlag
)


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    fields = ['image', 'caption']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'reviewer', 'rating', 'is_verified_purchase',
        'is_approved', 'is_flagged', 'helpful_count', 'created_at'
    ]
    list_filter = [
        'rating', 'is_verified_purchase', 'is_approved', 
        'is_flagged', 'created_at'
    ]
    search_fields = ['product__title', 'reviewer__email', 'comment']
    readonly_fields = ['helpful_count', 'not_helpful_count', 'created_at', 'updated_at']
    inlines = [ReviewImageInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'reviewer', 'rating', 'title', 'comment')
        }),
        ('Detailed Ratings', {
            'fields': ('quality_rating', 'value_rating', 'accuracy_rating')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved', 'is_flagged', 'flagged_reason')
        }),
        ('Engagement', {
            'fields': ('helpful_count', 'not_helpful_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['approve_reviews', 'flag_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} reviews approved.")
    approve_reviews.short_description = "Approve selected reviews"
    
    def flag_reviews(self, request, queryset):
        queryset.update(is_flagged=True)
        self.message_user(request, f"{queryset.count()} reviews flagged.")
    flag_reviews.short_description = "Flag selected reviews"


@admin.register(SellerReview)
class SellerReviewAdmin(admin.ModelAdmin):
    list_display = [
        'seller', 'reviewer', 'product', 'rating', 
        'is_verified_transaction', 'is_approved', 'is_flagged',
        'helpful_count', 'created_at'
    ]
    list_filter = [
        'rating', 'is_verified_transaction', 'is_approved',
        'is_flagged', 'created_at'
    ]
    search_fields = ['seller__email', 'reviewer__email', 'comment']
    readonly_fields = ['helpful_count', 'not_helpful_count', 'created_at', 'updated_at']
    inlines = [ReviewImageInline]
    
    fieldsets = (
        ('Review Information', {
            'fields': ('seller', 'reviewer', 'product', 'rating', 'title', 'comment')
        }),
        ('Detailed Ratings', {
            'fields': ('communication_rating', 'reliability_rating', 'professionalism_rating')
        }),
        ('Status', {
            'fields': ('is_verified_transaction', 'is_approved', 'is_flagged', 'flagged_reason')
        }),
        ('Engagement', {
            'fields': ('helpful_count', 'not_helpful_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['approve_reviews', 'flag_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} reviews approved.")
    approve_reviews.short_description = "Approve selected reviews"
    
    def flag_reviews(self, request, queryset):
        queryset.update(is_flagged=True)
        self.message_user(request, f"{queryset.count()} reviews flagged.")
    flag_reviews.short_description = "Flag selected reviews"


@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    list_display = ['responder', 'product_review', 'seller_review', 'created_at']
    list_filter = ['created_at']
    search_fields = ['responder__email', 'response']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['user', 'product_review', 'seller_review', 'vote', 'created_at']
    list_filter = ['vote', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at']


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ['product_review', 'seller_review', 'caption', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['caption']
    readonly_fields = ['uploaded_at']


@admin.register(ReviewFlag)
class ReviewFlagAdmin(admin.ModelAdmin):
    list_display = ['flagger', 'reason', 'status', 'created_at']
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['flagger__email', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Flag Information', {
            'fields': ('product_review', 'seller_review', 'flagger', 'reason', 'description')
        }),
        ('Admin Action', {
            'fields': ('status', 'admin_notes', 'resolved_at')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    actions = ['mark_as_resolved', 'mark_as_dismissed']
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='resolved', resolved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} flags marked as resolved.")
    mark_as_resolved.short_description = "Mark selected as resolved"
    
    def mark_as_dismissed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='dismissed', resolved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} flags marked as dismissed.")
    mark_as_dismissed.short_description = "Mark selected as dismissed"