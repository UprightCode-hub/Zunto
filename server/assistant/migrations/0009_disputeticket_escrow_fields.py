from django.core.serializers.json import DjangoJSONEncoder
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0008_disputeticket_admin_decision_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='disputeticket',
            name='escrow_execution_meta',
            field=models.JSONField(blank=True, default=dict, encoder=DjangoJSONEncoder),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='escrow_execution_reference',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='escrow_frozen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='escrow_released_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='escrow_state',
            field=models.CharField(
                choices=[
                    ('not_applicable', 'Not Applicable'),
                    ('frozen', 'Frozen'),
                    ('released_to_buyer', 'Released to Buyer'),
                    ('released_to_seller', 'Released to Seller'),
                ],
                default='not_applicable',
                max_length=30,
            ),
        ),
    ]
