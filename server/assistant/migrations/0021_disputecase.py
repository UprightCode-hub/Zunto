from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0020_ai_recommendation_feedback'),
        ('chat', '0005_rename_chat_conver_is_lock_534ef9_idx_chat_conver_is_lock_88cc81_idx_and_more'),
        ('orders', '0004_orderitem_order_items_seller__0dab98_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DisputeCase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('case_id', models.CharField(db_index=True, max_length=24, unique=True)),
                ('buyer_name', models.CharField(blank=True, max_length=255)),
                ('buyer_email', models.EmailField(blank=True, max_length=254)),
                ('seller_name', models.CharField(blank=True, max_length=255)),
                ('seller_email', models.EmailField(blank=True, max_length=254)),
                ('complaint_category', models.CharField(choices=[('delivery', 'Delivery'), ('payment', 'Payment'), ('harassment', 'Harassment'), ('fraud', 'Fraud'), ('product_quality', 'Product Quality')], max_length=32)),
                ('reference', models.CharField(blank=True, max_length=255)),
                ('ai_summary', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('under_review', 'Under Review'), ('resolved', 'Resolved')], default='open', max_length=20)),
                ('escalated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('buyer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispute_cases_as_buyer', to=settings.AUTH_USER_MODEL)),
                ('conversation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispute_cases', to='chat.conversation')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispute_cases', to='orders.order')),
                ('seller', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispute_cases_as_seller', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-escalated_at'],
                'indexes': [
                    models.Index(fields=['case_id'], name='assistant_d_case_id_a26456_idx'),
                    models.Index(fields=['status', '-escalated_at'], name='assistant_d_status_8718cf_idx'),
                    models.Index(fields=['complaint_category', '-escalated_at'], name='assistant_d_complai_a844ea_idx'),
                    models.Index(fields=['buyer', '-escalated_at'], name='assistant_d_buyer_i_0ac822_idx'),
                    models.Index(fields=['seller', '-escalated_at'], name='assistant_d_seller__f299a7_idx'),
                ],
            },
        ),
    ]
