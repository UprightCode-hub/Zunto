#!/usr/bin/env python
"""
Zunto Marketplace Seed Script
==============================
Populates the database with realistic Nigerian demo data:
  - 5 categories
  - 4 Nigerian locations
  - 10 seller accounts (with SellerProfiles)
  - 30 products (3 per seller), each with 2–3 images

Can be run from any of these locations:
    python seed_data.py                  # from server/
    python scripts/seed_data.py          # from server/
    python scripts/seed2.py              # renamed copy in scripts/

Requirements:
    pip install faker requests Pillow
"""

import os
import sys
import django
import random
import io
import time

# ---------------------------------------------------------------------------
# Bootstrap Django — must happen before any model imports
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ZuntoProject.settings")

# Walk up from the script's location until we find the directory that contains
# manage.py — that is the Django root (server/).  This works whether the script
# lives at  server/seed_data.py  or  server/scripts/seed_data.py.
def _find_django_root(start: str) -> str:
    candidate = start
    for _ in range(4):
        if os.path.isfile(os.path.join(candidate, "manage.py")):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return start  # fallback: script's own directory

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DJANGO_ROOT = _find_django_root(THIS_DIR)
if DJANGO_ROOT not in sys.path:
    sys.path.insert(0, DJANGO_ROOT)

django.setup()

# ---------------------------------------------------------------------------
# Now safe to import Django/project modules
# ---------------------------------------------------------------------------
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from faker import Faker
import requests

from accounts.models import User, SellerProfile
from market.models import Category, Location, Product, ProductImage

fake = Faker("en_NG")  # Nigerian locale for realistic names
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

CATEGORIES = [
    {
        "name": "Electronics",
        "description": "Phones, laptops, TVs, and gadgets",
        "icon": "📱",
        "order": 1,
    },
    {
        "name": "Fashion & Clothing",
        "description": "Men's and women's clothing, shoes, and accessories",
        "icon": "👗",
        "order": 2,
    },
    {
        "name": "Home & Furniture",
        "description": "Furniture, kitchen items, and home décor",
        "icon": "🛋️",
        "order": 3,
    },
    {
        "name": "Vehicles",
        "description": "Cars, motorcycles, and spare parts",
        "icon": "🚗",
        "order": 4,
    },
    {
        "name": "Food & Agriculture",
        "description": "Farm produce, groceries, and packaged foods",
        "icon": "🌾",
        "order": 5,
    },
]

LOCATIONS = [
    {"state": "Lagos", "city": "Lagos Island", "area": "Victoria Island"},
    {"state": "Lagos", "city": "Ikeja", "area": "Allen Avenue"},
    {"state": "Abuja", "city": "Garki", "area": "Area 11"},
    {"state": "Kano", "city": "Kano Municipal", "area": "Sabon Gari"},
]

# Realistic Nigerian first/last name pairs
NIGERIAN_NAMES = [
    ("Chukwuemeka", "Obi"),
    ("Adaeze", "Nwosu"),
    ("Babatunde", "Adeyemi"),
    ("Ngozi", "Eze"),
    ("Oluwaseun", "Afolabi"),
    ("Amina", "Musa"),
    ("Emeka", "Okafor"),
    ("Funmilayo", "Okonkwo"),
    ("Ibrahim", "Salisu"),
    ("Chioma", "Igwe"),
]

