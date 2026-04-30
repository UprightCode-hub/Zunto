from django.core.management.base import BaseCommand

from market.models import Product
from market.search.embeddings import generate_product_embedding
from market.search.vector_backend import product_vector_backend_status


class Command(BaseCommand):
    help = "Rebuild product embeddings and sync the production product vector index when pgvector is available."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit products processed.')
        parser.add_argument('--active-only', action='store_true', default=True)
        parser.add_argument('--include-inactive', action='store_true')

    def handle(self, *args, **options):
        status = product_vector_backend_status()
        self.stdout.write(
            self.style.NOTICE(
                f"Product vector backend: {status.backend} ready={status.ready} reason={status.reason}"
            )
        )

        queryset = Product.objects.select_related('category', 'location').order_by('id')
        if options['active_only'] and not options['include_inactive']:
            queryset = queryset.filter(status='active')
        limit = int(options.get('limit') or 0)
        if limit > 0:
            queryset = queryset[:limit]

        processed = 0
        updated = 0
        empty = 0
        for product in queryset.iterator(chunk_size=100):
            processed += 1
            vector = generate_product_embedding(product)
            if vector:
                Product.objects.filter(pk=product.pk).update(embedding_vector=vector)
                updated += 1
            else:
                Product.objects.filter(pk=product.pk).update(embedding_vector=[])
                empty += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed={processed} updated_embeddings={updated} empty_embeddings={empty}"
            )
        )
