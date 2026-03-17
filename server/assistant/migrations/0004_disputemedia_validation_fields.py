from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0003_disputemedia'),
    ]

    operations = [
        migrations.AddField(
            model_name='disputemedia',
            name='validated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputemedia',
            name='validation_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='disputemedia',
            name='validation_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=20),
        ),
        migrations.AddIndex(
            model_name='disputemedia',
            index=models.Index(fields=['report', 'validation_status', '-created_at'], name='assistant_di_report__ea97f2_idx'),
        ),
        migrations.AddConstraint(
            model_name='disputemedia',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False), ('media_type', 'audio')), fields=('report', 'media_type'), name='assistant_single_active_audio_per_report'),
        ),
    ]
