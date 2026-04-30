import json
import random
from decimal import Decimal
from typing import Dict, Iterable, List, Tuple

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify

from accounts.models import SellerProfile
from market.models import (
    Category,
    Location,
    Product,
    ProductAttributeSchema,
    ProductFamily,
)
from market.services.attribute_extractor import suggest_product_metadata

User = get_user_model()

SCALE_DATASET_LABEL = 'zunto_taxonomy_scale_v1'
SCALE_SELLER_DOMAIN = '@zunto-scale.local'
SCALE_PASSWORD = 'ZuntoScaleSeed@2026!'

TOP_CATEGORIES = [
    'Phones & Tablets',
    'Electronics',
    'Computers & Accessories',
    'Fashion',
    'Shoes & Footwear',
    'Beauty & Personal Care',
    'Groceries & Food',
    'Home & Furniture',
    'Appliances',
    'Vehicles',
    'Auto Parts',
    'Building Materials & Tools',
    'Baby & Kids',
    'Health & Wellness',
    'Sports & Fitness',
    'Books & Stationery',
    'Services',
    'Agriculture',
    'Industrial & Business',
    'Others',
]

SUBCATEGORY_BANK = {
    'Phones & Tablets': [
        'iPhones', 'Android Phones', 'Feature Phones', 'Tablets', 'Phone Accessories',
        'Smart Watches', 'Power Banks', 'Chargers & Cables', 'Phone Cases',
        'Screen Protectors', 'Earbuds & Headsets', 'Refurbished Phones', 'Mobile Repairs',
    ],
    'Electronics': [
        'Televisions', 'Audio Speakers', 'Headphones', 'Cameras', 'Gaming Consoles',
        'Drones', 'Projectors', 'Security Cameras', 'Solar Electronics', 'Radios',
        'Electronic Components', 'Streaming Devices', 'Home Theatre Systems',
    ],
    'Computers & Accessories': [
        'Laptops', 'Desktop Computers', 'Monitors', 'Keyboards & Mice', 'Printers',
        'Storage Drives', 'Networking Devices', 'Laptop Bags', 'Computer Parts',
        'Software Licenses', 'Gaming PCs', 'UPS & Power Backup', 'Workstations',
    ],
    'Fashion': [
        'Men Clothing', 'Women Clothing', 'Traditional Wear', 'Dresses', 'Shirts',
        'Trousers & Jeans', 'Bags', 'Watches', 'Jewelry', 'Perfumes', 'Caps & Hats',
        'Belts & Wallets', 'Fashion Accessories',
    ],
    'Shoes & Footwear': [
        'Sneakers', 'Formal Shoes', 'Sandals', 'Slippers', 'Boots', 'Heels',
        'Running Shoes', 'Kids Shoes', 'Safety Shoes', 'Shoe Care', 'Football Boots',
        'Loafers', 'Shoe Accessories',
    ],
    'Beauty & Personal Care': [
        'Skincare', 'Sunscreen', 'Hair Care', 'Hair Oils', 'Makeup', 'Perfumes',
        'Barbing Kits', 'Body Creams', 'Soaps & Washes', 'Natural Beauty',
        'Nail Care', 'Beauty Tools', 'Oral Care Beauty',
    ],
    'Groceries & Food': [
        'Rice & Grains', 'Beans & Legumes', 'Oils', 'Spices', 'Beverages',
        'Snacks', 'Frozen Foods', 'Fresh Produce', 'Meat & Fish', 'Baby Food',
        'Breakfast Foods', 'Bulk Groceries', 'Canned Foods',
    ],
    'Home & Furniture': [
        'Sofas', 'Beds & Mattresses', 'Tables', 'Chairs', 'Wardrobes', 'Kitchenware',
        'Home Decor', 'Curtains & Blinds', 'Lighting', 'Bathroom Accessories',
        'Storage & Organizers', 'Outdoor Furniture', 'Bedding',
    ],
    'Appliances': [
        'Refrigerators', 'Freezers', 'Washing Machines', 'Cookers & Ovens',
        'Microwaves', 'Blenders', 'Fans', 'Air Conditioners', 'Generators',
        'Water Dispensers', 'Irons', 'Vacuum Cleaners', 'Small Kitchen Appliances',
    ],
    'Vehicles': [
        'Cars', 'SUVs', 'Buses', 'Trucks', 'Motorcycles', 'Tricycles', 'Bicycles',
        'Vehicle Rentals', 'Boats', 'Heavy Vehicles', 'Electric Vehicles', 'Car Auctions',
        'Vehicle Accessories',
    ],
    'Auto Parts': [
        'Tyres', 'Batteries', 'Brake Parts', 'Engine Parts', 'Suspension Parts',
        'Car Electronics', 'Body Parts', 'Oils & Fluids', 'Filters', 'Lights',
        'Interior Accessories', 'Tools & Diagnostics',
    ],
    'Building Materials & Tools': [
        'Fasteners & Nails', 'Cement', 'Paints', 'Plumbing Materials',
        'Electrical Materials', 'Tiles', 'Roofing', 'Wood & Boards', 'Hand Tools',
        'Power Tools', 'Safety Gear', 'Doors & Windows',
    ],
    'Baby & Kids': [
        'Baby Clothing', 'Diapers', 'Strollers', 'Car Seats', 'Toys', 'School Bags',
        'Kids Furniture', 'Baby Feeding', 'Maternity', 'Baby Skincare',
        'Kids Shoes', 'Learning Materials',
    ],
    'Health & Wellness': [
        'Vitamins', 'Supplements', 'Medical Devices', 'First Aid', 'Fitness Nutrition',
        'Personal Hygiene', 'Mobility Aids', 'Health Monitors', 'Massage Products',
        'Eye Care', 'Dental Care', 'Wellness Herbs',
    ],
    'Sports & Fitness': [
        'Gym Equipment', 'Activewear', 'Football Gear', 'Basketball Gear',
        'Cycling Gear', 'Yoga & Pilates', 'Swimming Gear', 'Outdoor Sports',
        'Treadmills', 'Weights', 'Sports Shoes', 'Camping Gear',
    ],
    'Books & Stationery': [
        'Textbooks', 'Novels', 'Children Books', 'Office Stationery',
        'School Supplies', 'Art Supplies', 'Notebooks', 'Printers Paper',
        'Educational Materials', 'Religious Books', 'Exam Prep', 'Writing Tools',
    ],
    'Services': [
        'Repairs', 'Cleaning Services', 'Beauty Services', 'Tutoring',
        'Logistics', 'Event Services', 'Photography Services', 'Home Installation',
        'Vehicle Services', 'Business Services', 'Freelance Services', 'Rentals',
    ],
    'Agriculture': [
        'Seeds', 'Fertilizers', 'Farm Tools', 'Poultry', 'Livestock', 'Fishery',
        'Animal Feed', 'Irrigation', 'Farm Machinery', 'Agro Chemicals',
        'Harvested Crops', 'Greenhouse Supplies',
    ],
    'Industrial & Business': [
        'Office Equipment', 'Restaurant Equipment', 'POS Hardware',
        'Packaging Materials', 'Cleaning Supplies', 'Industrial Machines',
        'Generators Industrial', 'Safety Industrial', 'Warehouse Supplies',
        'Printing Equipment', 'Salon Equipment', 'Retail Fixtures',
    ],
    'Others': [
        'Gifts', 'Collectibles', 'Musical Instruments', 'Pet Supplies',
        'Travel Accessories', 'Religious Items', 'Party Supplies',
        'Security Services', 'Digital Products', 'Miscellaneous', 'Local Crafts',
        'Seasonal Items',
    ],
}

