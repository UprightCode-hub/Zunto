from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from market.recommender_eval_seed import dumps_pretty, seed_recommender_eval_catalog


class Command(BaseCommand):
    help = 'Seed clearly labeled, idempotent recommender demo/eval products.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete only prior recommender eval demo rows first.')
        parser.add_argument('--skip-embeddings', action='store_true', help='Seed products without rebuilding product embeddings.')
        parser.add_argument(
            '--allow-non-debug',
            action='store_true',
            help='Allow seeding when DEBUG is false. Intended only for isolated staging/eval databases.',
        )
        parser.add_argument('--json', action='store_true', help='Print machine-readable JSON.')

    def handle(self, *args, **options):
        if (
            not settings.DEBUG
            and not getattr(settings, 'TESTING', False)
            and not options['allow_non_debug']
        ):
            raise CommandError(
                'Refusing to seed recommender eval products while DEBUG is false. '
                'Use an isolated database and pass --allow-non-debug only intentionally.'
            )

        summary = seed_recommender_eval_catalog(
            reset=options['reset'],
            rebuild_embeddings=not options['skip_embeddings'],
        )

        if options['json']:
            self.stdout.write(dumps_pretty(summary))
            return

        self.stdout.write(self.style.SUCCESS('Recommender eval seed complete.'))
        self.stdout.write(f"Dataset label: {summary['dataset_label']}")
        self.stdout.write(f"Products: {summary['products']} ({summary['active_products']} active)")
        self.stdout.write(f"Images: {summary['images']}")
        self.stdout.write(
            'Embeddings rebuilt: '
            f"{summary['embeddings']['rebuilt']} "
            f"(empty={summary['embeddings']['empty']}, failed={summary['embeddings']['failed']})"
        )
