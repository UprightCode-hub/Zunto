import os

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from market.management.commands.seed_db import BUYER_DOMAIN, SELLER_DOMAIN
from market.models import Product
from market.search.embeddings import (
    _build_product_embedding_text,
    _encode_batch,
    _fallback_embedding,
)
from market.search.vector_backend import (
    PRODUCT_VECTOR_DIMENSIONS,
    bulk_sync_product_vectors,
    product_vector_backend_status,
)


class Command(BaseCommand):
    help = (
        "Seed the complete demo marketplace dataset and ensure product "
        "embeddings/vector index rows are ready."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing Zunto demo buyers/sellers and related rows before seeding.",
        )
        parser.add_argument(
            "--skip-embeddings",
            action="store_true",
            help="Seed accounts/products only; do not build or sync product embeddings.",
        )
        parser.add_argument(
            "--refresh-embeddings",
            action="store_true",
            help="Rebuild embeddings even when a product already has the expected dimensions.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Zunto demo dataset..."))
        previous_seed_flag = os.environ.get("ZUNTO_SEEDING_DEMO")
        os.environ["ZUNTO_SEEDING_DEMO"] = "1"
        try:
            call_command(
                "seed_db",
                clear=options["clear"],
                verbosity=options.get("verbosity", 1),
            )
        finally:
            if previous_seed_flag is None:
                os.environ.pop("ZUNTO_SEEDING_DEMO", None)
            else:
                os.environ["ZUNTO_SEEDING_DEMO"] = previous_seed_flag

        summary = self._demo_summary()
        if summary["products"] == 0:
            raise CommandError("Demo seeding completed but no demo products were found.")

        if options["skip_embeddings"]:
            self._print_summary(summary, embedding_summary=None)
            return

        embedding_summary = self._ensure_product_embeddings(
            refresh=options["refresh_embeddings"]
        )
        self._print_summary(summary, embedding_summary=embedding_summary)

    def _demo_summary(self):
        return {
            "sellers": self._seller_count(),
            "buyers": self._buyer_count(),
            "products": self._demo_products().count(),
        }

    def _seller_count(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.filter(email__endswith=SELLER_DOMAIN).count()

    def _buyer_count(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.filter(email__endswith=BUYER_DOMAIN).count()

    def _demo_products(self):
        return Product.objects.filter(seller__email__endswith=SELLER_DOMAIN)

    def _ensure_product_embeddings(self, *, refresh=False):
        products = list(
            self._demo_products()
            .select_related("category", "product_family", "location")
            .order_by("seller__email", "title")
        )

        to_encode = []
        reused_pairs = []
        embedding_text_map = {}
        empty = 0

        for product in products:
            text = _build_product_embedding_text(product)
            if not text.strip():
                empty += 1
                continue

            existing_vector = product.embedding_vector or []
            if (
                not refresh
                and isinstance(existing_vector, list)
                and len(existing_vector) == PRODUCT_VECTOR_DIMENSIONS
            ):
                reused_pairs.append((product, existing_vector))
                embedding_text_map[product.id] = text
                continue

            to_encode.append((product, text))

        encoded_pairs = []
        if to_encode:
            texts = [text for _product, text in to_encode]
            vectors = self._encode_texts(texts)
            if len(vectors) != len(to_encode):
                vectors = [_fallback_embedding(text, PRODUCT_VECTOR_DIMENSIONS) for text in texts]

            products_to_update = []
            for (product, text), vector in zip(to_encode, vectors):
                if not vector or len(vector) != PRODUCT_VECTOR_DIMENSIONS:
                    empty += 1
                    continue
                product.embedding_vector = vector
                products_to_update.append(product)
                encoded_pairs.append((product, vector))
                embedding_text_map[product.id] = text

            if products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    ["embedding_vector"],
                    batch_size=500,
                )

        vector_pairs = encoded_pairs + reused_pairs
        synced = bulk_sync_product_vectors(
            vector_pairs,
            embedding_text_map=embedding_text_map,
        )
        status = product_vector_backend_status()

        return {
            "encoded": len(encoded_pairs),
            "reused": len(reused_pairs),
            "empty": empty,
            "synced": synced,
            "backend": status.backend,
            "backend_ready": status.ready,
            "backend_reason": status.reason,
        }

    def _encode_texts(self, texts):
        if getattr(settings, "RENDER_FREE_TIER", False):
            return [_fallback_embedding(text, PRODUCT_VECTOR_DIMENSIONS) for text in texts]

        vectors = _encode_batch(texts)
        if vectors:
            return vectors

        return [_fallback_embedding(text, PRODUCT_VECTOR_DIMENSIONS) for text in texts]

    def _print_summary(self, summary, *, embedding_summary):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo seed ready."))
        self.stdout.write(f"Sellers: {summary['sellers']}")
        self.stdout.write(f"Buyers: {summary['buyers']}")
        self.stdout.write(f"Products: {summary['products']}")

        if embedding_summary is None:
            self.stdout.write(self.style.WARNING("Embeddings skipped by request."))
            return

        self.stdout.write(
            "Embeddings: "
            f"encoded={embedding_summary['encoded']} "
            f"reused={embedding_summary['reused']} "
            f"empty={embedding_summary['empty']}"
        )
        self.stdout.write(
            "Vector backend: "
            f"{embedding_summary['backend']} "
            f"ready={embedding_summary['backend_ready']} "
            f"synced={embedding_summary['synced']}"
        )
        if embedding_summary["backend_reason"]:
            self.stdout.write(f"Vector backend reason: {embedding_summary['backend_reason']}")
