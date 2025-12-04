from django.db import models
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()


class Report(models.Model):
    """User-submitted reports for issues requiring human review."""
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewing', 'Reviewing'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assistant_reports'
    )
    message = models.TextField(
        help_text="Original user message that triggered the report"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='medium'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    meta = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        help_text="Additional context: matched_rule, conversation_log_id, etc."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports'
    )
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', 'severity']),
        ]
    
    def __str__(self):
        return f"Report #{self.id} - {self.severity} - {self.status}"


class ConversationLog(models.Model):
    """Complete log of all assistant interactions for analysis and tuning."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assistant_conversations'
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Anonymous session tracking for non-authenticated users"
    )
    message = models.TextField(help_text="User's original message")
    
    # Processing results
    rule_hit = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        help_text="Matched rule: {id, action, severity, matched_phrase}"
    )
    faq_hit = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        help_text="FAQ match: {id, question, answer, score, method}"
    )
    llm_response = models.TextField(
        blank=True,
        help_text="Raw LLM output if used"
    )
    llm_meta = models.JSONField(
        null=True,
        blank=True,
        encoder=DjangoJSONEncoder,
        help_text="LLM metadata: tokens, time_ms, model_name"
    )
    
    # Final output
    final_reply = models.TextField(help_text="Reply sent to user")
    confidence = models.FloatField(
        default=0.0,
        help_text="Confidence score (0-1)"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Why this reply was chosen"
    )
    
    # Metadata
    processing_time_ms = models.IntegerField(
        default=0,
        help_text="Total processing time in milliseconds"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['session_id', '-created_at']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else f"session:{self.session_id[:8]}"
        return f"Conversation {self.id} - {user_str} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"