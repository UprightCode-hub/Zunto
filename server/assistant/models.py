#server/assistant/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from datetime import timedelta
from django.utils.crypto import get_random_string
from core.storage_backends import PrivateMediaStorage

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

    CONTEXT_TYPE_SUPPORT = 'support'
    CONTEXT_TYPE_RECOMMENDATION = 'recommendation'
    CONTEXT_TYPE_CHOICES = [
        (CONTEXT_TYPE_SUPPORT, 'Support'),
        (CONTEXT_TYPE_RECOMMENDATION, 'Recommendation'),
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

    context_type = models.CharField(
        max_length=20,
        choices=CONTEXT_TYPE_CHOICES,
        default=CONTEXT_TYPE_SUPPORT,
        help_text='Conversation context type: support or recommendation journey',
    )
    active_product = models.ForeignKey(
        'market.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_recommendation_sessions',
    )
    constraint_state = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True)
    intent_state = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True)
    drift_flag = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

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
            models.Index(fields=['context_type', '-last_activity']),
            models.Index(fields=['assistant_mode', 'context_type', '-last_activity']),
        ]

    def __str__(self):
        if self.user:
            user_str = (self.user.get_full_name() or self.user.email or '').strip()
        else:
            user_str = self.user_name or f"session:{self.session_id[:8]}"
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


class DisputeTicket(models.Model):
    SELLER_TYPE_VERIFIED = 'verified'
    SELLER_TYPE_UNVERIFIED = 'unverified'
    SELLER_TYPE_CHOICES = [
        (SELLER_TYPE_VERIFIED, 'Verified'),
        (SELLER_TYPE_UNVERIFIED, 'Unverified'),
    ]

    STATUS_OPEN = 'OPEN'
    STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    STATUS_RESOLVED_APPROVED = 'RESOLVED_APPROVED'
    STATUS_RESOLVED_DENIED = 'RESOLVED_DENIED'
    STATUS_CLOSED = 'CLOSED'
    STATUS_ESCALATED = 'ESCALATED'
    STATUS_UNDER_SENIOR_REVIEW = 'UNDER_SENIOR_REVIEW'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_RESOLVED_APPROVED, 'Resolved Approved'),
        (STATUS_RESOLVED_DENIED, 'Resolved Denied'),
        (STATUS_CLOSED, 'Closed'),
        (STATUS_ESCALATED, 'Escalated'),
        (STATUS_UNDER_SENIOR_REVIEW, 'Under Senior Review'),
    ]

    ESCROW_NOT_APPLICABLE = 'not_applicable'
    ESCROW_FROZEN = 'frozen'
    ESCROW_RELEASED_TO_BUYER = 'released_to_buyer'
    ESCROW_RELEASED_TO_SELLER = 'released_to_seller'
    ESCROW_STATE_CHOICES = [
        (ESCROW_NOT_APPLICABLE, 'Not Applicable'),
        (ESCROW_FROZEN, 'Frozen'),
        (ESCROW_RELEASED_TO_BUYER, 'Released to Buyer'),
        (ESCROW_RELEASED_TO_SELLER, 'Released to Seller'),
    ]

    ticket_id = models.CharField(max_length=20, unique=True, db_index=True)
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dispute_tickets_opened'
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dispute_tickets_received'
    )
    legacy_report = models.OneToOneField(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispute_ticket',
        help_text='Legacy Report mapping for backward-compatible dispute flow'
    )
    seller_type = models.CharField(max_length=20, choices=SELLER_TYPE_CHOICES)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispute_tickets'
    )
    product = models.ForeignKey(
        'market.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispute_tickets'
    )
    dispute_category = models.CharField(max_length=100)
    description = models.TextField()
    desired_resolution = models.CharField(max_length=255, blank=True)
    evidence_links = models.JSONField(default=list, encoder=DjangoJSONEncoder, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    ai_recommendation = models.TextField(null=True, blank=True)
    ai_recommended_decision = models.CharField(max_length=20, null=True, blank=True)
    ai_confidence_score = models.FloatField(null=True, blank=True)
    ai_risk_score = models.FloatField(null=True, blank=True)
    ai_reasoning_summary = models.TextField(null=True, blank=True)
    ai_policy_flags = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True)
    ai_evaluated_at = models.DateTimeField(null=True, blank=True)
    admin_decision = models.TextField(null=True, blank=True)
    admin_decision_reason = models.TextField(null=True, blank=True)
    admin_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispute_tickets_decided'
    )
    admin_decision_at = models.DateTimeField(null=True, blank=True)
    ai_admin_agreement = models.BooleanField(null=True, blank=True)
    ai_override_flag = models.BooleanField(default=False)
    ai_override_reason = models.TextField(null=True, blank=True)
    ai_evaluated_against_admin_at = models.DateTimeField(null=True, blank=True)
    risk_score = models.FloatField(null=True, blank=True)
    escrow_state = models.CharField(max_length=30, choices=ESCROW_STATE_CHOICES, default=ESCROW_NOT_APPLICABLE)
    escrow_frozen_at = models.DateTimeField(null=True, blank=True)
    escrow_released_at = models.DateTimeField(null=True, blank=True)
    escrow_executed_at = models.DateTimeField(null=True, blank=True)
    escrow_execution_locked = models.BooleanField(default=False)
    escrow_execution_reference = models.CharField(max_length=120, blank=True)
    escrow_execution_meta = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True)
    seller_response_due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_id']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['seller_type', '-created_at']),
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['seller', '-created_at']),
        ]

    def __str__(self):
        return f"{self.ticket_id} ({self.status})"

    @classmethod
    def generate_ticket_id(cls) -> str:
        year = timezone.now().year
        for _ in range(10):
            suffix = get_random_string(4, allowed_chars='0123456789')
            candidate = f"TICKET-{year}-{suffix}"
            if not cls.objects.filter(ticket_id=candidate).exists():
                return candidate
        raise ValueError('Unable to generate unique ticket id')


