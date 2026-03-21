from django.conf import settings
from django.db import migrations, models
import django.core.serializers.json
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0013_disputeauditlog'),
        ('market', '0008_rename_mkt_vid_scan_idx_product_vid_product_6b28b2_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='conversationsession',
            name='active_product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='active_recommendation_sessions', to='market.product'),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='constraint_state',
            field=models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='context_type',
            field=models.CharField(choices=[('support', 'Support'), ('recommendation', 'Recommendation')], default='support', help_text='Conversation context type: support or recommendation journey', max_length=20),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='drift_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='conversationsession',
            name='intent_state',
            field=models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
        ),
        migrations.AddIndex(
            model_name='conversationsession',
            index=models.Index(fields=['context_type', '-last_activity'], name='assistant_co_context_96b742_idx'),
        ),
        migrations.AddIndex(
            model_name='conversationsession',
            index=models.Index(fields=['assistant_mode', 'context_type', '-last_activity'], name='assistant_co_assista_286483_idx'),
        ),
        migrations.CreateModel(
            name='RecommendationDemandGap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requested_category', models.CharField(blank=True, max_length=120)),
                ('requested_attributes', models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('user_location', models.CharField(blank=True, max_length=200)),
                ('frequency', models.PositiveIntegerField(default=1)),
                ('first_seen_at', models.DateTimeField(auto_now_add=True)),
                ('last_seen_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recommendation_demand_gaps', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-last_seen_at'],
            },
        ),
        migrations.CreateModel(
            name='UserBehaviorProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ai_search_count', models.PositiveIntegerField(default=0)),
                ('normal_search_count', models.PositiveIntegerField(default=0)),
                ('dominant_categories', models.JSONField(blank=True, default=list, encoder=django.core.serializers.json.DjangoJSONEncoder)),
                ('avg_budget_min', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('avg_budget_max', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('ai_conversion_rate', models.FloatField(default=0.0)),
                ('normal_conversion_rate', models.FloatField(default=0.0)),
                ('switch_frequency', models.FloatField(default=0.0)),
                ('ai_high_intent_no_conversion', models.BooleanField(default=False)),
                ('last_aggregated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='behavior_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='recommendationdemandgap',
            index=models.Index(fields=['requested_category', '-last_seen_at'], name='assistant_re_request_6cfad9_idx'),
        ),
        migrations.AddIndex(
            model_name='recommendationdemandgap',
            index=models.Index(fields=['frequency', '-last_seen_at'], name='assistant_re_frequen_4f6251_idx'),
        ),
        migrations.AddIndex(
            model_name='userbehaviorprofile',
            index=models.Index(fields=['-last_aggregated_at'], name='assistant_us_last_ag_4f82ab_idx'),
        ),
        migrations.AddIndex(
            model_name='userbehaviorprofile',
            index=models.Index(fields=['ai_high_intent_no_conversion', '-updated_at'], name='assistant_us_ai_high_d434f8_idx'),
        ),
    ]
