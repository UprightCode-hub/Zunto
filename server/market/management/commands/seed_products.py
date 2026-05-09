# server/market/management/commands/seed_products.py

import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from market.demo_image_urls import existing_image_url_or_blank, image_url_for_product
from market.models import Category, ProductFamily, Location, Product

User = get_user_model()

SEED_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "seed", "seed.json"
)

IMAGE_SOURCE = "demo_external_url:loremflickr_category"


class Command(BaseCommand):
    help = "Import seed products from market/seed/seed.json using direct ORM"

    def add_arguments(self, parser):
        parser.add_argument(
            "--seller",
            type=str,
            default=None,
            help="Single seller email. Omit to distribute across all scale sellers.",
        )
        parser.add_argument(
            "--seller-domain",
            type=str,
            default="@zunto-scale.local",
            help="Email domain to filter scale sellers (default: @zunto-scale.local)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing products for the target seller(s) before importing",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Import only this many products (for testing)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate data without writing to DB",
        )

    def handle(self, *args, **options):
        if not os.path.exists(SEED_PATH):
            self.stderr.write(f"seed.json not found at {SEED_PATH}")
            return

        # ------------------------------------------------------------------
        # Resolve seller(s)
        # ------------------------------------------------------------------
        if options["seller"]:
            try:
                sellers = [User.objects.get(email=options["seller"])]
            except User.DoesNotExist:
                self.stderr.write(f"No user with email '{options['seller']}'")
                return
        else:
            sellers = list(
                User.objects.filter(
                    email__endswith=options["seller_domain"]
                ).order_by("email")
            )
            if not sellers:
                self.stderr.write(
                    f"No users found with domain '{options['seller_domain']}'. "
                    f"Pass --seller <email> to specify one manually."
                )
                return
            self.stdout.write(f"Distributing across {len(sellers)} sellers.")

        # ------------------------------------------------------------------
        # Load seed JSON
        # ------------------------------------------------------------------
        with open(SEED_PATH, encoding="utf-8") as f:
            products_data = json.load(f)

        if options["limit"]:
            products_data = products_data[: options["limit"]]

        self.stdout.write(f"Loaded {len(products_data)} products from seed.json")

        # ------------------------------------------------------------------
        # Optional clear
        # ------------------------------------------------------------------
        if options["clear"] and not options["dry_run"]:
            for seller in sellers:
                deleted, _ = Product.objects.filter(seller=seller).delete()
                self.stdout.write(
                    f"Cleared {deleted} products for {seller.email}"
                )

        # ------------------------------------------------------------------
        # Pre-cache lookups — avoids N+1 queries in the loop
        # ------------------------------------------------------------------
        category_cache = {c.name: c for c in Category.objects.all()}
        family_cache = {f.name: f for f in ProductFamily.objects.all()}
        location_cache = {str(loc): loc for loc in Location.objects.all()}

        # ------------------------------------------------------------------
        # Import loop
        # ------------------------------------------------------------------
        success = 0
        skipped = 0
        errors = []

        for i, data in enumerate(products_data):
            title = data.get("title", "")
            seller = sellers[i % len(sellers)]

            # Resolve Category
            category_name = data.get("category", "")
            category = category_cache.get(category_name)
            if not category:
                errors.append(
                    f"Row {i}: category '{category_name}' not found "
                    f"— skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            # Resolve ProductFamily
            family_name = data.get("product_family", "")
            family = family_cache.get(family_name)
            if not family:
                errors.append(
                    f"Row {i}: product_family '{family_name}' not found "
                    f"— skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            # Validate family belongs to category
            allowed = {family.top_category_id, family.subcategory_id}
            if category.id not in allowed:
                errors.append(
                    f"Row {i}: family '{family_name}' does not belong to "
                    f"category '{category_name}' — skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            # Resolve Location
            location_str = data.get("location", "")
            location = location_cache.get(location_str)
            if not location:
                errors.append(
                    f"Row {i}: location '{location_str}' not found "
                    f"— skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            # Validate condition (required for listing_type=product)
            condition = data.get("condition", "")
            listing_type = data.get("listing_type", "product")
            if listing_type == "product" and condition not in dict(
                Product.CONDITION_CHOICES
            ):
                errors.append(
                    f"Row {i}: invalid condition '{condition}' "
                    f"— skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            if options["dry_run"]:
                success += 1
                continue

            try:
                existing_product = Product.objects.filter(seller=seller, title=title).only(
                    "id",
                    "slug",
                    "image_url_locked",
                    "image_source",
                ).first()
                provided_image_url = existing_image_url_or_blank(data.get("image_url") or data.get("image_url_locked"))
                existing_image_url = existing_image_url_or_blank(getattr(existing_product, "image_url_locked", ""))
                new_slug = "" if existing_product else self._unique_slug(title)
                product_identifier = (
                    getattr(existing_product, "slug", "")
                    or getattr(existing_product, "id", "")
                    or new_slug
                )
                image_url = provided_image_url or existing_image_url or image_url_for_product(
                    title=title,
                    category=category_name,
                    product_family=family_name,
                    brand=data.get("brand", ""),
                    product_identifier=product_identifier,
                )
                image_source = (
                    data.get("image_source")
                    or (getattr(existing_product, "image_source", "") if existing_image_url else "")
                    or IMAGE_SOURCE
                )
                defaults = {
                    "description": data.get("description", ""),
                    "listing_type": listing_type,
                    "category": category,
                    "product_family": family,
                    "location": location,
                    "price": data.get("price", "0.00"),
                    "negotiable": data.get("negotiable", False),
                    "condition": condition,
                    "brand": data.get("brand", ""),
                    "quantity": data.get("quantity", 1),
                    "status": data.get("status", "active"),
                    "attributes": data.get("attributes", {}),
                    "search_tags": data.get("search_tags", []),
                    # Store URL-backed demo images so Render free tier
                    # restarts do not wipe locally stored product media.
                    "image_url_locked": image_url,
                    "image_source": image_source,
                }
                if new_slug:
                    defaults["slug"] = new_slug
                Product.objects.update_or_create(
                    seller=seller,
                    title=title,
                    defaults=defaults,
                )
                success += 1
            except Exception as exc:
                errors.append(
                    f"Row {i}: DB error — {exc} — '{title[:50]}'"
                )
                skipped += 1

            if (i + 1) % 50 == 0:
                self.stdout.write(
                    f"  {i + 1}/{len(products_data)} processed..."
                )

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        label = "DRY RUN — " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{label}Done. {success} imported, {skipped} skipped."
            )
        )
        if errors:
            self.stdout.write(f"\nFirst {min(10, len(errors))} issues:")
            for msg in errors[:10]:
                self.stderr.write(f"  {msg}")
            if len(errors) > 10:
                self.stderr.write(f"  ... and {len(errors) - 10} more")

    def _unique_slug(self, value):
        base = slugify(value)[:230] or "product"
        slug = base
        counter = 1
        slug_queryset = Product.all_objects.all()
        while slug_queryset.filter(slug=slug).exists():
            suffix = f"-{counter}"
            slug = f"{base[:255 - len(suffix)]}{suffix}"
            counter += 1
        return slug
