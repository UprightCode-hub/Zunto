from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0012_disputeticket_escalation_and_ai_admin_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DisputeAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('STATUS_CHANGE', 'Status Change'), ('ESCROW_EXECUTION', 'Escrow Execution'), ('ESCALATION_TRIGGER', 'Escalation Trigger'), ('ADMIN_DECISION', 'Admin Decision'), ('AI_RECOMMENDATION', 'AI Recommendation'), ('AI_OVERRIDE_FLAGGED', 'AI Override Flagged')], max_length=40)),
                ('previous_value', models.JSONField(blank=True, default=dict, encoder=DjangoJSONEncoder, null=True)),
                ('new_value', models.JSONField(blank=True, default=dict, encoder=DjangoJSONEncoder, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict, encoder=DjangoJSONEncoder, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dispute_ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_logs', to='assistant.disputeticket')),
                ('performed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispute_audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='disputeauditlog',
            index=models.Index(fields=['dispute_ticket', '-created_at'], name='assistant_d_dispute_9969c7_idx'),
        ),
        migrations.AddIndex(
            model_name='disputeauditlog',
            index=models.Index(fields=['action_type', '-created_at'], name='assistant_d_action__4b92d4_idx'),
        ),
    ]
