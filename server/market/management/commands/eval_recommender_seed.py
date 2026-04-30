from django.core.management.base import BaseCommand, CommandError

from market.recommender_eval_seed import (
    DATASET_LABEL,
    dumps_pretty,
    run_seeded_recommender_evals,
    seeded_product_queryset,
)


class Command(BaseCommand):
    help = 'Run deterministic recommender evals against the labeled seed catalog.'

    def add_arguments(self, parser):
        parser.add_argument('--top-k', type=int, default=5, help='Number of direct retrieval results to inspect per case.')
        parser.add_argument('--json', action='store_true', help='Print machine-readable JSON.')

    def handle(self, *args, **options):
        if not seeded_product_queryset().exists():
            raise CommandError(
                f'No {DATASET_LABEL} products found. Run seed_recommender_eval_products first.'
            )

        report = run_seeded_recommender_evals(top_k=options['top_k'])

        if options['json']:
            self.stdout.write(dumps_pretty(report))
            return

        self.stdout.write(
            f"Seeded recommender evals: {report['passed']}/{report['total']} "
            f"passed ({report['pass_rate_percent']}%)."
        )
        for result in report['results']:
            status = 'PASS' if result['passed'] else 'FAIL'
            titles = ', '.join(product['title'] for product in result['results']) or 'no results'
            self.stdout.write(f"- {status} {result['name']}: {titles}")

        if report['remaining_gaps']:
            self.stdout.write('Remaining retrieval/ranking gaps:')
            for gap in report['remaining_gaps']:
                self.stdout.write(f"- {gap['case']}: {gap['reason']}")
