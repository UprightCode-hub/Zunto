from django.contrib.auth.hashers import make_password
from django.db import migrations
from django.db.models import Q


DEMO_PASSWORD = 'Seller1234!'
TEST_PASSWORD = 'Test123!'

SELLER_DOMAINS = (
    '@zunto-demo.com',
    '@zunto-scale.local',
    '@zunto-reco-eval.local',
)
BUYER_DOMAINS = (
    '@zunto-buyer.com',
)
TEST_USERS = {
    'buyer@test.com': {
        'password': TEST_PASSWORD,
        'role': 'buyer',
        'is_seller': False,
        'is_verified_seller': False,
    },
    'seller@test.com': {
        'password': TEST_PASSWORD,
        'role': 'seller',
        'is_seller': True,
        'is_verified_seller': True,
    },
    'service@test.com': {
        'password': TEST_PASSWORD,
        'role': 'service_provider',
        'is_seller': False,
        'is_verified_seller': False,
    },
}


def repair_seeded_demo_accounts(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    SellerProfile = apps.get_model('accounts', 'SellerProfile')

    query = Q(email__in=TEST_USERS.keys())
    for domain in SELLER_DOMAINS + BUYER_DOMAINS:
        query |= Q(email__endswith=domain)

    for user in User.objects.filter(query).iterator():
        test_config = TEST_USERS.get(user.email)
        is_demo_seller = any(user.email.endswith(domain) for domain in SELLER_DOMAINS)
        is_demo_buyer = any(user.email.endswith(domain) for domain in BUYER_DOMAINS)

        if test_config:
            password = test_config['password']
            user.role = test_config['role']
            user.is_seller = test_config['is_seller']
            user.is_verified_seller = test_config['is_verified_seller']
        elif is_demo_seller:
            password = DEMO_PASSWORD
            user.role = 'seller'
            user.is_seller = True
            user.is_verified_seller = True
        elif is_demo_buyer:
            password = DEMO_PASSWORD
            user.role = 'buyer'
            user.is_seller = False
            user.is_verified_seller = False
        else:
            continue

        user.password = make_password(password)
        user.is_active = True
        user.is_verified = True
        user.save()

        if user.is_seller:
            SellerProfile.objects.update_or_create(
                user_id=user.id,
                defaults={
                    'status': 'approved',
                    'is_verified_seller': True,
                    'verified': True,
                    'seller_commerce_mode': getattr(user, 'seller_commerce_mode', 'direct') or 'direct',
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_user_profile_picture'),
    ]

    operations = [
        migrations.RunPython(repair_seeded_demo_accounts, migrations.RunPython.noop),
    ]
