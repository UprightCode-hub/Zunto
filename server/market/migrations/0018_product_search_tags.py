from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0017_alter_productimage_image_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='search_tags',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Seller/admin supplied search tags used by hybrid product retrieval. "
                    "Examples: ['iphone', '128gb', 'tokunbo', 'gaming laptop']."
                ),
            ),
        ),
    ]
