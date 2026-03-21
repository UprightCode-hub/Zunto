from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0002_alter_product_deleted_at'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductShareEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('shared_via', models.CharField(default='link', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='share_events', to='market.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_products', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'product_share_events',
                'ordering': ['-created_at'],
                'unique_together': {('product', 'user')},
            },
        ),
        migrations.AddIndex(
            model_name='productshareevent',
            index=models.Index(fields=['product', '-created_at'], name='product_sha_product_6f70d7_idx'),
        ),
        migrations.AddIndex(
            model_name='productshareevent',
            index=models.Index(fields=['user', '-created_at'], name='product_sha_user_id_158a7f_idx'),
        ),
    ]
