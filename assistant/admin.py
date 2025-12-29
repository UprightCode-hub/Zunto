from django.contrib import admin
from django.utils.html import format_html
from .models import Report #ConversationLog


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'severity_badge', 'status_badge', 'created_at', 'resolved_at']
    list_filter = ['severity', 'status', 'created_at']
    search_fields = ['message', 'admin_notes', 'user__username']
    readonly_fields = ['created_at', 'meta']
    
    fieldsets = (
        ('Report Details', {
            'fields': ('user', 'message', 'severity', 'meta', 'created_at')
        }),
        ('Resolution', {
            'fields': ('status', 'resolved_at', 'resolved_by', 'admin_notes')
        }),
    )
    
    def severity_badge(self, obj):
        colors = {
            'low': '#28a745',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.severity, '#6c757d'),
            obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#dc3545',
            'reviewing': '#ffc107',
            'resolved': '#28a745',
            'closed': '#6c757d',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register#(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_display', 'message_preview', 'confidence', 'has_rule', 'has_faq', 'used_llm', 'created_at']
    list_filter = ['created_at', 'confidence']
    search_fields = ['message', 'final_reply', 'user__username', 'session_id']
    readonly_fields = ['created_at', 'rule_hit', 'faq_hit', 'llm_meta']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('User & Input', {
            'fields': ('user', 'session_id', 'message', 'created_at')
        }),
        ('Processing Results', {
            'fields': ('rule_hit', 'faq_hit', 'llm_response', 'llm_meta')
        }),
        ('Final Output', {
            'fields': ('final_reply', 'confidence', 'explanation', 'processing_time_ms')
        }),
    )
    
    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return f"Anonymous ({obj.session_id[:8]})"
    user_display.short_description = 'User'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def has_rule(self, obj):
        return '✓' if obj.rule_hit else '✗'
    has_rule.short_description = 'Rule'
    
    def has_faq(self, obj):
        return '✓' if obj.faq_hit else '✗'
    has_faq.short_description = 'FAQ'
    
    def used_llm(self, obj):
        return '✓' if obj.llm_response else '✗'
    used_llm.short_description = 'LLM'