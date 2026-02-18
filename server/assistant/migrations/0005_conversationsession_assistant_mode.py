from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0004_disputemedia_validation_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversationsession',
            name='assistant_mode',
            field=models.CharField(
                choices=[
                    ('homepage_reco', 'Homepage Recommendation Assistant'),
                    ('inbox_general', 'Inbox General Assistant'),
                    ('customer_service', 'Customer Service Assistant'),
                ],
                default='inbox_general',
                help_text='Canonical assistant mode for policy and routing',
                max_length=30,
            ),
        ),
    ]
