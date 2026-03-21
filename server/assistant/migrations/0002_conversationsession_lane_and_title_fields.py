from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversationsession',
            name='assistant_lane',
            field=models.CharField(
                choices=[('inbox', 'Inbox Assistant'), ('customer_service', 'Customer Service Assistant')],
                default='inbox',
                help_text='Assistant lane for this persistent session',
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='conversation_title',
            field=models.CharField(
                blank=True,
                help_text='Deterministic title generated once from first user message',
                max_length=180,
            ),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='is_persistent',
            field=models.BooleanField(
                default=True,
                help_text='Persistent sessions are stored and listed in inbox',
            ),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='title_generated_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Timestamp when conversation title was first set',
                null=True,
            ),
        ),
    ]
