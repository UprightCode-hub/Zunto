from django.core.management.base import BaseCommand

from market.models import Product
from market.recommender_eval_seed import (
    audit_product_recommendation_quality,
    dumps_pretty,
    format_audit_report,
)


class Command(BaseCommand):
    help = 'Audit product structured-data coverage for AI recommendations.'

    def add_arguments(self, parser):
        parser.add_argument('--dataset-label', default='', help='Optional attributes.dataset_label slice to audit.')
        parser.add_argument('--all-statuses', action='store_true', help='Audit all products instead of active products only.')
        parser.add_argument('--json', action='store_true', help='Print machine-readable JSON.')

    def handle(self, *args, **options):
        queryset = Product.objects.all() if options['all_statuses'] else Product.objects.filter(status='active')
        dataset_label = str(options.get('dataset_label') or '').strip()
        if dataset_label:
            queryset = queryset.filter(attributes__dataset_label=dataset_label)

        audit = audit_product_recommendation_quality(queryset)

        if options['json']:
            self.stdout.write(dumps_pretty(audit))
            return

        self.stdout.write(format_audit_report(audit))
