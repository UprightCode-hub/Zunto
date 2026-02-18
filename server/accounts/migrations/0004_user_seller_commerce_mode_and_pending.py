from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_pendingregistration'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingregistration',
            name='seller_commerce_mode',
            field=models.CharField(
                choices=[
                    ('direct', 'Direct Seller (buyer pays seller directly)'),
                    ('managed', 'Managed by Zunto (buyer pays Zunto)'),
                ],
                default='direct',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='seller_commerce_mode',
            field=models.CharField(
                choices=[
                    ('direct', 'Direct Seller (buyer pays seller directly)'),
                    ('managed', 'Managed by Zunto (buyer pays Zunto)'),
                ],
                default='direct',
                help_text='Direct sellers handle payment off-platform. Managed sellers use Zunto payment, shipping, and refunds.',
                max_length=20,
            ),
        ),
    ]
