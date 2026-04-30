from django.core.management.base import BaseCommand

from market.taxonomy_seed import dumps_pretty, run_scale_recommender_eval


class Command(BaseCommand):
    help = 'Run recommender smoke evals against the large taxonomy seed catalog.'

    def add_arguments(self, parser):
        parser.add_argument('--top-k', type=int, default=5)
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        report = run_scale_recommender_eval(top_k=options['top_k'])
        if options['json']:
            self.stdout.write(dumps_pretty(report))
            return

        self.stdout.write(
            f"Scale recommender evals: {report['passed']}/{report['total']} "
            f"passed ({report['pass_rate_percent']}%)"
        )
        for result in report['results']:
            status = 'PASS' if result['passed'] else 'FAIL'
            self.stdout.write(
                f"- {status} {result['name']}: "
                f"{result['top3_relevant']} relevant in top 3, "
                f"{result['result_count']} results"
            )
