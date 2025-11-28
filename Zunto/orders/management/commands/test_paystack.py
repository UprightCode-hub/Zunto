# orders/management/commands/test_paystack.py
from django.core.management.base import BaseCommand
from orders.paystack_service import PaystackService


class Command(BaseCommand):
    help = 'Test Paystack integration'
    
    def handle(self, *args, **options):
        paystack = PaystackService()
        
        # Test initialize transaction
        self.stdout.write("Testing transaction initialization...")
        result = paystack.initialize_transaction(
            email='test@example.com',
            amount=10000,  # 100 Naira in kobo
            reference='TEST-REF-123'
        )
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS('✓ Transaction initialized successfully')
            )
            data = result['data']['data']
            self.stdout.write(f"  Authorization URL: {data['authorization_url']}")
            self.stdout.write(f"  Reference: {data['reference']}")
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed: {result.get("error")}')
            )
        
        # Test verify transaction (will fail if not actually paid)
        self.stdout.write("\nTesting transaction verification...")
        verify_result = paystack.verify_transaction('TEST-REF-123')
        
        if verify_result['success']:
            self.stdout.write(
                self.style.SUCCESS('✓ Verification API is working')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠ Verification failed (expected if payment not made)')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n✓ Paystack integration test completed!')
        )