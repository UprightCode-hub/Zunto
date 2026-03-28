from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_alter_user_profile_picture'),
    ]

    operations = [
        migrations.AddField(
            model_name='sellerprofile',
            name='ai_memory',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
