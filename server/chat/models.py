import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buying_conversations'
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='selling_conversations'
    )

    product = models.ForeignKey(
        'market.Product',
        on_delete=models.CASCADE,
        related_name='conversations'
    )

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = 'chat_conversations'
        ordering = ['-updated_at']

        unique_together = ['buyer', 'seller', 'product']

        indexes = [
            models.Index(fields=['buyer', '-updated_at']),
            models.Index(fields=['seller', '-updated_at']),
            models.Index(fields=['product']),
            models.Index(fields=['-updated_at']),
        ]

        constraints = [
            models.CheckConstraint(
                check=~models.Q(buyer=models.F('seller')),
                name='different_users_in_conversation'
            )
        ]

    def __str__(self):
        return f"Conversation: {self.buyer.get_full_name()} <-> {self.seller.get_full_name()} (Product: {self.product.title})"

    def user_is_participant(self, user):
        return user == self.buyer or user == self.seller

    def get_unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    def get_other_user(self, user):
        if user == self.buyer:
            return self.seller
        return self.buyer

    def get_last_message(self):
        return self.messages.order_by('-created_at').first()

    def mark_as_read_for_user(self, user):
        unread_messages = self.messages.filter(is_read=False).exclude(sender=user)
        count = unread_messages.update(is_read=True)
        return count


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('file', 'File'),
        ('voice', 'Voice Note'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        db_index=True
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )

    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        db_index=True
    )
    content = models.TextField(
        blank=True,
        default='[No content]'
    )

    attachment_url = models.URLField(
        max_length=500,
        blank=True,
        null=True
    )
    attachment_size = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    attachment_mime = models.CharField(
        max_length=100,
        blank=True
    )
    attachment_duration = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    waveform_data = models.JSONField(
        null=True,
        blank=True
    )

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['conversation', 'is_read']),
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        sender_name = self.sender.get_full_name()
        if self.message_type == 'text':
            preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
            return f"{sender_name}: {preview}"
        return f"{sender_name}: [{self.message_type.upper()}]"

    def save(self, *args, **kwargs):
        if self.conversation:
            self.conversation.updated_at = timezone.now()
            self.conversation.save(update_fields=['updated_at'])

        super().save(*args, **kwargs)

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @property
    def is_attachment(self):
        return bool(self.attachment_url)

    @property
    def attachment_filename(self):
        if self.attachment_url:
            return self.attachment_url.split('/')[-1]
        return None


class MessageRead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='message_reads'
    )
    read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'chat_message_reads'
        unique_together = ['message', 'user']
        ordering = ['-read_at']
        indexes = [
            models.Index(fields=['message', 'user']),
            models.Index(fields=['user', '-read_at']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} read message at {self.read_at}"


class TypingIndicator(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='typing_in'
    )
    last_typed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'chat_typing_indicators'
        unique_together = ['conversation', 'user']
        ordering = ['-last_typed_at']

    def __str__(self):
        return f"{self.user.get_full_name()} typing in {self.conversation.id}"

    def is_active(self):
        return (timezone.now() - self.last_typed_at).seconds < 5