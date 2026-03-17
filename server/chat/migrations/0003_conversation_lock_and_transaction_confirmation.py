# Generated manually for Phase 2 confirmation workflow

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_remove_message_message_has_content_or_attachment_and_more'),
        ('market', '0002_alter_product_deleted_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='is_locked',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='conversation',
            name='locked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversation',
            name='lock_reason',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['is_locked', '-updated_at'], name='chat_conver_is_lock_534ef9_idx'),
        ),
        migrations.CreateModel(
            name='TransactionConfirmation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('seller_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('buyer_confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed')], db_index=True, default='pending', max_length=20)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buyer_confirmations', to=settings.AUTH_USER_MODEL)),
                ('conversation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='transaction_confirmation', to='chat.conversation')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transaction_confirmations', to='market.product')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seller_confirmations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'chat_transaction_confirmations',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='transactionconfirmation',
            index=models.Index(fields=['buyer', 'status'], name='chat_transa_buyer_i_b2b296_idx'),
        ),
        migrations.AddIndex(
            model_name='transactionconfirmation',
            index=models.Index(fields=['seller', 'status'], name='chat_transa_seller__17d371_idx'),
        ),
        migrations.AddIndex(
            model_name='transactionconfirmation',
            index=models.Index(fields=['product', 'status'], name='chat_transa_product_070f6e_idx'),
        ),
        migrations.AddIndex(
            model_name='transactionconfirmation',
            index=models.Index(fields=['status', '-updated_at'], name='chat_transa_status_2084fe_idx'),
        ),
    ]