class DisputeTicketCommunication(models.Model):
    CHANNEL_CHAT = 'chat'
    CHANNEL_EMAIL = 'email'
    CHANNEL_SYSTEM = 'system'
    CHANNEL_CHOICES = [
        (CHANNEL_CHAT, 'Chat'),
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SYSTEM, 'System'),
    ]

    SENDER_BUYER = 'buyer'
    SENDER_SELLER = 'seller'
    SENDER_AI = 'ai'
    SENDER_ADMIN = 'admin'
    SENDER_SYSTEM = 'system'
    SENDER_CHOICES = [
        (SENDER_BUYER, 'Buyer'),
        (SENDER_SELLER, 'Seller'),
        (SENDER_AI, 'AI'),
        (SENDER_ADMIN, 'Admin'),
        (SENDER_SYSTEM, 'System'),
    ]

    ticket = models.ForeignKey(
        DisputeTicket,
        on_delete=models.CASCADE,
        related_name='communications'
    )
    sender_role = models.CharField(max_length=20, choices=SENDER_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_SYSTEM)
    message_type = models.CharField(max_length=40, default='note')
    body = models.TextField(blank=True)
    meta = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at']),
            models.Index(fields=['sender_role', 'created_at']),
        ]

    def __str__(self):
        return f"{self.ticket.ticket_id} {self.sender_role}:{self.message_type}"


class DisputeAuditLog(models.Model):
    ACTION_STATUS_CHANGE = 'STATUS_CHANGE'
    ACTION_ESCROW_EXECUTION = 'ESCROW_EXECUTION'
    ACTION_ESCALATION_TRIGGER = 'ESCALATION_TRIGGER'
    ACTION_ADMIN_DECISION = 'ADMIN_DECISION'
    ACTION_AI_RECOMMENDATION = 'AI_RECOMMENDATION'
    ACTION_AI_OVERRIDE_FLAGGED = 'AI_OVERRIDE_FLAGGED'

    ACTION_CHOICES = [
        (ACTION_STATUS_CHANGE, 'Status Change'),
        (ACTION_ESCROW_EXECUTION, 'Escrow Execution'),
        (ACTION_ESCALATION_TRIGGER, 'Escalation Trigger'),
        (ACTION_ADMIN_DECISION, 'Admin Decision'),
        (ACTION_AI_RECOMMENDATION, 'AI Recommendation'),
        (ACTION_AI_OVERRIDE_FLAGGED, 'AI Override Flagged'),
    ]

    dispute_ticket = models.ForeignKey(
        DisputeTicket,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    action_type = models.CharField(max_length=40, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispute_audit_logs',
    )
    previous_value = models.JSONField(default=dict, encoder=DjangoJSONEncoder, null=True, blank=True)
    new_value = models.JSONField(default=dict, encoder=DjangoJSONEncoder, null=True, blank=True)
    metadata = models.JSONField(default=dict, encoder=DjangoJSONEncoder, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dispute_ticket', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.dispute_ticket.ticket_id}:{self.action_type}"




class UserBehaviorProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='behavior_profile'
    )
    ai_search_count = models.PositiveIntegerField(default=0)
    normal_search_count = models.PositiveIntegerField(default=0)
    dominant_categories = models.JSONField(default=list, encoder=DjangoJSONEncoder, blank=True)
    avg_budget_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    avg_budget_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ai_conversion_rate = models.FloatField(default=0.0)
    normal_conversion_rate = models.FloatField(default=0.0)
    switch_frequency = models.FloatField(default=0.0)
    ai_high_intent_no_conversion = models.BooleanField(default=False)
    last_aggregated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-last_aggregated_at']),
            models.Index(fields=['ai_high_intent_no_conversion', '-updated_at']),
        ]

    def __str__(self):
        return f"BehaviorProfile<{self.user_id}>"


