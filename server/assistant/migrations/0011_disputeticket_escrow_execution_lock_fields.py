from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0010_disputeticket_ai_recommendation_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='disputeticket',
            name='escrow_executed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='escrow_execution_locked',
            field=models.BooleanField(default=False),
        ),
    ]
