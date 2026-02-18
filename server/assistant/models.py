#server/assistant/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ConversationSession(models.Model):
    """
    CRITICAL FIELDS:
    - context: Primary field used by ContextManager for storing conversation data
    - context_data: Legacy compatibility alias
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

    LANE_CHOICES = [
        ('inbox', 'Inbox Assistant'),
        ('customer_service', 'Customer Service Assistant'),
    ]

    MODE_CHOICES = [
        ('homepage_reco', 'Homepage Recommendation Assistant'),
        ('inbox_general', 'Inbox General Assistant'),
        ('customer_service', 'Customer Service Assistant'),
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
    assistant_lane = models.CharField(
        max_length=30,
        choices=LANE_CHOICES,
        default='inbox',
        help_text="Legacy assistant lane for backward compatibility"
    )
    assistant_mode = models.CharField(
        max_length=30,
        choices=MODE_CHOICES,
        default='inbox_general',
        help_text="Canonical assistant mode for policy and routing"
    )
    is_persistent = models.BooleanField(
        default=True,
        help_text="Persistent sessions are stored and listed in inbox"
    )
    conversation_title = models.CharField(
        max_length=180,
        blank=True,
        help_text="Deterministic title generated once from first user message"
    )
    title_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when conversation title was first set"
    )
    current_state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='greeting',
        help_text="Current conversation state"
    )

                                                    
    context = models.JSONField(
        default=dict,
        encoder=DjangoJSONEncoder,
        help_text="Complete session context: history, traits, sentiment, escalation, metadata"
    )

                          
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

    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)                                  
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
        self.conversation_history.append({
            'role': role,
            'content': content,
            'timestamp': timezone.now().isoformat()
        })
        self.message_count += 1
        self.save()

    def close_session(self):
        self.current_state = 'closed'
        self.closed_at = timezone.now()
        self.save()


class Report(models.Model):
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

    REPORT_TYPE_CHOICES = [
        ('dispute', 'Dispute'),
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
        ('suggestion', 'Suggestion'),
        ('bug', 'Bug Report'),
        ('scam', 'Scam Report'),
        ('other', 'Other'),
    ]

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

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default='other',
        help_text="Type of report (dispute, feedback, complaint, etc.)"
    )

    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Report category (scam, payment, product, service, etc.)"
    )

    ai_generated_draft = models.TextField(
        blank=True,
        help_text="AI-generated draft message for user to use when contacting seller/support"
    )

    contact_preference = models.CharField(
        max_length=20,
        choices=CONTACT_PREFERENCE_CHOICES,
        default='none',
        help_text="User's preferred platform for contacting seller"
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
            models.Index(fields=['report_type', '-created_at']),
        ]

    def __str__(self):
        return f"Report #{self.id} - {self.report_type} - {self.severity} - {self.status}"


class DisputeMedia(models.Model):
    MEDIA_TYPE_IMAGE = 'image'
    MEDIA_TYPE_AUDIO = 'audio'

    MEDIA_TYPE_CHOICES = [
        (MEDIA_TYPE_IMAGE, 'Image'),
        (MEDIA_TYPE_AUDIO, 'Audio'),
    ]

    STORAGE_LOCAL = 'local'
    STORAGE_OBJECT = 'object_storage'

    STORAGE_CHOICES = [
        (STORAGE_LOCAL, 'Local Disk'),
        (STORAGE_OBJECT, 'Object Storage'),
    ]

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='evidence_files'
    )
    VALIDATION_PENDING = 'pending'
    VALIDATION_APPROVED = 'approved'
    VALIDATION_REJECTED = 'rejected'

    VALIDATION_STATUS_CHOICES = [
        (VALIDATION_PENDING, 'Pending'),
        (VALIDATION_APPROVED, 'Approved'),
        (VALIDATION_REJECTED, 'Rejected'),
    ]

    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(upload_to='assistant/dispute_evidence/%Y/%m/%d')
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)

    source_storage = models.CharField(
        max_length=30,
        choices=STORAGE_CHOICES,
        default=STORAGE_LOCAL,
        help_text='Storage backend used for this file'
    )
    storage_key = models.CharField(
        max_length=500,
        blank=True,
        help_text='Abstract storage key/path for future object storage migration'
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_dispute_media'
    )

    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS_CHOICES,
        default=VALIDATION_PENDING,
        db_index=True
    )
    validation_reason = models.TextField(blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    retention_expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report', '-created_at']),
            models.Index(fields=['media_type', '-created_at']),
            models.Index(fields=['retention_expires_at', 'is_deleted']),
            models.Index(fields=['report', 'validation_status', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['report', 'media_type'],
                condition=models.Q(media_type='audio', is_deleted=False),
                name='assistant_single_active_audio_per_report'
            )
        ]

    def __str__(self):
        return f"DisputeMedia #{self.id} ({self.media_type}) - report:{self.report_id}"

    def refresh_retention(self):
        if self.report.status in {'resolved', 'closed'} and self.report.resolved_at:
            self.retention_expires_at = self.report.resolved_at + timedelta(days=90)

    def mark_deleted(self):
        if self.is_deleted:
            return
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])



class ConversationLog(models.Model):
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
                                                            
    anonymous_session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Anonymous session tracking for non-authenticated users"
    )
    message = models.TextField(help_text="User's original message")

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

    final_reply = models.TextField(help_text="Reply sent to user")
    confidence = models.FloatField(
        default=0.0,
        help_text="Confidence score (0-1)"
    )
    explanation = models.TextField(
        blank=True,
        help_text="Why this reply was chosen"
    )

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
            models.Index(fields=['anonymous_session_id', '-created_at']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else f"session:{self.anonymous_session_id[:8]}"
        return f"Conversation {self.id} - {user_str} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
