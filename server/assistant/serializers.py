#server/assistant/serializers.py
from rest_framework import serializers
from .models import (
    Report,
    ConversationLog,
    ConversationSession,
    DisputeMedia,
    DisputeTicket,
    DisputeTicketCommunication,
)


class AskRequestSerializer(serializers.Serializer):
    """Input serializer for assistant query."""
    message = serializers.CharField(
        max_length=2000,
        required=True,
        help_text="User's question or message"
    )
    user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Optional user ID for authenticated requests"
    )
    session_id = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        help_text="Session ID for anonymous users"
    )


class FAQHitSerializer(serializers.Serializer):
    """FAQ match result."""
    id = serializers.IntegerField()
    question = serializers.CharField()
    answer = serializers.CharField()
    score = serializers.FloatField()
    method = serializers.CharField()


class RuleHitSerializer(serializers.Serializer):
    """Rule match result."""
    id = serializers.CharField()
    action = serializers.CharField()
    severity = serializers.CharField()
    matched_phrase = serializers.CharField()


class LLMResultSerializer(serializers.Serializer):
    """LLM processing result."""
    used = serializers.BooleanField()
    text = serializers.CharField(required=False, allow_null=True)
    meta = serializers.DictField(required=False, allow_null=True)


class AskResponseSerializer(serializers.Serializer):
    """Response serializer for assistant query."""
    faq = FAQHitSerializer(required=False, allow_null=True)
    rule = RuleHitSerializer(required=False, allow_null=True)
    llm = LLMResultSerializer(required=False, allow_null=True)
    reply = serializers.CharField()
    confidence = serializers.FloatField()
    explanation = serializers.CharField()


class ConversationSessionSerializer(serializers.ModelSerializer):
    """Serializer for conversation sessions."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationSession
        fields = [
            'id', 'session_id', 'user', 'user_username', 'user_name',
            'assistant_lane', 'assistant_mode', 'is_persistent', 'conversation_title', 'title_generated_at',
            'current_state', 'context_type', 'active_product', 'constraint_state', 'intent_state', 'drift_flag', 'completed_at',
            'context_data', 'conversation_history',
            'message_count', 'sentiment_score', 'satisfaction_score',
            'escalation_level', 'is_escalated', 'created_at',
            'last_activity', 'closed_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'last_activity']
    
    def get_is_active(self, obj):
        return obj.is_active()


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reports."""
    
    class Meta:
        model = Report
        fields = ['message', 'severity', 'meta', 'session']
        extra_kwargs = {
            'severity': {'required': False},
            'meta': {'required': False},
            'session': {'required': False},
        }


class ReportSerializer(serializers.ModelSerializer):
    """Full report serializer."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    session_id = serializers.CharField(source='session.session_id', read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'user', 'user_username', 'session', 'session_id',
            'message', 'severity', 'status', 'meta', 'created_at',
            'resolved_at', 'admin_notes'
        ]
        read_only_fields = ['id', 'created_at', 'resolved_at']


class ConversationLogSerializer(serializers.ModelSerializer):
    """Serializer for conversation logs (admin only)."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    session_full_id = serializers.CharField(source='session.session_id', read_only=True)
    
    class Meta:
        model = ConversationLog
        fields = '__all__'
        read_only_fields = ['id', 'created_at']

class DisputeMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeMedia
        fields = [
            'id', 'report', 'media_type', 'file', 'original_filename', 'mime_type',
            'file_size', 'source_storage', 'storage_key', 'uploaded_by',
            'validation_status', 'validation_reason', 'validated_at',
            'retention_expires_at', 'is_deleted', 'deleted_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'source_storage', 'storage_key', 'uploaded_by',
            'validation_status', 'validation_reason', 'validated_at',
            'retention_expires_at', 'is_deleted', 'deleted_at', 'created_at'
        ]


class DisputeTicketCreateSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(required=False, allow_null=True)
    product_id = serializers.UUIDField(required=False, allow_null=True)
    dispute_category = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=5000)
    desired_resolution = serializers.CharField(max_length=255)
    evidence = serializers.ListField(
        child=serializers.CharField(max_length=1000),
        required=False,
        allow_empty=True,
    )


class DisputeTicketCommunicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeTicketCommunication
        fields = ['id', 'sender_role', 'channel', 'message_type', 'body', 'meta', 'created_at']


class DisputeTicketSerializer(serializers.ModelSerializer):
    buyer_id = serializers.UUIDField(source='buyer.id', read_only=True)
    seller_id = serializers.UUIDField(source='seller.id', read_only=True)
    order_id = serializers.UUIDField(source='order.id', read_only=True)
    product_id = serializers.UUIDField(source='product.id', read_only=True)
    evidence_links = serializers.ListField(child=serializers.CharField(), read_only=True)
    communications = DisputeTicketCommunicationSerializer(many=True, read_only=True)

    class Meta:
        model = DisputeTicket
        fields = [
            'ticket_id',
            'buyer_id',
            'seller_id',
            'seller_type',
            'order_id',
            'product_id',
            'dispute_category',
            'description',
            'desired_resolution',
            'evidence_links',
            'status',
            'ai_recommendation',
            'ai_recommended_decision',
            'ai_confidence_score',
            'ai_risk_score',
            'ai_reasoning_summary',
            'ai_policy_flags',
            'ai_evaluated_at',
            'admin_decision',
            'admin_decision_reason',
            'admin_user',
            'admin_decision_at',
            'ai_admin_agreement',
            'ai_override_flag',
            'ai_override_reason',
            'ai_evaluated_against_admin_at',
            'risk_score',
            'escrow_state',
            'escrow_frozen_at',
            'escrow_released_at',
            'escrow_executed_at',
            'escrow_execution_locked',
            'escrow_execution_reference',
            'escrow_execution_meta',
            'seller_response_due_at',
            'created_at',
            'updated_at',
            'communications',
        ]


class DisputeTicketAdminDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            DisputeTicket.STATUS_UNDER_REVIEW,
            DisputeTicket.STATUS_RESOLVED_APPROVED,
            DisputeTicket.STATUS_RESOLVED_DENIED,
            DisputeTicket.STATUS_CLOSED,
        ]
    )
    admin_decision = serializers.CharField(max_length=5000)
    admin_decision_reason = serializers.CharField(max_length=5000, required=False, allow_blank=True)




class LogDemandGapRequestSerializer(serializers.Serializer):
    raw_query = serializers.CharField(max_length=2000, required=True, allow_blank=False)
    filters = serializers.DictField(required=True)
    source = serializers.ChoiceField(choices=['homepage_reco', 'grid_search', 'future_use'])


class LogDemandGapResponseSerializer(serializers.Serializer):
    logged = serializers.BooleanField(required=True)

class TranslateSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=2000, required=True)


class TranslateSearchResponseSerializer(serializers.Serializer):
    filters = serializers.DictField(required=True)
    refined_query = serializers.CharField(required=True, allow_blank=True)
    confidence = serializers.FloatField(required=True)

    def validate_filters(self, value):
        allowed_keys = {
            'search',
            'category',
            'condition',
            'min_price',
            'max_price',
            'is_negotiable',
            'verified_product',
            'verified_seller',
            'ordering',
        }

        unknown = set(value.keys()) - allowed_keys
        if unknown:
            raise serializers.ValidationError(f'Unsupported filter keys: {sorted(unknown)}')

        return value


class HotDemandClusterSerializer(serializers.Serializer):
    category = serializers.CharField(required=True)
    location = serializers.CharField(required=True, allow_blank=True)
    hot_score = serializers.FloatField(required=True)
