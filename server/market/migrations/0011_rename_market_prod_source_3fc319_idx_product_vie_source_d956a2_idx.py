# Generated manually to preserve migration graph compatibility.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0010_product_is_verified_product'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='productview',
            old_name='market_prod_source_3fc319_idx',
            new_name='product_vie_source_d956a2_idx',
        ),
    ]
