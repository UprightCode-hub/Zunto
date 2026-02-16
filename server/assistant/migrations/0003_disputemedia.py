from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0002_conversationsession_lane_and_title_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DisputeMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('audio', 'Audio')], max_length=20)),
                ('file', models.FileField(upload_to='assistant/dispute_evidence/%Y/%m/%d')),
                ('original_filename', models.CharField(blank=True, max_length=255)),
                ('mime_type', models.CharField(blank=True, max_length=120)),
                ('file_size', models.PositiveIntegerField(default=0)),
                ('source_storage', models.CharField(choices=[('local', 'Local Disk'), ('object_storage', 'Object Storage')], default='local', help_text='Storage backend used for this file', max_length=30)),
                ('storage_key', models.CharField(blank=True, help_text='Abstract storage key/path for future object storage migration', max_length=500)),
                ('retention_expires_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evidence_files', to='assistant.report')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_dispute_media', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['report', '-created_at'], name='assistant_di_report__be8e93_idx'), models.Index(fields=['media_type', '-created_at'], name='assistant_di_media_t_5f8391_idx'), models.Index(fields=['retention_expires_at', 'is_deleted'], name='assistant_di_retenti_7f20ee_idx')],
            },
        ),
    ]
