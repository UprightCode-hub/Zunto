from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0005_productreport_moderated_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='productvideo',
            name='scanned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='productvideo',
            name='security_quarantine_path',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='productvideo',
            name='security_scan_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='productvideo',
            name='security_scan_status',
            field=models.CharField(
                choices=[('pending', 'Pending'), ('clean', 'Clean'), ('quarantined', 'Quarantined'), ('rejected', 'Rejected')],
                db_index=True,
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name='productvideo',
            index=models.Index(fields=['product', 'security_scan_status', '-uploaded_at'], name='mkt_vid_scan_idx'),
        ),
    ]