GENERIC_FAMILY_SUFFIXES = [
    'Standard', 'Premium', 'Budget', 'Wholesale', 'Replacement', 'Professional',
]

BRANDS = [
    'ZuntoChoice', 'PrimeMart', 'UrbanLine', 'ValueHub', 'Nova', 'Royal',
    'Swift', 'Evergreen', 'MaxPro', 'BluePeak', 'Natura', 'HarvestChoice',
    'TechPoint', 'HomeEase', 'AutoSure', 'BuildRight',
]

LOCATIONS = [
    ('Lagos', 'Ikeja', 'Computer Village'),
    ('Lagos', 'Yaba', 'Sabo'),
    ('Lagos', 'Lekki', 'Phase 1'),
    ('Abuja', 'Wuse', 'Zone 4'),
    ('Abuja', 'Garki', 'Area 11'),
    ('Rivers', 'Port Harcourt', 'GRA Phase 2'),
    ('Oyo', 'Ibadan', 'Bodija'),
    ('Kano', 'Kano Municipal', 'Sabon Gari'),
    ('Enugu', 'Enugu North', 'New Haven'),
    ('Kaduna', 'Kaduna North', 'Central Market'),
]


def dumps_pretty(payload: Dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def _schema_profile(top_name: str, sub_name: str) -> List[Dict]:
    lower = f'{top_name} {sub_name}'.lower()
    if 'phone' in lower or 'tablet' in lower:
        keys = [
            ('model', 'Model', 'text', True), ('storage', 'Storage', 'select', True),
            ('ram', 'RAM', 'select', False), ('battery_health', 'Battery health', 'number', False),
            ('network', 'Network lock', 'select', True), ('color', 'Colour', 'text', False),
            ('screen_size', 'Screen size', 'decimal', False), ('accessories', 'Accessories', 'list', False),
            ('warranty', 'Warranty', 'text', False), ('sim_slots', 'SIM slots', 'number', False),
            ('charger_type', 'Charger type', 'text', False), ('os_version', 'OS version', 'text', False),
        ]
    elif any(term in lower for term in ['grocery', 'food', 'rice', 'grain', 'agriculture', 'baby food']):
        keys = [
            ('variety', 'Variety', 'text', True), ('weight', 'Weight', 'text', True),
            ('pack_size', 'Pack size', 'text', True), ('expiry_date', 'Expiry date', 'date', False),
            ('origin', 'Origin', 'text', False), ('grade', 'Grade', 'text', False),
            ('organic', 'Organic', 'boolean', False), ('wholesale_available', 'Wholesale available', 'boolean', False),
            ('storage_instruction', 'Storage instruction', 'text', False), ('unit_count', 'Unit count', 'number', False),
            ('dietary_tags', 'Dietary tags', 'list', False), ('production_date', 'Production date', 'date', False),
        ]
    elif any(term in lower for term in ['shoe', 'fashion', 'clothing', 'wear']):
        keys = [
            ('size', 'Size', 'text', True), ('gender', 'Gender', 'select', False),
            ('color', 'Colour', 'text', True), ('material', 'Material', 'text', False),
            ('style', 'Style', 'text', False), ('fit', 'Fit', 'text', False),
            ('occasion', 'Occasion', 'text', False), ('season', 'Season', 'text', False),
            ('care_instruction', 'Care instruction', 'text', False), ('country_size', 'Country size system', 'text', False),
            ('heel_height', 'Heel height', 'text', False), ('closure_type', 'Closure type', 'text', False),
        ]
    elif any(term in lower for term in ['beauty', 'skincare', 'sunscreen', 'health']):
        keys = [
            ('skin_type', 'Skin type', 'text', False), ('spf', 'SPF', 'number', False),
            ('volume', 'Volume', 'text', True), ('ingredient_highlight', 'Key ingredient', 'text', False),
            ('use_case', 'Use case', 'text', True), ('expiry_date', 'Expiry date', 'date', False),
            ('scent', 'Scent', 'text', False), ('finish', 'Finish', 'text', False),
            ('age_group', 'Age group', 'text', False), ('pack_size', 'Pack size', 'text', False),
            ('nafdac_status', 'NAFDAC status', 'text', False), ('suitable_for', 'Suitable for', 'text', False),
        ]
    elif any(term in lower for term in ['building', 'tools', 'fastener', 'nail', 'auto parts']):
        keys = [
            ('material', 'Material', 'text', True), ('length', 'Length', 'text', False),
            ('gauge', 'Gauge', 'text', False), ('head_type', 'Head type', 'text', False),
            ('coating', 'Coating', 'text', False), ('quantity_per_pack', 'Quantity per pack', 'number', True),
            ('use_case', 'Use case', 'text', True), ('compatibility', 'Compatibility', 'text', False),
            ('standard', 'Standard', 'text', False), ('package_weight', 'Package weight', 'text', False),
            ('corrosion_resistant', 'Corrosion resistant', 'boolean', False), ('warranty', 'Warranty', 'text', False),
        ]
    elif any(term in lower for term in ['vehicle', 'car', 'motorcycle']):
        keys = [
            ('make', 'Make', 'text', True), ('model', 'Model', 'text', True),
            ('year', 'Year', 'number', True), ('mileage', 'Mileage', 'number', False),
            ('transmission', 'Transmission', 'select', False), ('fuel_type', 'Fuel type', 'select', False),
            ('engine_size', 'Engine size', 'text', False), ('color', 'Colour', 'text', False),
            ('registered', 'Registered', 'boolean', False), ('service_history', 'Service history', 'text', False),
            ('body_type', 'Body type', 'text', False), ('vin_available', 'VIN available', 'boolean', False),
        ]
    else:
        keys = [
            ('brand', 'Brand', 'text', False), ('model', 'Model', 'text', False),
            ('material', 'Material', 'text', False), ('color', 'Colour', 'text', False),
            ('size', 'Size', 'text', False), ('capacity', 'Capacity', 'text', False),
            ('use_case', 'Use case', 'text', True), ('compatibility', 'Compatibility', 'text', False),
            ('pack_size', 'Pack size', 'text', False), ('warranty', 'Warranty', 'text', False),
            ('origin', 'Origin', 'text', False), ('included_items', 'Included items', 'list', False),
        ]
    return [
        {
            'key': key,
            'label': label,
            'value_type': value_type,
            'required': required,
            'order': index,
            'seller_prompt': f'Enter {label.lower()} for this product.',
            'examples': [],
            'search_weight': Decimal('1.50') if required else Decimal('1.00'),
            'filterable': True,
            'comparable': value_type in {'number', 'decimal'},
        }
        for index, (key, label, value_type, required) in enumerate(keys, start=1)
    ]


def _ensure_categories() -> Tuple[Dict[str, Category], List[Category]]:
    top_categories = {}
    subcategories = []
    for top_order, top_name in enumerate(TOP_CATEGORIES, start=1):
        top, _ = Category.objects.update_or_create(
            name=top_name,
            defaults={
                'description': f'{top_name} marketplace category for scaled recommender testing.',
                'icon': 'box',
                'parent': None,
                'is_active': True,
                'order': top_order,
            },
        )
        top_categories[top_name] = top
        for sub_order, sub_name in enumerate(SUBCATEGORY_BANK[top_name], start=1):
            sub, _ = Category.objects.update_or_create(
                name=sub_name,
                defaults={
                    'description': f'{sub_name} under {top_name}.',
                    'icon': 'tag',
                    'parent': top,
                    'is_active': True,
                    'order': sub_order,
                },
            )
            subcategories.append(sub)
    return top_categories, subcategories


def _ensure_product_families(top_categories: Dict[str, Category]) -> List[ProductFamily]:
    families = []
    for top_name, sub_names in SUBCATEGORY_BANK.items():
        top = top_categories[top_name]
        for sub_name in sub_names:
            sub = Category.objects.get(name=sub_name)
            for index, suffix in enumerate(GENERIC_FAMILY_SUFFIXES, start=1):
                family_name = f'{sub_name} {suffix}'
                family, _ = ProductFamily.objects.update_or_create(
                    top_category=top,
                    subcategory=sub,
                    slug=slugify(family_name),
                    defaults={
                        'name': family_name,
                        'description': f'{family_name} listings in {sub_name}.',
                        'aliases': [sub_name, family_name.replace('&', 'and')],
                        'keywords': [top_name, sub_name, suffix, family_name],
                        'is_active': True,
                        'order': index,
                    },
                )
                families.append(family)
    return families


def _ensure_attribute_schemas(families: Iterable[ProductFamily]) -> int:
    count = 0
    for family in families:
        top_name = family.top_category.name
        sub_name = family.subcategory.name if family.subcategory_id else ''
        for spec in _schema_profile(top_name, sub_name):
            ProductAttributeSchema.objects.update_or_create(
                product_family=family,
                key=spec['key'],
                defaults={
                    'label': spec['label'],
                    'value_type': spec['value_type'],
                    'required': spec['required'],
                    'options': spec.get('options', []),
                    'unit': spec.get('unit', ''),
                    'seller_prompt': spec['seller_prompt'],
                    'examples': spec.get('examples', []),
                    'search_weight': spec['search_weight'],
                    'filterable': spec['filterable'],
                    'comparable': spec['comparable'],
                    'order': spec['order'],
                    'is_active': True,
                },
            )
            count += 1
    return count


def _ensure_locations() -> List[Location]:
    locations = []
    for state, city, area in LOCATIONS:
        location, _ = Location.objects.get_or_create(
            state=state,
            city=city,
            area=area,
            defaults={'is_active': True},
        )
        locations.append(location)
    return locations


def _ensure_sellers(locations: List[Location], seller_count: int) -> List[User]:
    sellers = []
    for index in range(1, seller_count + 1):
        location = locations[(index - 1) % len(locations)]
        email = f'scale-seller-{index:02d}{SCALE_SELLER_DOMAIN}'
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': f'Scale{index:02d}',
                'last_name': 'Seller',
                'role': 'seller',
                'is_seller': True,
                'is_verified': True,
                'is_verified_seller': True,
                'seller_commerce_mode': 'managed',
                'city': location.city,
                'state': location.state,
                'country': 'Nigeria',
                'bio': 'Fake seller account for large-scale recommender testing.',
            },
        )
        if created:
            user.set_password(SCALE_PASSWORD)
            user.save(update_fields=['password'])
        SellerProfile.objects.update_or_create(
            user=user,
            defaults={
                'status': SellerProfile.STATUS_APPROVED,
                'is_verified_seller': True,
                'verified': True,
                'seller_commerce_mode': 'managed',
                'active_location': location,
                'rating': round(4.0 + (index % 10) / 10, 2),
                'total_reviews': 10 + index,
                'ai_memory': {
                    'dataset_label': SCALE_DATASET_LABEL,
                    'fake_demo_data': True,
                },
            },
        )
        sellers.append(user)
    return sellers