# Product templates per category slug
PRODUCT_TEMPLATES = {
    "electronics": [
        {
            "title": "Tecno Camon 30 Pro – Barely Used",
            "description": (
                "Selling my Tecno Camon 30 Pro. 256GB storage, 8GB RAM. "
                "Bought 3 months ago, still in perfect condition. Comes with original box and charger. "
                "No scratches, screen protector still on. Reason for selling: upgrading to a different brand."
            ),
            "price": 195000,
            "condition": "like_new",
            "brand": "Tecno",
            "quantity": 1,
        },
        {
            "title": "Infinix Note 40 – 128GB Dual SIM",
            "description": (
                "Infinix Note 40 in good working condition. "
                "Fast charging 45W, 5000mAh battery, 50MP camera. "
                "Minor scratches on the back case but screen is perfect. "
                "Tested and trusted. No repairs, original phone."
            ),
            "price": 145000,
            "condition": "good",
            "brand": "Infinix",
            "quantity": 1,
        },
        {
            "title": "HP Pavilion Laptop i5 11th Gen",
            "description": (
                "HP Pavilion 15, Intel Core i5 11th Gen, 8GB RAM, 512GB SSD. "
                "Windows 11 activated. Great for office work, school, and light design. "
                "Battery holds charge up to 6 hours. Charger included. "
                "No fault, selling because I switched to a Mac."
            ),
            "price": 420000,
            "condition": "good",
            "brand": "HP",
            "quantity": 1,
        },
    ],
    "fashion-clothing": [
        {
            "title": "Ankara Skirt Set – Size M",
            "description": (
                "Beautiful Ankara two-piece skirt and top set, size M. "
                "Hand-sewn by a Lagos tailor, fabric sourced from Balogun market. "
                "Worn once for a family event. No stains or tears. Perfect for owambe."
            ),
            "price": 18500,
            "condition": "like_new",
            "brand": "",
            "quantity": 1,
        },
        {
            "title": "Men's Agbada Set – Royal Blue",
            "description": (
                "Premium quality men's agbada three-piece set in royal blue. "
                "Embroidered neckline, complete with cap (fila). Size XL. "
                "Dry-cleaned and stored properly. Only worn once for a wedding in Abuja."
            ),
            "price": 35000,
            "condition": "like_new",
            "brand": "",
            "quantity": 1,
        },
        {
            "title": "Nike Air Force 1 – Size 43",
            "description": (
                "Authentic Nike Air Force 1 Low Triple White, UK size 9 / EU 43. "
                "Bought from a trusted Lagos reseller. Worn only a handful of times. "
                "Original box included. No yellowing on sole."
            ),
            "price": 68000,
            "condition": "good",
            "brand": "Nike",
            "quantity": 1,
        },
    ],
    "home-furniture": [
        {
            "title": "L-Shaped Sofa – 5-Seater",
            "description": (
                "Quality L-shaped sofa, dark grey fabric, 5-seater. "
                "About 1 year old, very clean and comfortable. "
                "Reason for selling: relocating. Available for self-collection in Lekki. "
                "Dimensions: 280cm x 180cm."
            ),
            "price": 185000,
            "condition": "good",
            "brand": "",
            "quantity": 1,
        },
        {
            "title": "Qasa Standing Fan – 18 Inch",
            "description": (
                "Qasa 18-inch standing fan with remote control. "
                "Three speed settings, oscillating function works perfectly. "
                "Used for one dry season. Everything intact. Lagos delivery available at a small fee."
            ),
            "price": 22000,
            "condition": "good",
            "brand": "Qasa",
            "quantity": 2,
        },
        {
            "title": "IKEA-Style Office Desk & Chair Set",
            "description": (
                "White work desk (120cm x 60cm) and ergonomic office chair. "
                "Desk has two drawers and a cable management hole. "
                "Chair has adjustable height and lumbar support. "
                "Both in excellent condition. Bought for home office, no longer needed."
            ),
            "price": 78000,
            "condition": "like_new",
            "brand": "",
            "quantity": 1,
        },
    ],
    "vehicles": [
        {
            "title": "Toyota Camry 2015 – Full Option",
            "description": (
                "2015 Toyota Camry SE, full option. Black exterior, black leather interior. "
                "Reverse camera, push-start, sunroof, Bluetooth audio. "
                "Lagos-cleared, all papers complete. "
                "Engine and chassis number available for verification. Priced to sell fast."
            ),
            "price": 9800000,
            "condition": "good",
            "brand": "Toyota",
            "quantity": 1,
        },
        {
            "title": "Honda CB 150 Motorcycle – 2022",
            "description": (
                "Honda CB 150 2022 model. Fuel-efficient dispatch bike, low mileage. "
                "Custom rack fitted for delivery. Tyres newly changed. "
                "All documents available, no faults. Ideal for logistics or personal use."
            ),
            "price": 620000,
            "condition": "good",
            "brand": "Honda",
            "quantity": 1,
        },
        {
            "title": "Ford Ranger Pickup – 2018",
            "description": (
                "2018 Ford Ranger XLT 4x4, manual gearbox, diesel. "
                "Used for farm transportation. Body in fair condition, engine very strong. "
                "New brake pads and battery fitted last month. "
                "Good for construction site or farm work. Serious buyers only."
            ),
            "price": 12500000,
            "condition": "fair",
            "brand": "Ford",
            "quantity": 1,
        },
    ],
    "food-agriculture": [
        {
            "title": "Fresh Tomatoes – 50kg Bag (Farm Gate Price)",
            "description": (
                "Fresh Roma tomatoes, harvested this week from our Kaduna farm. "
                "Perfect for market traders, restaurants, and food processors. "
                "Bulk discount available for orders above 200kg. "
                "Delivery can be arranged to Kano main market."
            ),
            "price": 28000,
            "condition": "new",
            "brand": "",
            "quantity": 50,
        },
        {
            "title": "Organic Palm Oil – 25 Litres",
            "description": (
                "Pure, unadulterated red palm oil from Imo State. "
                "Processed traditionally, no additives or preservatives. "
                "Rich colour and aroma. Good for cooking or resale. "
                "Available in 5L and 25L jerry cans. Wholesale enquiries welcome."
            ),
            "price": 18500,
            "condition": "new",
            "brand": "",
            "quantity": 30,
        },
        {
            "title": "Basmati Rice – 50kg Bag",
            "description": (
                "Long-grain basmati rice, perfect for jollof and fried rice. "
                "Imported, sealed bag, no weevils. Bulk pricing available. "
                "Suitable for event caterers, canteen operators, and wholesalers. "
                "Pick-up from Kano warehouse or arrange haulage."
            ),
            "price": 55000,
            "condition": "new",
            "brand": "",
            "quantity": 100,
        },
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str):
    print(f"[seed] {msg}")


def fetch_placeholder_image(width: int = 640, height: int = 480, idx: int = 0) -> bytes | None:
    """
    Download a deterministic placeholder image from picsum.photos.
    Falls back to a solid-colour PNG generated with Pillow if the network is unavailable.
    """
    url = f"https://picsum.photos/seed/{idx}/{width}/{height}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content
    except Exception as exc:
        log(f"  ⚠ Could not fetch remote image ({exc}). Generating local placeholder.")
        return _generate_local_placeholder(width, height, idx)


def _generate_local_placeholder(width: int, height: int, idx: int) -> bytes:
    """Generate a minimal solid-colour JPEG using Pillow as a fallback."""
    try:
        from PIL import Image as PILImage

        palette = [
            (230, 126, 34),   # orange
            (52, 152, 219),   # blue
            (46, 204, 113),   # green
            (155, 89, 182),   # purple
            (231, 76, 60),    # red
            (52, 73, 94),     # dark slate
        ]
        colour = palette[idx % len(palette)]
        img = PILImage.new("RGB", (width, height), colour)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return buf.getvalue()
    except ImportError:
        # Ultra-minimal 1×1 white JPEG (valid JFIF bytes)
        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1eP"
            b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00"
            b"\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00"
            b"\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00"
            b"\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81"
            b"\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19"
            b"\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86"
            b"\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4"
            b"\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2"
            b"\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9"
            b"\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5"
            b"\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd7\xff\xd9"
        )


