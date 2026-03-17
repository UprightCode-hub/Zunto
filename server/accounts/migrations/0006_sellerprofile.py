from django.db import migrations, models
import django.db.models.deletion
import uuid


def backfill_seller_profiles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    SellerProfile = apps.get_model('accounts', 'SellerProfile')

    seller_users = User.objects.filter(is_seller=True).only('id', 'is_verified_seller', 'seller_commerce_mode')
    for user in seller_users.iterator():
        SellerProfile.objects.update_or_create(
            user_id=user.id,
            defaults={
                'status': 'approved',
                'is_verified_seller': bool(getattr(user, 'is_verified_seller', False)),
                'seller_commerce_mode': getattr(user, 'seller_commerce_mode', 'direct') or 'direct',
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_user_seller_flags'),
    ]

    operations = [
        migrations.CreateModel(
            name='SellerProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], db_index=True, default='pending', max_length=20)),
                ('is_verified_seller', models.BooleanField(default=False)),
                ('seller_commerce_mode', models.CharField(choices=[('direct', 'Direct Seller (buyer pays seller directly)'), ('managed', 'Managed by Zunto (buyer pays Zunto)')], default='direct', help_text='Direct sellers handle payment off-platform. Managed sellers use Zunto payment, shipping, and refunds.', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='seller_profile', to='accounts.user')),
            ],
            options={
                'db_table': 'seller_profiles',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='sellerprofile',
            index=models.Index(fields=['status'], name='seller_prof_status_5c6689_idx'),
        ),
        migrations.AddIndex(
            model_name='sellerprofile',
            index=models.Index(fields=['is_verified_seller'], name='seller_prof_is_veri_4eebf3_idx'),
        ),
        migrations.RunPython(backfill_seller_profiles, migrations.RunPython.noop),
    ]

