#server/assistant/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Report,
    ConversationLog,
    DisputeTicket,
    DisputeTicketCommunication,
    DisputeAuditLog,
    UserBehaviorProfile,
    RecommendationDemandGap,
)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'severity_badge', 'status_badge', 'created_at', 'resolved_at']
    list_filter = ['severity', 'status', 'created_at']
    search_fields = ['message', 'admin_notes', 'user__username']
    readonly_fields = ['created_at', 'meta']

    def severity_badge(self, obj):
        colors = {'low': '#28a745', 'medium': '#ffc107', 'high': '#fd7e14', 'critical': '#dc3545'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.severity, '#6c757d'),
            obj.get_severity_display(),
        )

    def status_badge(self, obj):
        colors = {'pending': '#dc3545', 'reviewing': '#ffc107', 'resolved': '#28a745', 'closed': '#6c757d'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display(),
        )


@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'confidence', 'created_at']
    list_filter = ['created_at', 'confidence']
    search_fields = ['message', 'final_reply', 'user__username', 'anonymous_session_id']
    readonly_fields = ['created_at', 'rule_hit', 'faq_hit', 'llm_meta']


@admin.register(DisputeTicket)
class DisputeTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'buyer', 'seller', 'seller_type', 'status', 'seller_response_due_at', 'created_at']
    list_filter = ['seller_type', 'status', 'created_at']
    search_fields = ['ticket_id', 'buyer__email', 'seller__email', 'dispute_category', 'description']
    readonly_fields = ['ticket_id', 'created_at', 'updated_at']


@admin.register(DisputeTicketCommunication)
class DisputeTicketCommunicationAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'sender_role', 'channel', 'message_type', 'created_at']
    list_filter = ['sender_role', 'channel', 'message_type']
    search_fields = ['ticket__ticket_id', 'body']


@admin.register(DisputeAuditLog)
class DisputeAuditLogAdmin(admin.ModelAdmin):
    list_display = ['dispute_ticket', 'action_type', 'performed_by', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['dispute_ticket__ticket_id', 'performed_by__email']
    readonly_fields = ['created_at']


@admin.register(UserBehaviorProfile)
class UserBehaviorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'ai_search_count', 'normal_search_count', 'ai_high_intent_no_conversion', 'last_aggregated_at']
    search_fields = ['user__email']
    list_filter = ['ai_high_intent_no_conversion']


@admin.register(RecommendationDemandGap)
class RecommendationDemandGapAdmin(admin.ModelAdmin):
    list_display = ['requested_category', 'user', 'frequency', 'user_location', 'last_seen_at']
    search_fields = ['requested_category', 'user__email', 'user_location']
    list_filter = ['requested_category']
