#server/accounts/management/commands/create_test_users.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

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
                User.objects.create_user(**user_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {user_data["email"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User already exists: {user_data["email"]}')
                )
