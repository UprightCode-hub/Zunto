import json
from django.db import transaction
from market.demo_image_urls import existing_image_url_or_blank, image_url_for_product
from market.models import Product, Category, ProductFamily

BATCH_SIZE = 100
IMAGE_SOURCE = "demo_external_url:loremflickr_category"


def find_family(name, families):
    """
    Flexible matcher for ProductFamily.
    Handles cases like:
    'iPhones Premium' → 'iPhones'
    """
    if not name:
        return None

    name = name.lower().strip()

    # exact match
    if name in families:
        return families[name]

    # partial match
    for key, val in families.items():
        if name in key or key in name:
            return val

    return None


def run():
    with open("market/seed/seed.json", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    created = 0
    skipped = 0

    # preload mappings
    categories = {c.name.lower(): c for c in Category.objects.all()}
    families = {f.name.lower(): f for f in ProductFamily.objects.all()}

    print(f"Loaded {len(categories)} categories")
    print(f"Loaded {len(families)} product families\n")

    for i in range(0, total, BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        objs = []

        for item in batch:
            cat_key = item.get("category", "").lower().strip()
            fam_key = item.get("product_family", "")

            category = categories.get(cat_key)
            family = find_family(fam_key, families)

            if not category:
                print(f"⚠️ Skipping (missing category): {item.get('title')}")
                skipped += 1
                continue

            if not family:
                print(f"⚠️ Skipping (missing product_family): {item.get('title')}")
                skipped += 1
                continue

            try:
                image_url = (
                    existing_image_url_or_blank(item.get("image_url") or item.get("image_url_locked"))
                    or image_url_for_product(
                        title=item.get("title"),
                        category=category.name,
                        product_family=family.name,
                        brand=item.get("brand", ""),
                    )
                )
                obj = Product(
                    title=item.get("title"),
                    description=item.get("description"),
                    listing_type=item.get("listing_type"),
                    category=category,
                    product_family=family,
                    location=item.get("location"),
                    price=item.get("price"),
                    negotiable=item.get("negotiable", True),
                    condition=item.get("condition"),
                    brand=item.get("brand", ""),
                    quantity=item.get("quantity", 1),
                    status=item.get("status", "active"),
                    attributes=item.get("attributes", {}),
                    search_tags=item.get("search_tags", []),
                    image_url_locked=image_url,
                    image_source=item.get("image_source") or IMAGE_SOURCE,
                )
                objs.append(obj)

            except Exception as e:
                print(f"❌ Error building product: {item.get('title')} → {e}")
                skipped += 1

        with transaction.atomic():
            Product.objects.bulk_create(objs, ignore_conflicts=True)

        created += len(objs)
        print(f"Inserted {created}/{total}")

    print("\n======================")
    print(f"✅ Done. Inserted: {created}")
    print(f"⚠️ Skipped: {skipped}")
    print("======================")
