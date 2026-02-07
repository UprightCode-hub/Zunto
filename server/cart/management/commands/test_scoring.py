# cart/management/commands/test_scoring.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cart.scoring import calculate_all_scores
from cart.analytics import get_score_analytics_summary

User = get_user_model()


class Command(BaseCommand):
    help = 'Test scoring calculations for a specific user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='User email to test')

    def handle(self, *args, **options):
        email = options.get('email')
        
        if email:
            try:
                user = User.objects.get(email=email)
                scores = calculate_all_scores(user)
                
                self.stdout.write(self.style.SUCCESS(f'\nScores for {user.email}:'))
                self.stdout.write(f"  Abandonment: {scores['abandonment_score']}")
                self.stdout.write(f"  Value: {scores['value_score']}")
                self.stdout.write(f"  Conversion: {scores['conversion_score']}")
                self.stdout.write(f"  Hesitation: {scores['hesitation_score']}")
                self.stdout.write(f"  Composite: {scores['composite_score']}")
                
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User {email} not found'))
        else:
            summary = get_score_analytics_summary()
            self.stdout.write(self.style.SUCCESS('\nScore Analytics Summary:'))
            self.stdout.write(f"  Total Users Scored: {summary['total_users_scored']}")
            self.stdout.write(f"  Average Composite Score: {summary['averages']['composite']}")
            self.stdout.write(f"  Score Range: {summary['range']['min']} - {summary['range']['max']}")
            self.stdout.write(f"\nDistribution:")
            dist = summary['distribution']
            self.stdout.write(f"  High Value: {dist['high_value']} ({dist['high_value_pct']}%)")
            self.stdout.write(f"  Medium Value: {dist['medium_value']} ({dist['medium_value_pct']}%)")
            self.stdout.write(f"  Low Value: {dist['low_value']} ({dist['low_value_pct']}%)")
            self.stdout.write(f"  At Risk: {dist['at_risk']} ({dist['at_risk_pct']}%)")