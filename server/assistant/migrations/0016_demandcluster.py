from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0003_productshareevent'),
        ('assistant', '0015_demand_match_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemandCluster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('demand_count', models.IntegerField(default=0)),
                ('last_gap_at', models.DateTimeField(blank=True, null=True)),
                ('hot_score', models.FloatField(default=0.0)),
                ('is_hot', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='demand_clusters', to='market.category')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='demand_clusters', to='market.location')),
            ],
            options={
                'ordering': ['-hot_score', '-updated_at'],
                'indexes': [models.Index(fields=['is_hot', '-hot_score'], name='assistant_d_is_hot_d9a223_idx'), models.Index(fields=['category', 'location'], name='assistant_d_categor_71f976_idx')],
                'constraints': [models.UniqueConstraint(fields=('category', 'location'), name='unique_demand_cluster_category_location')],
            },
        ),
    ]
