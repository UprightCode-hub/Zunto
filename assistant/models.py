from django.db import models
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ConversationSession(models.Model):
    """
    Tracks user conversation sessions for context management.
    Each session maintains state and conversation history.
    
    CRITICAL FIELDS for AI modules:
    - context: Used by ContextManager for storing conversation data
    - context_data: Alias for compatibility
    - conversation_history: Message history tracking
    """
    
    STATE_CHOICES = [
        ('greeting', 'Greeting'),
        ('awaiting_name', 'Awaiting Name'),
        ('menu', 'Menu'),
        ('inquiry', 'Inquiry'),
        ('faq_mode', 'FAQ Mode'),
        ('dispute_mode', 'Dispute Mode'),
        ('feedback_mode', 'Feedback Mode'),
        ('chat_mode', 'Chat Mode'),
        ('escalation', 'Escalation'),
        ('resolution', 'Resolution'),
        ('feedback', 'Feedback'),
        ('closed', 'Closed'),
    ]
    
    session_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique session identifier (UUID)"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversation_sessions',
        help_text="Authenticated user (optional)"
    )
    user_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="User's name collected during conversation"
    )
    current_state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='greeting',
        help_text="Current conversation state"
    )
    
    # CRITICAL: Main context field used by ContextManager
    context = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        help_text="Complete session context: history, traits, sentiment, escalation, metadata"
    )
    
    # Conversation context (legacy compatibility)
    context_data = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        help_text="Session context: order_id, seller_name, issue_type, etc."
    )
    
    conversation_history = models.JSONField(
        default=list,
        encoder=DjangoJSONEncoder,
        help_text="List of messages: [{role, content, timestamp}]"
    )
    
    # Analytics
    message_count = models.IntegerField(
        default=0,
        help_text="Number of messages in this session"
    )
    sentiment_score = models.FloatField(
        default=0.5,
        help_text="Overall sentiment (0=negative, 1=positive)"
    )
    satisfaction_score = models.FloatField(
        default=0.5,
        help_text="User satisfaction estimate"
    )
    escalation_level = models.IntegerField(
        default=0,
        help_text="Escalation level (0=none, 3=critical)"
    )
    is_escalated = models.BooleanField(
        default=False,
        help_text="Whether session has been escalated to human"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)  # CRITICAL: context_manager.py expects this
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['-last_activity']),
            models.Index(fields=['user', '-last_activity']),
            models.Index(fields=['is_escalated', '-last_activity']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else self.user_name or f"session:{self.session_id[:8]}"
        return f"Session {self.session_id[:8]} - {user_str} - {self.current_state}"
    
    def is_active(self):
        """Check if session is still active (< 30 minutes since last activity)."""
        if self.closed_at:
            return False
        return timezone.now() - self.last_activity < timedelta(minutes=30)
    
    def add_message(self, role, content):
        """Add a message to conversation history."""
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': timezone.now().isoformat()
        })
        self.message_count += 1
        self.save()
    
    def close_session(self):
        """Mark session as closed."""
        self.current_state = 'closed'
        self.closed_at = timezone.now()
        self.save()


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
    
    # NEW: Report type choices for dispute_flow.py and feedback_flow.py
    REPORT_TYPE_CHOICES = [
        ('dispute', 'Dispute'),
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
        ('suggestion', 'Suggestion'),
        ('bug', 'Bug Report'),
        ('scam', 'Scam Report'),
        ('other', 'Other'),
    ]
    
    # NEW: Contact preference choices for dispute_flow.py
    CONTACT_PREFERENCE_CHOICES = [
        ('email', 'Email'),
        ('twitter', 'Twitter'),
        ('whatsapp', 'WhatsApp'),
        ('phone', 'Phone'),
        ('none', 'None'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assistant_reports'
    )
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        help_text="Associated conversation session"
    )
    message = models.TextField(
        help_text="Original user message that triggered the report"
    )
    
    # NEW FIELD #1: Report Type (Required by feedback_flow.py line 402)
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default='other',
        help_text="Type of report (dispute, feedback, complaint, etc.)"
    )
    
    # NEW FIELD #2: Category (Required by feedback_flow.py line 402)
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Report category (scam, payment, product, service, etc.)"
    )
    
    # NEW FIELD #3: AI Generated Draft (Required by dispute_flow.py line 524)
    ai_generated_draft = models.TextField(
        blank=True,
        help_text="AI-generated draft message for user to use when contacting seller/support"
    )
    
    # NEW FIELD #4: Contact Preference (Required by dispute_flow.py line 524)
    contact_preference = models.CharField(
        max_length=20,
        choices=CONTACT_PREFERENCE_CHOICES,
        default='none',
        help_text="User's preferred platform for contacting seller"
    )
    
    # Existing fields
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
        help_text="Additional context: matched_rule, conversation_log_id, seller_info, etc."
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
            models.Index(fields=['report_type', '-created_at']),  # NEW: Index for report type
        ]
    
    def __str__(self):
        return f"Report #{self.id} - {self.report_type} - {self.severity} - {self.status}"



class ConversationLog(models.Model):
    """Complete log of all assistant interactions for analysis and tuning."""
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assistant_conversations'
    )
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        help_text="Associated conversation session"
    )
    # FIXED: Renamed from session_id to anonymous_session_id to avoid clash
    anonymous_session_id = models.CharField(
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
            models.Index(fields=['anonymous_session_id', '-created_at']),  # FIXED: Updated index
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else f"session:{self.anonymous_session_id[:8]}"
        return f"Conversation {self.id} - {user_str} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"