def make_phone() -> str:
    """Generate a unique Nigerian mobile number."""
    prefixes = ["0803", "0806", "0810", "0813", "0816", "0703", "0706", "0803", "0905", "0901"]
    while True:
        number = random.choice(prefixes) + "".join([str(random.randint(0, 9)) for _ in range(7)])
        if not User.objects.filter(phone=number).exists():
            return number


# ---------------------------------------------------------------------------
# Seeding functions
# ---------------------------------------------------------------------------

def seed_categories() -> dict[str, Category]:
    log("Seeding categories…")
    created = {}
    for data in CATEGORIES:
        cat, made = Category.objects.get_or_create(
            name=data["name"],
            defaults={
                "description": data["description"],
                "icon": data["icon"],
                "order": data["order"],
                "is_active": True,
            },
        )
        status = "created" if made else "exists"
        log(f"  {status}: {cat.name}")
        created[cat.slug] = cat
    return created


def seed_locations() -> list[Location]:
    log("Seeding locations…")
    locs = []
    for data in LOCATIONS:
        loc, made = Location.objects.get_or_create(
            state=data["state"],
            city=data["city"],
            area=data.get("area", ""),
            defaults={"is_active": True},
        )
        status = "created" if made else "exists"
        log(f"  {status}: {loc}")
        locs.append(loc)
    return locs


