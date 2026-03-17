#server/market/migrations/0005_productreport_moderated_by.py
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0004_productview_product_user_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='productreport',
            name='moderated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='moderated_product_reports',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
