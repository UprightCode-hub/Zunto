from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0008_rename_mkt_vid_scan_idx_product_vid_product_6b28b2_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='productview',
            name='source',
            field=models.CharField(choices=[('ai', 'AI'), ('normal_search', 'Normal Search'), ('homepage_feed', 'Homepage Feed'), ('direct', 'Direct')], db_index=True, default='direct', max_length=20),
        ),
        migrations.AddIndex(
            model_name='productview',
            index=models.Index(fields=['source', '-viewed_at'], name='market_prod_source_3fc319_idx'),
        ),
    ]