def _value_for_attribute(key: str, index: int) -> str:
    values = {
        'model': f'Model {index % 40 + 1}',
        'storage': ['64GB', '128GB', '256GB', '512GB'][index % 4],
        'ram': ['4GB', '8GB', '16GB', '32GB'][index % 4],
        'battery_health': f'{82 + index % 18}%',
        'network': ['unlocked', 'locked'][index % 2],
        'color': ['black', 'white', 'blue', 'red', 'silver'][index % 5],
        'size': ['S', 'M', 'L', 'XL', '42', '43'][index % 6],
        'weight': ['500g', '1kg', '5kg', '25kg', '50kg'][index % 5],
        'volume': ['100ml', '250ml', '500ml', '1L', '25L'][index % 5],
        'pack_size': ['single', 'pack of 3', 'pack of 6', 'carton'][index % 4],
        'quantity_per_pack': str(50 + (index % 20) * 25),
        'length': ['1 inch', '2 inch', '3 inch', '50mm', '100mm'][index % 5],
        'material': ['steel', 'cotton', 'leather', 'plastic', 'wood'][index % 5],
        'use_case': ['home', 'office', 'school', 'professional', 'wholesale'][index % 5],
        'year': str(2012 + index % 13),
        'mileage': str(10000 + index * 77),
    }
    return values.get(key, f'{key.replace("_", " ").title()} {index % 9 + 1}')


