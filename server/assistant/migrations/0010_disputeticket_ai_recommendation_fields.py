from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0009_disputeticket_escrow_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='disputeticket',
            name='ai_confidence_score',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_evaluated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_policy_flags',
            field=models.JSONField(blank=True, default=dict, encoder=DjangoJSONEncoder),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_reasoning_summary',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_recommended_decision',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='ai_risk_score',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
