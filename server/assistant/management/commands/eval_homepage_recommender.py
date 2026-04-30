from django.core.management.base import BaseCommand

from assistant.services.recommendation_evaluator import (
    dumps_pretty,
    run_homepage_recommender_evaluation,
)


class Command(BaseCommand):
    help = 'Run prompt-level evaluation for the homepage AI recommender.'

    def add_arguments(self, parser):
        parser.add_argument('--top-k', type=int, default=5, help='Number of ranked products to inspect per case.')
        parser.add_argument('--json', action='store_true', help='Print machine-readable JSON.')

    def handle(self, *args, **options):
        report = run_homepage_recommender_evaluation(top_k=options['top_k'])

        if options['json']:
            self.stdout.write(dumps_pretty(report))
            return

        self.stdout.write(
            f"Homepage recommender eval: {report['passed']}/{report['total']} "
            f"passed ({report['pass_rate_percent']}%)."
        )
        self.stdout.write('Aggregate metrics:')
        for metric, score in report['metrics'].items():
            self.stdout.write(f"- {metric}: {score}")

        self.stdout.write('Cases:')
        for result in report['results']:
            status = 'PASS' if result['passed'] else 'FAIL'
            titles = ', '.join(item['title'] for item in result['top_results']) or 'no results'
            self.stdout.write(f"- {status} {result['name']}: {titles}")
