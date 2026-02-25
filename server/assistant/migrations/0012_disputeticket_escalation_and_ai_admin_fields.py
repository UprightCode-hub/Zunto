from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0011_disputeticket_escrow_execution_lock_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='disputeticket',
            name='ai_admin_agreement',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_evaluated_against_admin_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_override_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_override_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='disputeticket',
            name='status',
            field=models.CharField(
                choices=[
                    ('OPEN', 'Open'),
                    ('UNDER_REVIEW', 'Under Review'),
                    ('RESOLVED_APPROVED', 'Resolved Approved'),
                    ('RESOLVED_DENIED', 'Resolved Denied'),
                    ('CLOSED', 'Closed'),
                    ('ESCALATED', 'Escalated'),
                    ('UNDER_SENIOR_REVIEW', 'Under Senior Review'),
                ],
                default='OPEN',
                max_length=20,
            ),
        ),
    ]
