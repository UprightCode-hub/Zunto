#server/accounts/management/commands/create_test_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import SellerProfile

User = get_user_model()

TEST_PASSWORD = 'Test123!'


class Command(BaseCommand):
    help = 'Create test users for development'
    
    def handle(self, *args, **kwargs):
                           
        users_data = [
            {
                'email': 'buyer@test.com',
                'first_name': 'Test',
                'last_name': 'Buyer',
                'role': 'buyer',
                'is_verified': True,
                'is_active': True,
            },
            {
                'email': 'seller@test.com',
                'first_name': 'Test',
                'last_name': 'Seller',
                'role': 'seller',
                'is_seller': True,
                'is_verified_seller': True,
                'is_verified': True,
                'is_active': True,
            },
            {
                'email': 'service@test.com',
                'first_name': 'Test',
                'last_name': 'Provider',
                'role': 'service_provider',
                'is_verified': True,
                'is_active': True,
            },
        ]
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults=user_data,
            )
            for key, value in user_data.items():
                setattr(user, key, value)
            user.set_password(TEST_PASSWORD)
            user.save()

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {user_data["email"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User already exists, repaired credentials and flags: {user_data["email"]}')
                )
            if user.email == 'seller@test.com':
                SellerProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'status': SellerProfile.STATUS_APPROVED,
                        'is_verified_seller': True,
                        'verified': True,
                        'seller_commerce_mode': user.seller_commerce_mode,
                    },
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Test credentials ready:'))
        for user_data in users_data:
            self.stdout.write(f'  {user_data["email"]} / {TEST_PASSWORD}')
