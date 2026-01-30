# cart/management/commands/calculate_scores.py

from django.core.management.base import BaseCommand
from cart.tasks import calculate_user_scores_bulk


class Command(BaseCommand):
    help = 'Manually calculate user scores'

    def handle(self, *args, **options):
        self.stdout.write('Calculating user scores...')
        result = calculate_user_scores_bulk()
        self.stdout.write(self.style.SUCCESS(result))