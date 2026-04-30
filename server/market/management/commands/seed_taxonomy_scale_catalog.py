from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from market.taxonomy_seed import dumps_pretty, seed_taxonomy_scale_catalog


class Command(BaseCommand):
    help = 'Seed scaled taxonomy, attribute schemas, fake sellers, and test products.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete prior scale-seeded products/users first.')
        parser.add_argument('--products', type=int, default=1000, help='Number of fake products to seed.')
        parser.add_argument('--sellers', type=int, default=20, help='Number of fake sellers to seed.')
        parser.add_argument(
            '--rebuild-embeddings',
            action='store_true',
            help='Generate product embeddings for seeded products.',
        )
        parser.add_argument(
            '--allow-non-debug',
            action='store_true',
            help='Allow seeding when DEBUG is false. Use only on isolated staging/eval databases.',
        )
        parser.add_argument('--json', action='store_true', help='Print machine-readable JSON.')

    def handle(self, *args, **options):
        if (
            not settings.DEBUG
            and not getattr(settings, 'TESTING', False)
            and not options['allow_non_debug']
        ):
            raise CommandError(
                'Refusing to seed scale catalog while DEBUG is false. '
                'Use an isolated database and pass --allow-non-debug intentionally.'
            )

        if options['products'] < 1:
            raise CommandError('--products must be at least 1.')
        if options['sellers'] < 1:
            raise CommandError('--sellers must be at least 1.')

        summary = seed_taxonomy_scale_catalog(
            reset=options['reset'],
            product_count=options['products'],
            seller_count=options['sellers'],
            rebuild_embeddings=options['rebuild_embeddings'],
        )

        if options['json']:
            self.stdout.write(dumps_pretty(summary))
            return

        self.stdout.write(self.style.SUCCESS('Scale taxonomy seed complete.'))
        self.stdout.write(f"Top categories: {summary['top_categories']}")
        self.stdout.write(f"Subcategories: {summary['subcategories']}")
        self.stdout.write(f"Product families: {summary['product_families']}")
        self.stdout.write(f"Attribute schemas: {summary['attribute_schemas']}")
        self.stdout.write(f"Sellers: {summary['sellers']}")
        self.stdout.write(f"Products: {summary['products']} ({summary['active_products']} active)")
        self.stdout.write(
            'Embeddings rebuilt: '
            f"{summary['embeddings']['rebuilt']} "
            f"(empty={summary['embeddings']['empty']}, failed={summary['embeddings']['failed']})"
        )
