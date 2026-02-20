#server/market/migrations/0004_productview_product_user_index.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0003_productshareevent'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='productview',
            index=models.Index(fields=['product', 'user'], name='product_view_product_user_idx'),
        ),
    ]
