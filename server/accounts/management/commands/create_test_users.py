#server/accounts/management/commands/create_test_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import SellerProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test users for development'
    
    def handle(self, *args, **kwargs):
                           
        users_data = [
            {
                'email': 'buyer@test.com',
                'password': 'Test123!',
                'first_name': 'Test',
                'last_name': 'Buyer',
                'role': 'buyer',
                'is_verified': True
            },
            {
                'email': 'seller@test.com',
                'password': 'Test123!',
                'first_name': 'Test',
                'last_name': 'Seller',
                'role': 'seller',
                'is_seller': True,
                'is_verified_seller': True,
                'is_verified': True
            },
            {
                'email': 'service@test.com',
                'password': 'Test123!',
                'first_name': 'Test',
                'last_name': 'Provider',
                'role': 'service_provider',
                'is_verified': True
            },
        ]
        
        for user_data in users_data:
            if not User.objects.filter(email=user_data['email']).exists():
                user = User.objects.create_user(**user_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {user_data["email"]}')
                )
            else:
                user = User.objects.get(email=user_data['email'])
                for key, value in user_data.items():
                    if key != 'password':
                        setattr(user, key, value)
                user.save()
                self.stdout.write(
                    self.style.WARNING(f'User already exists, updated role flags: {user_data["email"]}')
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
