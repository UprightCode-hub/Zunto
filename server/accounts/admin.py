#server/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import User, VerificationCode


class VerificationStatusFilter(admin.SimpleListFilter):
    """Custom filter for verification status"""
    title = _('verification status')
    parameter_name = 'verification'

    def lookups(self, request, model_admin):
        return (
            ('all_verified', _('All Verified')),
            ('email_only', _('Email Only')),
            ('phone_only', _('Phone Only')),
            ('none', _('Not Verified')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'all_verified':
            return queryset.filter(is_verified=True, is_phone_verified=True)
        elif self.value() == 'email_only':
            return queryset.filter(is_verified=True, is_phone_verified=False)
        elif self.value() == 'phone_only':
            return queryset.filter(is_verified=False, is_phone_verified=True)
        elif self.value() == 'none':
            return queryset.filter(is_verified=False, is_phone_verified=False)


class RecentUsersFilter(admin.SimpleListFilter):
    """Filter users by registration date"""
    title = _('registration date')
    parameter_name = 'registered'

    def lookups(self, request, model_admin):
        return (
            ('today', _('Today')),
            ('week', _('This week')),
            ('month', _('This month')),
            ('year', _('This year')),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'today':
            return queryset.filter(created_at__date=now.date())
        elif self.value() == 'week':
            start_week = now - timedelta(days=7)
            return queryset.filter(created_at__gte=start_week)
        elif self.value() == 'month':
            start_month = now - timedelta(days=30)
            return queryset.filter(created_at__gte=start_month)
        elif self.value() == 'year':
            start_year = now - timedelta(days=365)
            return queryset.filter(created_at__gte=start_year)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 
        'full_name_display', 
        'role_badge', 
        'verification_status', 
        'is_active', 
        'created_at'
    ]
    list_filter = [
        'role', 
        VerificationStatusFilter,
        RecentUsersFilter,
        'is_active', 
        'is_staff',
        'is_suspended',
        'created_at'
    ]
    search_fields = ['email', 'first_name', 'last_name', 'phone', 'nin', 'bvn']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
                    
    actions = ['verify_users', 'suspend_users', 'activate_users']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'phone', 'profile_picture', 'bio')
        }),
        (_('Role & Verification'), {
            'fields': ('role', 'is_verified', 'is_phone_verified', 'nin', 'bvn')
        }),
        (_('Address'), {
            'fields': ('address', 'city', 'state', 'country'),
            'classes': ('collapse',)                       
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 
                'is_staff', 
                'is_superuser', 
                'is_suspended', 
                'suspension_reason'
            )
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 
                'password1', 
                'password2', 
                'first_name', 
                'last_name', 
                'role'
            ),
        }),
    )
    
                            
    @admin.display(description='Full Name')
    def full_name_display(self, obj):
        """Display full name or email if name not set"""
        full_name = obj.get_full_name()
        return full_name if full_name else format_html(
            '<em style="color: #999;">{}</em>', 
            'Not set'
        )
    
    @admin.display(description='Role')
    def role_badge(self, obj):
        """Display role as colored badge"""
        colors = {
            'buyer': '#28a745',
            'seller': '#007bff',
            'admin': '#dc3545',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.role.upper()
        )
    
    @admin.display(description='Verification')
    def verification_status(self, obj):
        """Display verification status with icons"""
        email_icon = '✓' if obj.is_verified else '✗'
        phone_icon = '✓' if obj.is_phone_verified else '✗'
        email_color = '#28a745' if obj.is_verified else '#dc3545'
        phone_color = '#28a745' if obj.is_phone_verified else '#dc3545'
        
        return format_html(
            'Email: <span style="color: {}; font-weight: bold;">{}</span> | '
            'Phone: <span style="color: {}; font-weight: bold;">{}</span>',
            email_color, email_icon,
            phone_color, phone_icon
        )
    
                    
    @admin.action(description='Verify selected users (email)')
    def verify_users(self, request, queryset):
        """Mark selected users as verified"""
        updated = queryset.update(is_verified=True)
        self.message_user(
            request, 
            f'{updated} user(s) successfully verified.'
        )
    
    @admin.action(description='Suspend selected users')
    def suspend_users(self, request, queryset):
        """Suspend selected users"""
        updated = queryset.update(
            is_suspended=True, 
            suspension_reason='Suspended by admin'
        )
        self.message_user(
            request, 
            f'{updated} user(s) suspended.',
            level='warning'
        )
    
    @admin.action(description='Activate selected users')
    def activate_users(self, request, queryset):
        """Activate suspended users"""
        updated = queryset.update(
            is_active=True, 
            is_suspended=False, 
            suspension_reason=''
        )
        self.message_user(
            request, 
            f'{updated} user(s) activated.'
        )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related if needed"""
        qs = super().get_queryset(request)
                                    
        return qs


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ['get_user_email', 'code_type', 'code', 'is_used', 'created_at', 'expires_at']
    list_filter = ['code_type', 'is_used', 'created_at']
    search_fields = ['user_email', 'code', 'userfirst_name', 'user_last_name']
    readonly_fields = ['created_at', 'id']
    date_hierarchy = 'created_at'
    
    @admin.display(description='User Email', ordering='user__email')
    def get_user_email(self, obj):
        """Safely get user email"""
        try:
            return obj.user.email
        except:
            return 'N/A'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
