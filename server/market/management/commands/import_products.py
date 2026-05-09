import csv
import json
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from market.demo_image_urls import existing_image_url_or_blank, image_url_for_product, is_placeholder_image_url
from market.models import Category, Location, Product, ProductFamily


User = get_user_model()

BATCH_SIZE = 1000
TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}
CONDITION_ALIASES = {
    "brand_new": "new",
    "unused": "new",
    "used": "good",
    "tokunbo": "good",
    "fairly_used": "good",
    "fairly used": "good",
    "second_hand": "good",
    "second hand": "good",
}
STATUS_ALIASES = {
    "available": "active",
    "in_stock": "active",
    "in stock": "active",
    "out_of_stock": "sold",
    "out of stock": "sold",
}
GENERATED_IMAGE_SOURCE = "demo_external_url:loremflickr_category"


class Command(BaseCommand):
    help = "Bulk import products from CSV or JSON with external image URLs."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="CSV or JSON file containing product rows.")
        parser.add_argument(
            "--seller",
            default="",
            help=(
                "Fallback seller email or id. Rows can also provide seller_email, "
                "seller_id, or seller."
            ),
        )
        parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing products matched by seller + title instead of skipping them.",
        )
        parser.add_argument(
            "--skip-missing-lookups",
            action="store_true",
            help="Skip rows with missing category/location/family instead of creating simple lookup records.",
        )
        parser.add_argument(
            "--no-demo-image-fallback",
            action="store_true",
            help="Leave image_url_locked blank when a row does not provide an external image URL.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Product import file not found: {path}")

        rows = self._load_rows(path)
        if not rows:
            self.stdout.write(self.style.WARNING("No product rows found."))
            return

        batch_size = max(1, int(options["batch_size"] or BATCH_SIZE))
        create_missing = (not options["skip_missing_lookups"]) and (not options["dry_run"])
        self._load_lookup_caches()
        default_seller = self._resolve_default_seller(options.get("seller") or "")
        if default_seller:
            self.stdout.write(f"Default seller: {default_seller.email}")

        prepared = []
        errors = []
        for row_number, row in enumerate(rows, start=2 if path.suffix.lower() == ".csv" else 1):
            try:
                prepared.append(
                    self._prepare_row(
                        row,
                        row_number=row_number,
                        default_seller=default_seller,
                        create_missing=create_missing,
                        use_demo_image_fallback=not options["no_demo_image_fallback"],
                    )
                )
            except ValueError as exc:
                errors.append(f"Row {row_number}: {exc}")

        prepared = [item for item in prepared if item]
        if not prepared:
            self._print_errors(errors)
            self.stdout.write(self.style.WARNING("No valid products to import."))
            return

        seller_ids = {item["seller"].id for item in prepared}
        titles = {item["title"] for item in prepared}
        product_manager = getattr(Product, "all_objects", Product.objects)
        existing_products = {
            (product.seller_id, product.title): product
            for product in product_manager.filter(seller_id__in=seller_ids, title__in=titles)
        }
        used_slugs = set(product_manager.exclude(slug="").values_list("slug", flat=True))

        to_create = []
        to_update = []
        seen_keys = set()
        skipped_duplicates = 0

        for item in prepared:
            key = (item["seller"].id, item["title"])
            if key in seen_keys:
                skipped_duplicates += 1
                continue
            seen_keys.add(key)

            existing = existing_products.get(key)
            if existing:
                if options["update_existing"]:
                    if item.pop("_needs_demo_image", False):
                        self._assign_generated_image_url(item, existing.slug or existing.id)
                    self._apply_existing_updates(existing, item)
                    to_update.append(existing)
                else:
                    skipped_duplicates += 1
                continue

            slug_seed = item.pop("slug", "")
            item["slug"] = self._unique_slug(slug_seed or item["title"], used_slugs)
            if item.pop("_needs_demo_image", False):
                self._assign_generated_image_url(item, item["slug"])
            to_create.append(Product(**item))

        if options["dry_run"]:
            self._print_errors(errors)
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY RUN: {len(to_create)} new, {len(to_update)} updates, "
                    f"{skipped_duplicates} duplicates skipped, {len(errors)} bad rows."
                )
            )
            return

        created_count = self._bulk_create(to_create, batch_size=batch_size)
        updated_count = self._bulk_update(to_update, batch_size=batch_size) if options["update_existing"] else 0

        self._print_errors(errors)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created={created_count}, updated={updated_count}, "
                f"duplicates_skipped={skipped_duplicates}, bad_rows={len(errors)}."
            )
        )

    def _load_rows(self, path):
        suffix = path.suffix.lower()
        if suffix == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        if suffix == ".json":
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                payload = payload.get("products") or payload.get("rows") or []
            if not isinstance(payload, list):
                raise CommandError("JSON import file must contain a list or a {products: [...]} object.")
            return [row for row in payload if isinstance(row, dict)]
        raise CommandError("Unsupported file type. Use .csv or .json.")

    def _load_lookup_caches(self):
        self.category_cache = {}
        for category in Category.objects.all():
            for key in (category.name, category.slug, str(category.id)):
                if key:
                    self.category_cache[self._norm(key)] = category

        self.family_cache = {}
        for family in ProductFamily.objects.select_related("top_category", "subcategory"):
            for key in (family.name, family.slug, str(family.id)):
                if key:
                    self.family_cache[self._norm(key)] = family

        self.location_cache = {}
        for location in Location.objects.all():
            for key in (str(location), str(location.id), self._location_key(location.state, location.city, location.area)):
                if key:
                    self.location_cache[self._norm(key)] = location

        self.seller_cache = {}
        for user in User.objects.filter(Q(is_seller=True) | Q(role="seller")):
            for key in (user.email, str(user.id)):
                if key:
                    self.seller_cache[self._norm(key)] = user

    def _prepare_row(
        self,
        row,
        *,
        row_number,
        default_seller,
        create_missing,
        use_demo_image_fallback,
    ):
        title = self._clean(self._value(row, "title", "name", "product_name"))
        if not title:
            raise ValueError("missing title")

        seller = self._resolve_row_seller(row) or default_seller
        if not seller:
            raise ValueError("missing seller; provide seller_email in the row or --seller")

        category_name = self._clean(self._value(row, "category", "category_name", "category_slug"))
        category = self._resolve_category(category_name, create_missing=create_missing)
        if not category:
            raise ValueError(f"category not found: {category_name or '(blank)'}")

        family_name = self._clean(self._value(row, "product_family", "family", "product_family_name"))
        product_family = self._resolve_family(
            family_name,
            category=category,
            create_missing=create_missing,
        )

        location = self._resolve_location(row, create_missing=create_missing)
        if not location:
            raise ValueError("location not found")

        price = self._decimal(self._value(row, "price", "amount", "unit_price"), field="price")
        quantity = self._int(self._value(row, "quantity", "stock", "stock_quantity"), default=1)
        listing_type = self._clean(self._value(row, "listing_type", default="product")) or "product"
        condition = self._normalize_condition(self._value(row, "condition", default="new"))
        if listing_type == "product" and condition not in dict(Product.CONDITION_CHOICES):
            raise ValueError(f"invalid condition: {condition}")

        status = self._normalize_status(self._value(row, "status", default="active"))
        if status not in dict(Product.STATUS_CHOICES):
            status = "active"

        provided_image_url = self._external_url(
            self._value(row, "image_url", "image", "primary_image", "image_url_locked")
        )
        image_url = provided_image_url
        needs_demo_image = not image_url and use_demo_image_fallback
        default_image_source = "external_import_url" if provided_image_url else (GENERATED_IMAGE_SOURCE if needs_demo_image else "")
        image_source = self._clean(
            self._value(
                row,
                "image_source",
                default=default_image_source,
            )
        )[:255]

        return {
            "seller": seller,
            "title": title,
            "slug": self._clean(self._value(row, "slug")),
            "description": self._clean(self._value(row, "description", default=title)),
            "listing_type": listing_type,
            "category": category,
            "product_family": product_family,
            "location": location,
            "price": price,
            "negotiable": self._bool(self._value(row, "negotiable", "is_negotiable"), default=False),
            "condition": condition,
            "brand": self._clean(self._value(row, "brand")),
            "quantity": max(0, quantity),
            "status": status,
            "is_featured": self._bool(self._value(row, "is_featured", "featured"), default=False),
            "is_boosted": self._bool(self._value(row, "is_boosted", "boosted"), default=False),
            "is_verified": self._bool(self._value(row, "is_verified", "verified"), default=False),
            "is_verified_product": self._bool(self._value(row, "is_verified_product", "verified_product"), default=False),
            "attributes": self._json_object(self._value(row, "attributes"), default={}),
            "search_tags": self._json_list(self._value(row, "search_tags", "tags", "keywords"), default=[]),
            "image_url_locked": image_url or "",
            "image_source": image_source,
            "_needs_demo_image": needs_demo_image,
        }

    def _resolve_default_seller(self, value):
        if value:
            seller = self._find_seller(value)
            if not seller:
                raise CommandError(f"Default seller not found: {value}")
            return seller
        return User.objects.filter(Q(is_seller=True) | Q(role="seller")).order_by("email").first()

    def _resolve_row_seller(self, row):
        value = self._value(row, "seller_email", "seller_id", "seller")
        return self._find_seller(value) if value else None

    def _find_seller(self, value):
        key = self._norm(value)
        if key in self.seller_cache:
            return self.seller_cache[key]
        text = str(value or "").strip()
        if "@" in text:
            user = User.objects.filter(email__iexact=text).first()
        else:
            try:
                user = User.objects.filter(id=uuid.UUID(text)).first()
            except (TypeError, ValueError):
                user = None
        if user:
            self.seller_cache[self._norm(user.email)] = user
            self.seller_cache[self._norm(user.id)] = user
        return user

    def _resolve_category(self, value, *, create_missing):
        key = self._norm(value)
        if not key:
            return None
        category = self.category_cache.get(key)
        if category or not create_missing:
            return category
        category, _ = Category.objects.get_or_create(
            name=self._clean(value),
            defaults={"description": "", "is_active": True},
        )
        for cache_key in (category.name, category.slug, str(category.id)):
            self.category_cache[self._norm(cache_key)] = category
        return category

    def _resolve_family(self, value, *, category, create_missing):
        key = self._norm(value)
        if not key:
            return None
        family = self.family_cache.get(key)
        if family or not create_missing:
            return family
        top_category = category.parent or category
        subcategory = category if category.parent_id else None
        family, _ = ProductFamily.objects.get_or_create(
            name=self._clean(value),
            top_category=top_category,
            subcategory=subcategory,
            defaults={"is_active": True},
        )
        for cache_key in (family.name, family.slug, str(family.id)):
            self.family_cache[self._norm(cache_key)] = family
        return family

    def _resolve_location(self, row, *, create_missing):
        location_id = self._value(row, "location_id")
        if location_id and self._norm(location_id) in self.location_cache:
            return self.location_cache[self._norm(location_id)]

        state = self._clean(self._value(row, "state"))
        city = self._clean(self._value(row, "city"))
        area = self._clean(self._value(row, "area", "lga"))
        raw_location = self._clean(self._value(row, "location", "location_display"))

        if not (state or city or area) and raw_location:
            parts = [part.strip() for part in raw_location.split(",") if part.strip()]
            if len(parts) >= 3:
                area, city, state = parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                city, state = parts[0], parts[1]
            elif len(parts) == 1:
                city, state = parts[0], "Nigeria"

        cache_key = self._norm(raw_location or self._location_key(state, city, area))
        if cache_key in self.location_cache:
            return self.location_cache[cache_key]
        if not create_missing or not (state or city or area):
            return None

        location, _ = Location.objects.get_or_create(
            state=state or "Nigeria",
            city=city or state or "Unknown",
            area=area,
            defaults={"is_active": True},
        )
        for key in (str(location), str(location.id), self._location_key(location.state, location.city, location.area)):
            self.location_cache[self._norm(key)] = location
        return location

    def _bulk_create(self, products, *, batch_size):
        created = 0
        total = len(products)
        for start in range(0, total, batch_size):
            batch = products[start:start + batch_size]
            with transaction.atomic():
                Product.objects.bulk_create(batch, batch_size=batch_size, ignore_conflicts=True)
            created += len(batch)
            self.stdout.write(f"Created batch progress: {min(start + batch_size, total)}/{total}")
        return created

    def _bulk_update(self, products, *, batch_size):
        if not products:
            return 0
        fields = [
            "description",
            "listing_type",
            "category",
            "product_family",
            "location",
            "price",
            "negotiable",
            "condition",
            "brand",
            "quantity",
            "status",
            "is_featured",
            "is_boosted",
            "is_verified",
            "is_verified_product",
            "attributes",
            "search_tags",
            "image_url_locked",
            "image_source",
        ]
        updated = 0
        for start in range(0, len(products), batch_size):
            batch = products[start:start + batch_size]
            with transaction.atomic():
                Product.objects.bulk_update(batch, fields=fields, batch_size=batch_size)
            updated += len(batch)
            self.stdout.write(f"Updated batch progress: {min(start + batch_size, len(products))}/{len(products)}")
        return updated

    def _apply_existing_updates(self, product, item):
        for field, value in item.items():
            if field == "slug":
                continue
            if (
                field in {"image_url_locked", "image_source"}
                and item.get("image_source") == GENERATED_IMAGE_SOURCE
                and existing_image_url_or_blank(product.image_url_locked)
            ):
                continue
            setattr(product, field, value)

    def _assign_generated_image_url(self, item, product_identifier):
        product_family = item.get("product_family")
        item["image_url_locked"] = image_url_for_product(
            title=item.get("title", ""),
            category=getattr(item.get("category"), "name", item.get("category", "")),
            product_family=getattr(product_family, "name", product_family or ""),
            brand=item.get("brand", ""),
            product_identifier=product_identifier,
        )
        item["image_source"] = GENERATED_IMAGE_SOURCE

    def _unique_slug(self, value, used_slugs):
        base = slugify(value)[:230] or "product"
        slug = base
        counter = 1
        while slug in used_slugs:
            suffix = f"-{counter}"
            slug = f"{base[:255 - len(suffix)]}{suffix}"
            counter += 1
        used_slugs.add(slug)
        return slug

    def _value(self, row, *keys, default=""):
        for key in keys:
            if key in row and row[key] not in (None, ""):
                return row[key]
        return default

    def _clean(self, value):
        return " ".join(str(value or "").strip().split())

    def _norm(self, value):
        return self._clean(value).lower()

    def _location_key(self, state, city, area):
        return ", ".join(part for part in (area, city, state) if part)

    def _bool(self, value, *, default=False):
        if value in (None, ""):
            return default
        if isinstance(value, bool):
            return value
        normalized = self._norm(value)
        if normalized in TRUE_VALUES:
            return True
        if normalized in FALSE_VALUES:
            return False
        return default

    def _decimal(self, value, *, field):
        try:
            return Decimal(str(value).replace(",", "").strip())
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"invalid {field}: {value}") from exc

    def _int(self, value, *, default=0):
        if value in (None, ""):
            return default
        try:
            return int(float(str(value).replace(",", "").strip()))
        except (TypeError, ValueError):
            return default

    def _json_object(self, value, *, default):
        parsed = self._parse_jsonish(value, default=default)
        return parsed if isinstance(parsed, dict) else default

    def _json_list(self, value, *, default):
        parsed = self._parse_jsonish(value, default=default)
        if isinstance(parsed, list):
            return [self._clean(item).lower() for item in parsed if self._clean(item)]
        if isinstance(parsed, str):
            return [self._clean(item).lower() for item in parsed.split("|") if self._clean(item)]
        return default

    def _parse_jsonish(self, value, *, default):
        if value in (None, ""):
            return default
        if isinstance(value, (dict, list)):
            return value
        text = str(value).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if "," in text:
                return [item.strip() for item in text.split(",") if item.strip()]
            if "|" in text:
                return [item.strip() for item in text.split("|") if item.strip()]
            return text

    def _external_url(self, value):
        text = self._clean(value)
        if not text:
            return ""
        parsed = urlparse(text)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            if is_placeholder_image_url(text):
                return ""
            return text
        return ""

    def _normalize_condition(self, value):
        normalized = self._norm(value or "new")
        normalized = normalized.replace("-", "_").replace(" ", "_")
        return CONDITION_ALIASES.get(normalized, normalized)

    def _normalize_status(self, value):
        normalized = self._norm(value or "active").replace("-", "_").replace(" ", "_")
        return STATUS_ALIASES.get(normalized, normalized)

    def _print_errors(self, errors):
        if not errors:
            return
        self.stdout.write(f"\nFirst {min(20, len(errors))} row issues:")
        for message in errors[:20]:
            self.stderr.write(f"  {message}")
        if len(errors) > 20:
            self.stderr.write(f"  ... and {len(errors) - 20} more")
