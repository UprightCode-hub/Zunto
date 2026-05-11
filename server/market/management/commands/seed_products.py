# server/market/management/commands/seed_products.py

import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from accounts.models import SellerProfile
from market.demo_image_urls import existing_image_url_or_blank, image_url_for_product
from market.models import Category, ProductFamily, Location, Product

User = get_user_model()

SEED_SELLER_PASSWORD = "Seller1234!"
DEFAULT_SELLER_COUNT = 20

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
            "--seller-count",
            type=int,
            default=DEFAULT_SELLER_COUNT,
            help="Number of login-ready sellers to create when seeding by domain.",
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
        if options["seller_count"] < 1:
            self.stderr.write("--seller-count must be at least 1")
            return

        # ------------------------------------------------------------------
        # Resolve seller(s)
        # ------------------------------------------------------------------
        if options["seller"]:
            sellers = [self._ensure_seed_seller(options["seller"], index=1)]
        else:
            sellers = list(
                User.objects.filter(
                    email__endswith=options["seller_domain"]
                ).order_by("email")
            )
            if not sellers:
                sellers = [
                    self._ensure_seed_seller(
                        f"scale-seller-{index:02d}{options['seller_domain']}",
                        index=index,
                    )
                    for index in range(1, options["seller_count"] + 1)
                ]
                self.stdout.write(
                    f"Created {len(sellers)} login-ready sellers for {options['seller_domain']}."
                )
            else:
                sellers = [
                    self._ensure_seed_seller(seller.email, index=index)
                    for index, seller in enumerate(sellers, start=1)
                ]
                self.stdout.write(
                    f"Repaired {len(sellers)} seller accounts for {options['seller_domain']}."
                )
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
        # Pre-cache lookups
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

            # ---- Resolve or CREATE Category ----
            category_name = data.get("category", "")
            category = category_cache.get(category_name)
            if not category and category_name and not options["dry_run"]:
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={
                        "description": category_name,
                        "is_active": True,
                        "order": 100,
                    },
                )
                category_cache[category_name] = category
            if not category:
                errors.append(
                    f"Row {i}: category '{category_name}' not found "
                    f"— skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            # ---- Resolve or CREATE ProductFamily ----
            family_name = data.get("product_family", "")
            family = family_cache.get(family_name)
            if not family and family_name and not options["dry_run"]:
                family, _ = ProductFamily.objects.get_or_create(
                    name=family_name,
                    defaults={
                        "top_category": category,
                        "subcategory": None,
                        "is_active": True,
                    },
                )
                family_cache[family_name] = family
            if not family:
                errors.append(
                    f"Row {i}: product_family '{family_name}' not found "
                    f"— skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            # ---- Resolve or CREATE Location ----
            location_str = data.get("location", "")
            location = location_cache.get(location_str)
            if not location and location_str and not options["dry_run"]:
                # Parse "Area, City, State" format
                parts = [p.strip() for p in location_str.split(",") if p.strip()]
                if len(parts) >= 3:
                    area, city, state = parts[0], parts[1], parts[2]
                elif len(parts) == 2:
                    area, city, state = "", parts[0], parts[1]
                elif len(parts) == 1:
                    area, city, state = "", parts[0], "Nigeria"
                else:
                    area, city, state = "", "Lagos", "Lagos"

                location, _ = Location.objects.get_or_create(
                    state=state,
                    city=city,
                    area=area,
                    defaults={"is_active": True},
                )
                location_cache[location_str] = location
                location_cache[str(location)] = location
            if not location:
                errors.append(
                    f"Row {i}: location '{location_str}' not found "
                    f"— skipping '{title[:50]}'"
                )
                skipped += 1
                continue

            # Validate condition
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
                    "id", "slug", "image_url_locked", "image_source",
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
        self.stdout.write("")
        self.stdout.write("Seed seller credentials:")
        for seller in sellers[:3]:
            self.stdout.write(f"  {seller.email} / {SEED_SELLER_PASSWORD}")
        self.stdout.write("  See TEST_CREDENTIALS.md for more demo credentials.")

    def _ensure_seed_seller(self, email, *, index=1):
        local_part = email.split("@", 1)[0]
        display_name = local_part.replace(".", "-").replace("_", "-")
        user, _created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": display_name[:30] or "Seed",
                "last_name": "Seller",
            },
        )
        user.first_name = user.first_name or display_name[:30] or "Seed"
        user.last_name = user.last_name or "Seller"
        user.role = "seller"
        user.is_seller = True
        user.is_verified = True
        user.is_verified_seller = True
        user.is_active = True
        user.seller_commerce_mode = "managed" if index % 3 == 0 else "direct"
        user.country = user.country or "Nigeria"
        user.bio = user.bio or "Seeded demo seller account with verified login credentials."
        user.set_password(SEED_SELLER_PASSWORD)
        user.save()

        SellerProfile.objects.update_or_create(
            user=user,
            defaults={
                "status": SellerProfile.STATUS_APPROVED,
                "is_verified_seller": True,
                "verified": True,
                "seller_commerce_mode": user.seller_commerce_mode,
            },
        )
        return user

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
