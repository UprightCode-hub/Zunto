from django.db import migrations, models


def copy_verified_flag(apps, schema_editor):
    Product = apps.get_model('market', 'Product')
    Product.objects.filter(is_verified=True).update(is_verified_product=True)


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0009_productview_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_verified_product',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(copy_verified_flag, migrations.RunPython.noop),
    ]
