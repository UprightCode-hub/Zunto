import django.core.serializers.json
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0019_alter_disputemedia_file'),
        ('market', '0018_product_search_tags'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AIRecommendationFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'feedback_type',
                    models.CharField(
                        choices=[
                            ('helpful', 'Helpful'),
                            ('not_relevant', 'Not relevant'),
                            ('too_expensive', 'Too expensive'),
                            ('wrong_location', 'Wrong location'),
                            ('wrong_condition', 'Wrong condition'),
                            ('wrong_product_type', 'Wrong product type'),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                ('prompt', models.TextField(blank=True)),
                ('message', models.TextField(blank=True)),
                (
                    'source',
                    models.CharField(
                        choices=[('homepage_reco', 'Homepage recommendation')],
                        default='homepage_reco',
                        max_length=40,
                    ),
                ),
                (
                    'recommended_products',
                    models.JSONField(
                        blank=True,
                        default=list,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                    ),
                ),
                (
                    'recommendation_metadata',
                    models.JSONField(
                        blank=True,
                        default=dict,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'selected_product',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ai_recommendation_feedback',
                        to='market.product',
                    ),
                ),
                (
                    'session',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='recommendation_feedback',
                        to='assistant.conversationsession',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='ai_recommendation_feedback',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['feedback_type', '-created_at'], name='assistant_a_feedbac_bda409_idx'),
                    models.Index(fields=['source', '-created_at'], name='assistant_a_source_34a22d_idx'),
                    models.Index(fields=['user', '-created_at'], name='assistant_a_user_id_068e28_idx'),
                    models.Index(fields=['session', '-created_at'], name='assistant_a_session_203c08_idx'),
                    models.Index(fields=['selected_product', '-created_at'], name='assistant_a_selecte_0b93d9_idx'),
                ],
            },
        ),
    ]
