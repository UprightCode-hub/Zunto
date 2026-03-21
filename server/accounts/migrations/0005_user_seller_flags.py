from django.db import migrations, models


def populate_seller_flags(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='seller').update(is_seller=True)
    User.objects.filter(role='seller', is_verified=True).update(is_verified_seller=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_user_seller_commerce_mode_and_pending'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_seller',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='is_verified_seller',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(populate_seller_flags, migrations.RunPython.noop),
    ]