def seed_sellers(locations: list[Location]) -> list[User]:
    log("Seeding seller accounts…")
    sellers = []

    for idx, (first_name, last_name) in enumerate(NIGERIAN_NAMES):
        email = f"{first_name.lower()}.{last_name.lower()}@zunto-demo.com"

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            log(f"  exists: {user.email}")
            sellers.append(user)
            continue

        phone = make_phone()
        location = locations[idx % len(locations)]

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password="ZuntoSeed@2024!",
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role="seller",
                is_seller=True,
                is_verified=True,           # required for JWT login
                is_verified_seller=True,
                seller_commerce_mode="direct",
                address=fake.address(),
                city=location.city,
                state=location.state,
                country="Nigeria",
                bio=f"Trusted seller on Zunto. Specialising in quality goods across Nigeria.",
            )

            # Create approved SellerProfile and assign active location
            # (Product.save() reads active_location_id from here)
            SellerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "status": SellerProfile.STATUS_APPROVED,
                    "is_verified_seller": True,
                    "verified": True,
                    "seller_commerce_mode": "direct",
                    "active_location": location,
                },
            )

        log(f"  created: {user.email}  ({location})")
        sellers.append(user)

    return sellers


def seed_products(
    sellers: list[User],
    categories: dict[str, Category],
    image_counter: list[int],
):
    log("Seeding products…")

    # Map category slug → list of templates
    cat_templates = list(PRODUCT_TEMPLATES.items())  # [(slug, [templates]), …]

    total = 0
    for seller_idx, seller in enumerate(sellers):
        # Pick which category bundle this seller is "known for"
        slug, templates = cat_templates[seller_idx % len(cat_templates)]
        category = categories.get(slug)

        for tmpl in templates:
            title = tmpl["title"]

            # Idempotency: skip if a product with this exact title by this seller exists
            if Product.objects.filter(seller=seller, title=title).exists():
                log(f"  exists: [{seller.first_name}] {title}")
                continue

            with transaction.atomic():
                product = Product(
                    seller=seller,
                    title=title,
                    description=tmpl["description"],
                    listing_type="product",
                    category=category,
                    # NOTE: location is set automatically by Product.save() from
                    # seller.seller_profile.active_location — set above in seed_sellers()
                    price=tmpl["price"],
                    negotiable=random.choice([True, False]),
                    condition=tmpl.get("condition", "good"),
                    brand=tmpl.get("brand", ""),
                    quantity=tmpl.get("quantity", 1),
                    status="active",
                    is_featured=random.random() < 0.2,
                )
                product.save()  # triggers slug generation + location assignment

                # Attach 2–3 images
                num_images = random.randint(2, 3)
                for img_order in range(num_images):
                    img_idx = image_counter[0]
                    image_counter[0] += 1

                    image_bytes = fetch_placeholder_image(
                        width=640, height=480, idx=img_idx
                    )
                    if image_bytes is None:
                        continue

                    filename = f"seed_product_{img_idx:04d}.jpg"
                    content_file = ContentFile(image_bytes, name=filename)

                    ProductImage.objects.create(
                        product=product,
                        image=content_file,
                        caption=f"{title} – photo {img_order + 1}",
                        order=img_order,
                        is_primary=(img_order == 0),
                    )
                    # Small pause so picsum.photos doesn't rate-limit us
                    time.sleep(0.15)

            log(f"  created: [{seller.first_name}] {title}  ({num_images} images)")
            total += 1

    log(f"  → {total} new products created.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    use_r2 = getattr(settings, "USE_OBJECT_STORAGE", False)
    storage_mode = "Cloudflare R2" if use_r2 else "local filesystem"
    log(f"Starting Zunto seed  |  storage: {storage_mode}")
    log(f"Database: {settings.DATABASES['default'].get('NAME', '(see settings)')}")
    print()

    # Shared counter so every image gets a unique picsum seed
    image_counter = [0]

    categories = seed_categories()
    print()

    locations = seed_locations()
    print()

    sellers = seed_sellers(locations)
    print()

    seed_products(sellers, categories, image_counter)
    print()

    log("✅ Seed complete.")
    log(f"   Categories : {Category.objects.count()}")
    log(f"   Locations  : {Location.objects.count()}")
    log(f"   Sellers    : {User.objects.filter(role='seller').count()}")
    log(f"   Products   : {Product.objects.count()}")
    log(f"   Images     : {ProductImage.objects.count()}")
    print()
    log("Demo login credentials (any seller):")
    log("   email    : chukwuemeka.obi@zunto-demo.com")
    log("   password : ZuntoSeed@2024!")


if __name__ == "__main__":
    main()