def _attributes_for_family(family: ProductFamily, index: int) -> Dict:
    attrs = {
        'dataset_label': SCALE_DATASET_LABEL,
        'seed_index': index,
        'fake_demo_data': True,
        'product_family': family.name.lower(),
        'taxonomy_path': family.get_full_path(),
    }
    schemas = family.attribute_schemas.filter(is_active=True).order_by('order', 'key')
    for schema in schemas:
        attrs[schema.key] = _value_for_attribute(schema.key, index)
    return attrs


def _price_for_family(family: ProductFamily, index: int) -> Decimal:
    top = family.top_category.name.lower()
    if any(term in top for term in ['vehicle']):
        base = 850000
    elif any(term in top for term in ['phone', 'computer', 'electronics', 'appliance']):
        base = 45000
    elif any(term in top for term in ['building', 'industrial']):
        base = 8000
    elif any(term in top for term in ['grocery', 'agriculture']):
        base = 3500
    else:
        base = 2500
    return Decimal(base + (index % 97) * (base // 9 + 750)).quantize(Decimal('1.00'))


def _build_product_title(family: ProductFamily, index: int) -> str:
    brand = BRANDS[index % len(BRANDS)]
    variant = ['Classic', 'Plus', 'Max', 'Lite', 'Pro'][index % 5]
    return f'{brand} {family.name} {variant} #{index:04d}'


def _seed_products(
    families: List[ProductFamily],
    sellers: List[User],
    locations: List[Location],
    product_count: int,
    rebuild_embeddings: bool,
) -> Tuple[int, Dict[str, int]]:
    rng = random.Random(20260430)
    embedding_summary = {'rebuilt': 0, 'empty': 0, 'failed': 0}
    created_products = []

    for index in range(1, product_count + 1):
        family = families[(index - 1) % len(families)]
        seller = sellers[(index - 1) % len(sellers)]
        location = locations[(index - 1) % len(locations)]
        brand = BRANDS[index % len(BRANDS)]
        title = _build_product_title(family, index)
        attrs = _attributes_for_family(family, index)
        description = (
            f'{title} in {family.get_full_path()}. '
            f"Specs: {'; '.join(f'{k}: {v}' for k, v in list(attrs.items())[5:12])}."
        )
        suggestion = suggest_product_metadata(
            title=title,
            description=description,
            category=family.subcategory or family.top_category,
            product_family=family,
            brand=brand,
        )
        tags = sorted(set(suggestion['search_tags'] + family.keywords + [brand, family.name]))
        product, _ = Product.objects.update_or_create(
            seller=seller,
            title=title,
            defaults={
                'description': description,
                'listing_type': 'product',
                'category': family.subcategory or family.top_category,
                'product_family': family,
                'location': location,
                'price': _price_for_family(family, index),
                'negotiable': bool(index % 3 == 0),
                'condition': ['new', 'like_new', 'good', 'fair'][index % 4],
                'brand': brand,
                'quantity': 1 + rng.randint(0, 30),
                'status': 'active',
                'is_featured': bool(index % 43 == 0),
                'is_boosted': bool(index % 37 == 0),
                'is_verified': True,
                'is_verified_product': bool(index % 11 != 0),
                'attributes': attrs,
                'search_tags': tags[:30],
                'attributes_verified': bool(index % 7 != 0),
                'views_count': 20 + index % 500,
                'favorites_count': index % 80,
                'shares_count': index % 20,
            },
        )
        created_products.append(product)

    # -------------------------------------------------------------------------
    # CHANGED: replace the per-product encode loop with a single batch call.
    #
    # Previous code called generate_product_embedding(product) once per product
    # inside a for-loop, which triggered _encode_single() 1,000+ times and
    # produced "Batches: 1/1" in the SentenceTransformers log for every product.
    #
    # New code:
    #   1. Re-fetches all created products with select_related to avoid N+1
    #      queries inside _build_product_embedding_text (which accesses
    #      .category, .product_family, and .location on every product).
    #   2. Builds all embedding texts in one Python loop (no DB hits).
    #   3. Calls _encode_batch() once — one model.encode() call for all products.
    #   4. Writes all vectors with bulk_update (one SQL statement) and
    #      bulk_sync_product_vectors (one write-lock acquisition for sqlite_vec,
    #      one cursor block for pgvector).
    # -------------------------------------------------------------------------
    if rebuild_embeddings and created_products:
        from market.search.embeddings import _build_product_embedding_text, _encode_batch
        from market.search.vector_backend import bulk_sync_product_vectors

        # Re-fetch with related objects to avoid N+1 queries inside
        # _build_product_embedding_text, which accesses .category,
        # .product_family, and .location on each product.
        # The objects returned from update_or_create above do not
        # have those relations prefetched.
        created_ids = [p.pk for p in created_products]
        products_with_related = list(
            Product.objects.filter(pk__in=created_ids)
            .select_related('category', 'product_family', 'location')
        )

        try:
            texts = [_build_product_embedding_text(p) for p in products_with_related]

            # ONE model.encode() call for the entire seed run
            vectors = _encode_batch(texts)

            valid_pairs = []
            for product, text, vector in zip(products_with_related, texts, vectors):
                if text.strip() and vector:
                    product.embedding_vector = vector
                    valid_pairs.append((product, vector))
                    embedding_summary['rebuilt'] += 1
                else:
                    embedding_summary['empty'] += 1

            if valid_pairs:
                # One SQL UPDATE for all products — bypasses Product.save()
                # intentionally (slug and location logic must not re-run here)
                Product.objects.bulk_update(
                    [p for p, _ in valid_pairs],
                    ['embedding_vector'],
                    batch_size=500,
                )
                # One write-lock acquisition for the entire batch
                bulk_sync_product_vectors(valid_pairs)

        except Exception as exc:
            # Roll up failures — individual product errors are visible in logs
            # from _encode_batch's own fallback warnings
            already_counted = embedding_summary['rebuilt'] + embedding_summary['empty']
            embedding_summary['failed'] += max(len(created_products) - already_counted, 1)
            embedding_summary['rebuilt'] = 0
            embedding_summary['empty'] = 0

    return len(created_products), embedding_summary


def seeded_scale_queryset():
    return Product.objects.filter(attributes__dataset_label=SCALE_DATASET_LABEL)


SCALE_EVAL_CASES = [
    {
        'name': 'budget phones',
        'slots': {'product_type': 'iPhones', 'category': 'Phones & Tablets', 'price_max': 400000},
        'must_contain': ['iphone'],
    },
    {
        'name': 'beauty sunscreen',
        'slots': {'product_type': 'Sunscreen', 'category': 'Beauty & Personal Care'},
        'must_contain': ['sunscreen'],
    },
    {
        'name': 'groceries rice',
        'slots': {'product_type': 'Rice & Grains', 'category': 'Groceries & Food'},
        'must_contain': ['rice'],
    },
    {
        'name': 'shoes sneakers',
        'slots': {'product_type': 'Sneakers', 'category': 'Shoes & Footwear', 'attributes': {'size': '42'}},
        'must_contain': ['sneaker'],
    },
    {
        'name': 'building nails',
        'slots': {'product_type': 'Fasteners & Nails', 'category': 'Building Materials & Tools'},
        'must_contain': ['nail', 'fastener'],
    },
    {
        'name': 'vehicle parts',
        'slots': {'product_type': 'Brake Parts', 'category': 'Auto Parts'},
        'must_contain': ['brake'],
    },
]


def _product_blob(product: Product) -> str:
    attrs = product.attributes if isinstance(product.attributes, dict) else {}
    return ' '.join([
        product.title or '',
        product.description or '',
        product.brand or '',
        product.category.name if product.category_id else '',
        product.product_family.name if product.product_family_id else '',
        ' '.join(str(tag) for tag in (product.search_tags or [])),
        json.dumps(attrs, sort_keys=True),
    ]).lower()


def run_scale_recommender_eval(top_k: int = 5) -> Dict:
    from assistant.services.recommendation_service import RecommendationService

    base_queryset = seeded_scale_queryset().filter(status='active')
    results = []
    for case in SCALE_EVAL_CASES:
        products = RecommendationService._find_products(
            case['slots'],
            top_k=top_k,
            base_queryset=base_queryset,
        )
        serialized = []
        top3_relevant = 0
        price_ok = 0
        for product in products:
            blob = _product_blob(product)
            relevant = any(term in blob for term in case['must_contain'])
            budget_ok = (
                case['slots'].get('price_max') is None
                or product.price <= Decimal(str(case['slots']['price_max']))
            )
            if len(serialized) < 3 and relevant:
                top3_relevant += 1
            price_ok += int(budget_ok)
            serialized.append({
                'id': str(product.id),
                'title': product.title,
                'price': float(product.price),
                'product_family': product.product_family.name if product.product_family_id else '',
                'category': product.category.name if product.category_id else '',
                'relevant': relevant,
                'budget_ok': budget_ok,
                'score_components': getattr(product, 'recommendation_score_components', {}) or {},
                'match_reasons': getattr(product, 'recommendation_match_reasons', []) or [],
            })
        passed = bool(serialized) and top3_relevant >= min(2, len(serialized[:3])) and price_ok == len(serialized)
        results.append({
            'name': case['name'],
            'passed': passed,
            'top3_relevant': top3_relevant,
            'result_count': len(serialized),
            'results': serialized,
        })

    passed = sum(1 for result in results if result['passed'])
    total = len(results)
    return {
        'dataset_label': SCALE_DATASET_LABEL,
        'total': total,
        'passed': passed,
        'failed': total - passed,
        'pass_rate_percent': round((passed / total) * 100, 2) if total else 0.0,
        'results': results,
    }


def clear_scale_seed_data() -> Dict[str, int]:
    products = seeded_scale_queryset()
    product_count = products.count()
    products.delete()
    user_count = User.objects.filter(email__endswith=SCALE_SELLER_DOMAIN).count()
    User.objects.filter(email__endswith=SCALE_SELLER_DOMAIN).delete()
    return {'products_deleted': product_count, 'users_deleted': user_count}


@transaction.atomic
def seed_taxonomy_scale_catalog(
    *,
    reset: bool = False,
    product_count: int = 1000,
    seller_count: int = 20,
    rebuild_embeddings: bool = False,
) -> Dict:
    cleared = {'products_deleted': 0, 'users_deleted': 0}
    if reset:
        cleared = clear_scale_seed_data()

    top_categories, subcategories = _ensure_categories()
    families = _ensure_product_families(top_categories)
    schema_count = _ensure_attribute_schemas(families)
    locations = _ensure_locations()
    sellers = _ensure_sellers(locations, seller_count)
    products, embeddings = _seed_products(
        families,
        sellers,
        locations,
        product_count,
        rebuild_embeddings,
    )

    return {
        'dataset_label': SCALE_DATASET_LABEL,
        'cleared': cleared,
        'top_categories': len(top_categories),
        'subcategories': len(subcategories),
        'product_families': len(families),
        'attribute_schemas': schema_count,
        'sellers': len(sellers),
        'products': products,
        'active_products': seeded_scale_queryset().filter(status='active').count(),
        'embeddings': embeddings,
    }