from rest_framework import serializers
from .models import Report, ConversationLog, ConversationSession


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
            'current_state', 'context_data', 'conversation_history',
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