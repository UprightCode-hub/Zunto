#server/market/admin.py
from django.contrib import admin
from .models import (
    Category, Location, Product, ProductImage, 
    ProductVideo, Favorite, ProductView, ProductReport
)
                                        


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['state', 'city', 'area', 'is_active', 'created_at']
    list_filter = ['is_active', 'state']
    search_fields = ['state', 'city', 'area']
    ordering = ['state', 'city']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'caption', 'order', 'is_primary']


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 0
    fields = ['video', 'thumbnail', 'caption', 'duration']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'seller', 'listing_type', 'price', 'category', 
        'status', 'is_featured', 'is_boosted', 'views_count', 
        'favorites_count', 'created_at'
    ]
    list_filter = [
        'listing_type', 'status', 'is_featured', 'is_boosted', 
        'is_verified', 'category', 'condition', 'created_at'
    ]
    search_fields = ['title', 'description', 'seller__email', 'brand']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views_count', 'favorites_count', 'shares_count', 'created_at', 'updated_at']
    inlines = [ProductImageInline, ProductVideoInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('seller', 'title', 'slug', 'description', 'listing_type')
        }),
        ('Categorization', {
            'fields': ('category', 'location')
        }),
        ('Pricing & Details', {
            'fields': ('price', 'negotiable', 'condition', 'brand', 'quantity')
        }),
        ('Status & Promotion', {
            'fields': ('status', 'is_featured', 'is_boosted', 'boost_expires_at', 'is_verified', 'expires_at')
        }),
        ('Engagement Metrics', {
            'fields': ('views_count', 'favorites_count', 'shares_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['mark_as_featured', 'mark_as_verified', 'mark_as_sold']
    
    def mark_as_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f"{queryset.count()} products marked as featured.")
    mark_as_featured.short_description = "Mark selected as featured"
    
    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, f"{queryset.count()} products marked as verified.")
    mark_as_verified.short_description = "Mark selected as verified"
    
    def mark_as_sold(self, request, queryset):
        queryset.update(status='sold')
        self.message_user(request, f"{queryset.count()} products marked as sold.")
    mark_as_sold.short_description = "Mark selected as sold"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'caption', 'is_primary', 'order', 'uploaded_at']
    list_filter = ['is_primary', 'uploaded_at']
    search_fields = ['product__title', 'caption']


@admin.register(ProductVideo)
class ProductVideoAdmin(admin.ModelAdmin):
    list_display = ['product', 'caption', 'duration', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['product__title', 'caption']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'product__title']


@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['product__title', 'user__email', 'ip_address']
    readonly_fields = ['product', 'user', 'ip_address', 'user_agent', 'viewed_at']


@admin.register(ProductReport)
class ProductReportAdmin(admin.ModelAdmin):
    list_display = ['product', 'reporter', 'reason', 'status', 'created_at']
    list_filter = ['reason', 'status', 'created_at']
    search_fields = ['product__title', 'reporter__email', 'description']
    readonly_fields = ['product', 'reporter', 'created_at']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('product', 'reporter', 'reason', 'description')
        }),
        ('Status', {
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
        self.message_user(request, f"{queryset.count()} reports marked as resolved.")
    mark_as_resolved.short_description = "Mark selected as resolved"
    
    def mark_as_dismissed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='dismissed', resolved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} reports marked as dismissed.")
    mark_as_dismissed.short_description = "Mark selected as dismissed"