class RecommendationDemandGap(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendation_demand_gaps'
    )
    requested_category = models.CharField(max_length=120, blank=True)
    requested_attributes = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True)
    user_location = models.CharField(max_length=200, blank=True)
    frequency = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen_at']
        indexes = [
            models.Index(fields=['requested_category', '-last_seen_at']),
            models.Index(fields=['frequency', '-last_seen_at']),
            models.Index(
                fields=['requested_category', 'user', 'user_location'],
                name='demand_match_idx',
            ),
        ]

    def __str__(self):
        return f"DemandGap<{self.requested_category or 'unknown'} x{self.frequency}>"


class AIRecommendationFeedback(models.Model):
    FEEDBACK_HELPFUL = 'helpful'
    FEEDBACK_NOT_RELEVANT = 'not_relevant'
    FEEDBACK_TOO_EXPENSIVE = 'too_expensive'
    FEEDBACK_WRONG_LOCATION = 'wrong_location'
    FEEDBACK_WRONG_CONDITION = 'wrong_condition'
    FEEDBACK_WRONG_PRODUCT_TYPE = 'wrong_product_type'
    FEEDBACK_CHOICES = [
        (FEEDBACK_HELPFUL, 'Helpful'),
        (FEEDBACK_NOT_RELEVANT, 'Not relevant'),
        (FEEDBACK_TOO_EXPENSIVE, 'Too expensive'),
        (FEEDBACK_WRONG_LOCATION, 'Wrong location'),
        (FEEDBACK_WRONG_CONDITION, 'Wrong condition'),
        (FEEDBACK_WRONG_PRODUCT_TYPE, 'Wrong product type'),
    ]

    SOURCE_HOMEPAGE_RECO = 'homepage_reco'
    SOURCE_CHOICES = [
        (SOURCE_HOMEPAGE_RECO, 'Homepage recommendation'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_recommendation_feedback',
    )
    session = models.ForeignKey(
        ConversationSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendation_feedback',
    )
    selected_product = models.ForeignKey(
        'market.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_recommendation_feedback',
    )
    feedback_type = models.CharField(max_length=40, choices=FEEDBACK_CHOICES, db_index=True)
    prompt = models.TextField(blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=40, choices=SOURCE_CHOICES, default=SOURCE_HOMEPAGE_RECO)
    recommended_products = models.JSONField(default=list, encoder=DjangoJSONEncoder, blank=True)
    recommendation_metadata = models.JSONField(default=dict, encoder=DjangoJSONEncoder, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['feedback_type', '-created_at']),
            models.Index(fields=['source', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['selected_product', '-created_at']),
        ]

    def __str__(self):
        product = self.selected_product_id or 'no-product'
        return f"AIRecoFeedback<{self.feedback_type}:{product}>"




class DemandCluster(models.Model):
    category = models.ForeignKey(
        'market.Category',
        on_delete=models.CASCADE,
        related_name='demand_clusters',
    )
    location = models.ForeignKey(
        'market.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demand_clusters',
    )
    demand_count = models.IntegerField(default=0)
    last_gap_at = models.DateTimeField(null=True, blank=True)
    hot_score = models.FloatField(default=0.0)
    is_hot = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-hot_score', '-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['category', 'location'], name='unique_demand_cluster_category_location'),
        ]
        indexes = [
            models.Index(fields=['is_hot', '-hot_score']),
            models.Index(fields=['category', 'location']),
        ]

    def __str__(self):
        category_name = self.category.name if self.category_id else 'unknown'
        location_name = str(self.location) if self.location_id else 'any'
        return f"DemandCluster<{category_name}@{location_name} d={self.demand_count}>"


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
    file = models.FileField(upload_to='disputes/%Y/%m/%d', storage=PrivateMediaStorage())
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
        if self.user:
            user_str = (self.user.get_full_name() or self.user.email or '').strip()
        else:
            user_str = f"session:{self.anonymous_session_id[:8]}"
        return f"Conversation {self.id} - {user_str} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
