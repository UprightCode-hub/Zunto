import io
import json
from decimal import Decimal
from typing import Dict, Iterable, List, Optional

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import SellerProfile
from market.models import Category, Location, Product, ProductImage
from market.search.embeddings import generate_product_embedding

User = get_user_model()

DATASET_LABEL = 'zunto_recommender_eval_v1'
DEMO_TITLE_PREFIX = '[DEMO EVAL]'
SELLER_DOMAIN = '@zunto-reco-eval.local'
VERIFIER_EMAIL = f'recommender.verifier{SELLER_DOMAIN}'
PASSWORD = 'ZuntoRecoEval@2026!'
IMAGE_CAPTION_PREFIX = 'Zunto recommender eval image'


LOCATION_SPECS = {
    'lagos_ikeja': ('Lagos', 'Ikeja', 'Computer Village'),
    'lagos_yaba': ('Lagos', 'Yaba', 'Sabo'),
    'lagos_lekki': ('Lagos', 'Lekki', 'Phase 1'),
    'abuja_wuse': ('Abuja', 'Wuse', 'Zone 4'),
    'abuja_garki': ('Abuja', 'Garki', 'Area 11'),
    'rivers_ph': ('Rivers', 'Port Harcourt', 'GRA Phase 2'),
}

CATEGORY_SPECS = {
    'Phones': ('Smartphones, accessories, and mobile devices', 'phone'),
    'Beauty': ('Beauty, skincare, and grooming products', 'sparkles'),
    'Groceries': ('Packaged food, market staples, and bulk groceries', 'shopping-basket'),
    'Fashion': ('Clothing, bags, and fashion accessories', 'shirt'),
    'Shoes': ('Sneakers, formal shoes, sandals, and footwear', 'footprints'),
    'Electronics': ('Computers, audio gear, appliances, and gadgets', 'laptop'),
}

SELLER_SPECS = {
    'lagos_ikeja': ('Ada', 'Reco', 'ada.reco'),
    'lagos_yaba': ('Tunde', 'Reco', 'tunde.reco'),
    'lagos_lekki': ('Mariam', 'Reco', 'mariam.reco'),
    'abuja_wuse': ('Ibrahim', 'Reco', 'ibrahim.reco'),
    'abuja_garki': ('Kemi', 'Reco', 'kemi.reco'),
    'rivers_ph': ('Nneka', 'Reco', 'nneka.reco'),
}


def _attrs(eval_key: str, product_family: str, tags: Iterable[str], **extra) -> Dict:
    payload = {
        'dataset_label': DATASET_LABEL,
        'eval_key': eval_key,
        'product_family': product_family,
        'tags': sorted({str(tag).strip().lower() for tag in tags if str(tag).strip()}),
        'fake_demo_data': True,
    }
    payload.update(extra)
    return payload


PRODUCT_SPECS = [
    {
        'eval_key': 'iphone_11_budget_lagos',
        'title': f'{DEMO_TITLE_PREFIX} iPhone 11 128GB Budget Lagos',
        'description': 'Clearly labeled fake eval iPhone 11 with 128GB storage, unlocked network, and Lagos pickup.',
        'category': 'Phones',
        'location': 'lagos_yaba',
        'price': '185000.00',
        'condition': 'fair',
        'brand': 'Apple',
        'quantity': 4,
        'status': 'active',
        'attributes': _attrs(
            'iphone_11_budget_lagos',
            'iphone',
            ['phone', 'iphone', 'smartphone', '128gb', 'budget', 'lagos', 'fairly used'],
            model='iPhone 11',
            storage='128GB',
            network='unlocked',
            color='black',
        ),
    },
    {
        'eval_key': 'iphone_13_premium_lagos',
        'title': f'{DEMO_TITLE_PREFIX} iPhone 13 Pro 256GB Premium Lagos',
        'description': 'Clearly labeled fake eval premium iPhone 13 Pro with 256GB storage and verified seller.',
        'category': 'Phones',
        'location': 'lagos_lekki',
        'price': '630000.00',
        'condition': 'like_new',
        'brand': 'Apple',
        'quantity': 2,
        'status': 'active',
        'attributes': _attrs(
            'iphone_13_premium_lagos',
            'iphone',
            ['phone', 'iphone', 'smartphone', '256gb', 'premium', 'lagos', 'alternative'],
            model='iPhone 13 Pro',
            storage='256GB',
            network='unlocked',
            color='sierra blue',
        ),
    },
    {
        'eval_key': 'iphone_15_expensive_trap',
        'title': f'{DEMO_TITLE_PREFIX} iPhone 15 Pro Max Premium Trap',
        'description': 'Clearly labeled fake eval high-price iPhone control for budget-trap checks.',
        'category': 'Phones',
        'location': 'lagos_lekki',
        'price': '1650000.00',
        'condition': 'new',
        'brand': 'Apple',
        'quantity': 1,
        'status': 'active',
        'attributes': _attrs(
            'iphone_15_expensive_trap',
            'iphone',
            ['phone', 'iphone', 'smartphone', 'premium', 'budget-trap', 'lagos'],
            model='iPhone 15 Pro Max',
            storage='256GB',
        ),
    },
    {
        'eval_key': 'iphone_xr_out_of_stock_trap',
        'title': f'{DEMO_TITLE_PREFIX} iPhone XR Ultra Cheap Out Of Stock Trap',
        'description': 'Clearly labeled fake eval cheap iPhone that must not rank because stock is zero.',
        'category': 'Phones',
        'location': 'lagos_ikeja',
        'price': '75000.00',
        'condition': 'fair',
        'brand': 'Apple',
        'quantity': 0,
        'status': 'active',
        'attributes': _attrs(
            'iphone_xr_out_of_stock_trap',
            'iphone',
            ['phone', 'iphone', 'smartphone', 'cheap', 'out-of-stock', 'budget-trap'],
            model='iPhone XR',
            storage='64GB',
        ),
    },
    {
        'eval_key': 'samsung_a54_abuja',
        'title': f'{DEMO_TITLE_PREFIX} Samsung Galaxy A54 Abuja',
        'description': 'Clearly labeled fake eval Samsung A-series phone in Abuja for location alternatives.',
        'category': 'Phones',
        'location': 'abuja_wuse',
        'price': '290000.00',
        'condition': 'good',
        'brand': 'Samsung',
        'quantity': 3,
        'status': 'active',
        'attributes': _attrs(
            'samsung_a54_abuja',
            'android phone',
            ['phone', 'android', 'samsung', 'a54', 'abuja', 'alternative'],
            model='Galaxy A54',
            storage='128GB',
        ),
    },
    {
        'eval_key': 'sunscreen_spf50_lagos',
        'title': f'{DEMO_TITLE_PREFIX} SPF 50 Sunscreen Gel Lagos',
        'description': 'Clearly labeled fake eval broad spectrum SPF 50 sunscreen for face and body in Lagos.',
        'category': 'Beauty',
        'location': 'lagos_ikeja',
        'price': '15000.00',
        'condition': 'new',
        'brand': 'SkinSafe',
        'quantity': 12,
        'status': 'active',
        'attributes': _attrs(
            'sunscreen_spf50_lagos',
            'sunscreen',
            ['beauty', 'skincare', 'sunscreen', 'spf50', 'spf 50', 'lagos'],
            spf='50',
            skin_type='all skin types',
        ),
    },
    {
        'eval_key': 'hair_growth_oil_lagos_control',
        'title': f'{DEMO_TITLE_PREFIX} Rosemary Hair Growth Oil Lagos Control',
        'description': 'Clearly labeled fake eval beauty haircare control for category boundary checks.',
        'category': 'Beauty',
        'location': 'lagos_ikeja',
        'price': '12000.00',
        'condition': 'new',
        'brand': 'RootGlow',
        'quantity': 10,
        'status': 'active',
        'attributes': _attrs(
            'hair_growth_oil_lagos_control',
            'hair oil',
            ['beauty', 'haircare', 'oil', 'control', 'lagos'],
            volume='250ml',
        ),
    },
    {
        'eval_key': 'shea_butter_abuja',
        'title': f'{DEMO_TITLE_PREFIX} Raw Shea Butter 1kg Abuja',
        'description': 'Clearly labeled fake eval raw shea butter beauty alternative in Abuja.',
        'category': 'Beauty',
        'location': 'abuja_garki',
        'price': '9800.00',
        'condition': 'new',
        'brand': 'Natura',
        'quantity': 18,
        'status': 'active',
        'attributes': _attrs(
            'shea_butter_abuja',
            'shea butter',
            ['beauty', 'skincare', 'shea butter', 'abuja', 'alternative'],
            weight='1kg',
        ),
    },
    {
        'eval_key': 'basmati_rice_50kg_lagos',
        'title': f'{DEMO_TITLE_PREFIX} Premium Basmati Rice 50kg Lagos',
        'description': 'Clearly labeled fake eval 50kg premium basmati rice bag for grocery retrieval.',
        'category': 'Groceries',
        'location': 'lagos_yaba',
        'price': '65000.00',
        'condition': 'new',
        'brand': 'HarvestChoice',
        'quantity': 20,
        'status': 'active',
        'attributes': _attrs(
            'basmati_rice_50kg_lagos',
            'basmati rice',
            ['groceries', 'rice', 'basmati', '50kg', 'bulk', 'lagos'],
            variety='basmati',
            weight='50kg',
        ),
    },
    {
        'eval_key': 'long_grain_rice_25kg_abuja_control',
        'title': f'{DEMO_TITLE_PREFIX} Long Grain Rice 25kg Abuja Control',
        'description': 'Clearly labeled fake eval rice control outside Lagos and below requested pack size.',
        'category': 'Groceries',
        'location': 'abuja_wuse',
        'price': '29000.00',
        'condition': 'new',
        'brand': 'HarvestChoice',
        'quantity': 15,
        'status': 'active',
        'attributes': _attrs(
            'long_grain_rice_25kg_abuja_control',
            'rice',
            ['groceries', 'rice', 'long grain', '25kg', 'abuja', 'control'],
            variety='long grain',
            weight='25kg',
        ),
    },
    {
        'eval_key': 'palm_oil_rivers',
        'title': f'{DEMO_TITLE_PREFIX} Red Palm Oil 25L Port Harcourt',
        'description': 'Clearly labeled fake eval grocery alternative for non-rice category checks.',
        'category': 'Groceries',
        'location': 'rivers_ph',
        'price': '24000.00',
        'condition': 'new',
        'brand': 'DeltaFresh',
        'quantity': 30,
        'status': 'active',
        'attributes': _attrs(
            'palm_oil_rivers',
            'palm oil',
            ['groceries', 'palm oil', '25l', 'port harcourt'],
            volume='25L',
        ),
    },
    {
        'eval_key': 'nike_sneaker_42_abuja',
        'title': f'{DEMO_TITLE_PREFIX} Nike Running Sneaker Size 42 Abuja',
        'description': 'Clearly labeled fake eval Nike running sneaker size 42 in Abuja.',
        'category': 'Shoes',
        'location': 'abuja_wuse',
        'price': '58000.00',
        'condition': 'good',
        'brand': 'Nike',
        'quantity': 5,
        'status': 'active',
        'attributes': _attrs(
            'nike_sneaker_42_abuja',
            'sneaker',
            ['shoes', 'sneaker', 'nike', 'running', 'size 42', 'abuja', 'affordable'],
            size='42',
            color='white',
            use_case='running',
        ),
    },
    {
        'eval_key': 'adidas_sneaker_43_lagos_control',
        'title': f'{DEMO_TITLE_PREFIX} Adidas Sneaker Size 43 Lagos Control',
        'description': 'Clearly labeled fake eval Adidas footwear control with wrong size and higher price in Lagos.',
        'category': 'Shoes',
        'location': 'lagos_ikeja',
        'price': '70000.00',
        'condition': 'good',
        'brand': 'Adidas',
        'quantity': 2,
        'status': 'active',
        'attributes': _attrs(
            'adidas_sneaker_43_lagos_control',
            'sneaker',
            ['shoes', 'sneaker', 'adidas', 'size 43', 'lagos', 'control'],
            size='43',
            color='black',
        ),
    },
    {
        'eval_key': 'formal_shoe_42_lagos_control',
        'title': f'{DEMO_TITLE_PREFIX} Oxford Formal Shoe Size 42 Lagos Control',
        'description': 'Clearly labeled fake eval formal footwear control in size 42.',
        'category': 'Shoes',
        'location': 'lagos_ikeja',
        'price': '52000.00',
        'condition': 'good',
        'brand': 'Bata',
        'quantity': 4,
        'status': 'active',
        'attributes': _attrs(
            'formal_shoe_42_lagos_control',
            'formal shoe',
            ['shoes', 'formal shoe', 'oxford', 'size 42', 'lagos', 'control'],
            size='42',
            color='brown',
        ),
    },
    {
        'eval_key': 'ankara_dress_lagos',
        'title': f'{DEMO_TITLE_PREFIX} Ankara Midi Dress Lagos',
        'description': 'Clearly labeled fake eval Ankara midi dress for fashion retrieval.',
        'category': 'Fashion',
        'location': 'lagos_lekki',
        'price': '32000.00',
        'condition': 'new',
        'brand': 'Zunto Atelier',
        'quantity': 6,
        'status': 'active',
        'attributes': _attrs(
            'ankara_dress_lagos',
            'dress',
            ['fashion', 'dress', 'ankara', 'midi', 'lagos'],
            size='M',
            fabric='ankara',
        ),
    },
    {
        'eval_key': 'denim_jacket_abuja_control',
        'title': f'{DEMO_TITLE_PREFIX} Denim Jacket Abuja Control',
        'description': 'Clearly labeled fake eval fashion control that should not match dress-specific retrieval.',
        'category': 'Fashion',
        'location': 'abuja_garki',
        'price': '27000.00',
        'condition': 'like_new',
        'brand': 'UrbanLine',
        'quantity': 3,
        'status': 'active',
        'attributes': _attrs(
            'denim_jacket_abuja_control',
            'jacket',
            ['fashion', 'jacket', 'denim', 'abuja', 'control'],
            size='L',
        ),
    },
    {
        'eval_key': 'gaming_laptop_16gb_lagos',
        'title': f'{DEMO_TITLE_PREFIX} HP Victus Gaming Laptop 16GB Lagos',
        'description': 'Clearly labeled fake eval HP Victus gaming laptop with 16GB RAM, 512GB SSD, GTX graphics.',
        'category': 'Electronics',
        'location': 'lagos_ikeja',
        'price': '820000.00',
        'condition': 'good',
        'brand': 'HP',
        'quantity': 2,
        'status': 'active',
        'attributes': _attrs(
            'gaming_laptop_16gb_lagos',
            'gaming laptop',
            ['electronics', 'laptop', 'gaming laptop', '16gb ram', '512gb ssd', 'lagos'],
            ram='16GB',
            storage='512GB SSD',
            gpu='GTX 1650',
        ),
    },
    {
        'eval_key': 'gaming_laptop_8gb_unverified_control',
        'title': f'{DEMO_TITLE_PREFIX} Gaming Laptop 8GB Unverified Attr Control',
        'description': 'Clearly labeled fake eval gaming laptop control with unverified attributes.',
        'category': 'Electronics',
        'location': 'lagos_ikeja',
        'price': '620000.00',
        'condition': 'good',
        'brand': 'Dell',
        'quantity': 1,
        'status': 'active',
        'attributes_verified': False,
        'attributes': _attrs(
            'gaming_laptop_8gb_unverified_control',
            'gaming laptop',
            ['electronics', 'laptop', 'gaming laptop', '8gb ram', 'unverified', 'control'],
            ram='8GB',
            storage='256GB SSD',
        ),
    },
    {
        'eval_key': 'bluetooth_speaker_abuja',
        'title': f'{DEMO_TITLE_PREFIX} JBL Bluetooth Speaker Abuja',
        'description': 'Clearly labeled fake eval electronics alternative for non-laptop checks.',
        'category': 'Electronics',
        'location': 'abuja_wuse',
        'price': '95000.00',
        'condition': 'like_new',
        'brand': 'JBL',
        'quantity': 3,
        'status': 'active',
        'attributes': _attrs(
            'bluetooth_speaker_abuja',
            'bluetooth speaker',
            ['electronics', 'speaker', 'bluetooth', 'jbl', 'abuja'],
            battery_life='20 hours',
        ),
    },
    {
        'eval_key': 'drone_suspended_no_result_control',
        'title': f'{DEMO_TITLE_PREFIX} Camera Drone Suspended No Result Control',
        'description': 'Clearly labeled fake eval suspended drone listing for no-result checks.',
        'category': 'Electronics',
        'location': 'lagos_ikeja',
        'price': '450000.00',
        'condition': 'good',
        'brand': 'DJI',
        'quantity': 1,
        'status': 'suspended',
        'attributes': _attrs(
            'drone_suspended_no_result_control',
            'drone',
            ['electronics', 'drone', 'camera drone', 'suspended', 'no-result-control'],
        ),
    },
]


EVAL_CASES = [
    {
        'name': 'phones_budget_lagos',
        'slots': {
            'category': 'Phones',
            'product_type': 'iphone',
            'raw_query': 'i need a fairly used iphone in lagos under 250k',
            'price_max': 250000,
            'location': 'Lagos',
            'condition': 'fair',
        },
        'expect_any': ['iphone_11_budget_lagos'],
        'expect_none': ['iphone_15_expensive_trap', 'iphone_xr_out_of_stock_trap'],
    },
    {
        'name': 'phones_premium_lagos',
        'slots': {
            'category': 'Phones',
            'product_type': 'iphone',
            'raw_query': 'show premium iphone options in lagos',
            'location': 'Lagos',
            'price_intent': 'premium',
        },
        'expect_any': ['iphone_13_premium_lagos', 'iphone_15_expensive_trap'],
        'expect_none': ['iphone_xr_out_of_stock_trap'],
    },
    {
        'name': 'beauty_sunscreen_spf50',
        'slots': {
            'category': 'Beauty',
            'product_type': 'sunscreen',
            'raw_query': 'spf 50 sunscreen in lagos under 20k',
            'price_max': 20000,
            'location': 'Lagos',
            'condition': 'new',
            'attributes': {'spf': '50'},
        },
        'expect_any': ['sunscreen_spf50_lagos'],
        'expect_none': ['hair_growth_oil_lagos_control'],
    },
    {
        'name': 'groceries_basmati_50kg',
        'slots': {
            'category': 'Groceries',
            'product_type': 'basmati rice',
            'raw_query': '50kg premium basmati rice in lagos',
            'location': 'Lagos',
            'condition': 'new',
            'attributes': {'weight': '50kg'},
        },
        'expect_any': ['basmati_rice_50kg_lagos'],
        'expect_none': ['long_grain_rice_25kg_abuja_control'],
    },
    {
        'name': 'shoes_size_42_abuja',
        'slots': {
            'category': 'Shoes',
            'product_type': 'sneaker',
            'raw_query': 'affordable nike sneaker size 42 in abuja',
            'price_max': 65000,
            'location': 'Abuja',
            'condition': 'good',
            'brand': 'Nike',
            'attributes': {'size': '42'},
        },
        'expect_any': ['nike_sneaker_42_abuja'],
        'expect_none': ['adidas_sneaker_43_lagos_control', 'formal_shoe_42_lagos_control'],
    },
    {
        'name': 'fashion_ankara_dress',
        'slots': {
            'category': 'Fashion',
            'product_type': 'dress',
            'raw_query': 'ankara dress in lagos',
            'location': 'Lagos',
            'condition': 'new',
        },
        'expect_any': ['ankara_dress_lagos'],
        'expect_none': ['denim_jacket_abuja_control'],
    },
    {
        'name': 'electronics_gaming_laptop_16gb',
        'slots': {
            'category': 'Electronics',
            'product_type': 'gaming laptop',
            'raw_query': 'gaming laptop 16gb ram in lagos',
            'location': 'Lagos',
            'condition': 'good',
            'attributes': {'ram': '16GB'},
        },
        'expect_any': ['gaming_laptop_16gb_lagos'],
        'expect_none': ['gaming_laptop_8gb_unverified_control'],
    },
    {
        'name': 'no_result_drone',
        'slots': {
            'category': 'Electronics',
            'product_type': 'drone',
            'raw_query': 'camera drone in lagos',
            'location': 'Lagos',
        },
        'expect_empty': True,
    },
    {
        'name': 'budget_trap_too_cheap',
        'slots': {
            'category': 'Phones',
            'product_type': 'iphone',
            'raw_query': 'iphone in lagos under 80k',
            'price_max': 80000,
            'location': 'Lagos',
        },
        'expect_empty': True,
        'expect_none': ['iphone_xr_out_of_stock_trap', 'iphone_15_expensive_trap'],
    },
    {
        'name': 'location_sneaker_lagos_no_match',
        'slots': {
            'category': 'Shoes',
            'product_type': 'sneaker',
            'raw_query': 'nike sneaker size 42 in lagos under 65k',
            'price_max': 65000,
            'location': 'Lagos',
            'attributes': {'size': '42'},
        },
        'expect_empty': True,
        'expect_none': ['nike_sneaker_42_abuja', 'adidas_sneaker_43_lagos_control'],
    },
    {
        'name': 'iphone_alternatives',
        'mode': 'alternatives',
        'slots': {
            'category': 'Phones',
            'product_type': 'iphone',
            'raw_query': 'iphone in lagos under 80k',
            'price_max': 80000,
            'location': 'Lagos',
        },
        'expect_any': ['iphone_11_budget_lagos', 'iphone_13_premium_lagos'],
        'expect_none': ['iphone_xr_out_of_stock_trap'],
    },
]


def seeded_product_queryset():
    return Product.objects.filter(
        Q(attributes__dataset_label=DATASET_LABEL)
        | Q(title__startswith=DEMO_TITLE_PREFIX)
        | Q(seller__email__endswith=SELLER_DOMAIN)
    )


def _create_demo_image_bytes(seed: int, title: str) -> bytes:
    try:
        from PIL import Image, ImageDraw, ImageFont

        width, height = 900, 675
        palette = [
            (20, 92, 88),
            (123, 63, 0),
            (42, 83, 130),
            (95, 63, 128),
            (36, 99, 62),
            (135, 52, 61),
        ]
        background = palette[seed % len(palette)]
        accent = palette[(seed + 2) % len(palette)]
        image = Image.new('RGB', (width, height), background)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        draw.rectangle((36, 36, width - 36, height - 36), outline=(255, 255, 255), width=5)
        draw.rounded_rectangle((150, 170, width - 150, height - 210), radius=24, fill=accent)
        draw.rectangle((210, 230, width - 210, 290), fill=(255, 255, 255))
        draw.rectangle((210, 320, width - 260, 365), fill=(235, 235, 235))
        draw.rectangle((210, 395, width - 310, 435), fill=(220, 220, 220))
        draw.text((70, 78), 'Zunto recommender eval', fill=(255, 255, 255), font=font)
        draw.text((70, 112), title[:70], fill=(255, 255, 255), font=font)
        draw.text((70, height - 96), 'Fake demo media for retrieval and UI testing', fill=(255, 255, 255), font=font)

        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=82)
        return buffer.getvalue()
    except Exception:
        return (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00'
            b'\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x08\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\xff\xd9'
        )


def _seed_locations() -> Dict[str, Location]:
    locations = {}
    for key, (state, city, area) in LOCATION_SPECS.items():
        location, _ = Location.objects.update_or_create(
            state=state,
            city=city,
            area=area,
            defaults={'is_active': True},
        )
        locations[key] = location
    return locations


def _seed_categories() -> Dict[str, Category]:
    categories = {}
    for index, (name, (description, icon)) in enumerate(CATEGORY_SPECS.items(), start=1):
        category, _ = Category.objects.update_or_create(
            name=name,
            defaults={
                'description': description,
                'icon': icon,
                'is_active': True,
                'order': index,
            },
        )
        categories[name] = category
    return categories


def _seed_verifier() -> User:
    user, created = User.objects.get_or_create(
        email=VERIFIER_EMAIL,
        defaults={
            'first_name': 'Reco',
            'last_name': 'Verifier',
            'role': 'admin',
            'is_staff': True,
            'is_verified': True,
        },
    )
    if created:
        user.set_password(PASSWORD)
        user.save(update_fields=['password'])
    else:
        updates = {
            'first_name': 'Reco',
            'last_name': 'Verifier',
            'role': 'admin',
            'is_staff': True,
            'is_verified': True,
        }
        for field, value in updates.items():
            setattr(user, field, value)
        user.save(update_fields=[*updates.keys(), 'updated_at'])
    return user


def _seed_sellers(locations: Dict[str, Location]) -> Dict[str, User]:
    sellers = {}
    for key, (first_name, last_name, local_part) in SELLER_SPECS.items():
        location = locations[key]
        email = f'{local_part}{SELLER_DOMAIN}'
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'role': 'seller',
                'is_seller': True,
                'is_verified': True,
                'is_verified_seller': True,
                'seller_commerce_mode': 'managed',
                'city': location.city,
                'state': location.state,
                'country': 'Nigeria',
                'bio': f'{first_name} is a clearly labeled recommender eval seller.',
            },
        )
        if created:
            user.set_password(PASSWORD)
            user.save(update_fields=['password'])
        else:
            updates = {
                'first_name': first_name,
                'last_name': last_name,
                'role': 'seller',
                'is_seller': True,
                'is_verified': True,
                'is_verified_seller': True,
                'seller_commerce_mode': 'managed',
                'city': location.city,
                'state': location.state,
                'country': 'Nigeria',
                'bio': f'{first_name} is a clearly labeled recommender eval seller.',
            }
            for field, value in updates.items():
                setattr(user, field, value)
            user.save(update_fields=[*updates.keys(), 'updated_at'])

        SellerProfile.objects.update_or_create(
            user=user,
            defaults={
                'status': SellerProfile.STATUS_APPROVED,
                'is_verified_seller': True,
                'verified': True,
                'seller_commerce_mode': 'managed',
                'active_location': location,
                'rating': 4.7,
                'total_reviews': 32,
                'ai_memory': {
                    'dataset_label': DATASET_LABEL,
                    'fake_demo_data': True,
                },
            },
        )
        sellers[key] = user
    return sellers


def _ensure_seed_image(product: Product, image_seed: int) -> bool:
    caption = f'{IMAGE_CAPTION_PREFIX}: {product.attributes.get("eval_key", product.id)}'
    if ProductImage.objects.filter(product=product, caption=caption).exists():
        return False

    ProductImage.objects.filter(
        product=product,
        caption__startswith=IMAGE_CAPTION_PREFIX,
    ).delete()
    image_name = f'products/recommender_eval/{DATASET_LABEL}_{image_seed:03d}.jpg'
    storage = ProductImage._meta.get_field('image').storage
    try:
        if not storage.exists(image_name):
            storage.save(
                image_name,
                ContentFile(_create_demo_image_bytes(image_seed, product.title)),
            )
    except Exception:
        pass

    ProductImage.objects.create(
        product=product,
        image=image_name,
        caption=caption,
        order=0,
        is_primary=True,
    )
    return True


def _seed_products(
    sellers: Dict[str, User],
    categories: Dict[str, Category],
    locations: Dict[str, Location],
    verifier: User,
) -> List[Product]:
    products = []
    now = timezone.now()
    for index, spec in enumerate(PRODUCT_SPECS, start=1):
        attributes = dict(spec['attributes'])
        attributes_verified = bool(spec.get('attributes_verified', True))
        product, _ = Product.objects.update_or_create(
            seller=sellers[spec['location']],
            title=spec['title'],
            defaults={
                'description': spec['description'],
                'listing_type': 'product',
                'category': categories[spec['category']],
                'location': locations[spec['location']],
                'price': Decimal(spec['price']),
                'negotiable': bool(spec.get('negotiable', True)),
                'condition': spec['condition'],
                'brand': spec.get('brand', ''),
                'quantity': int(spec['quantity']),
                'status': spec['status'],
                'is_featured': bool(spec.get('is_featured', False)),
                'is_boosted': bool(spec.get('is_boosted', False)),
                'is_verified': bool(spec.get('is_verified', True)),
                'is_verified_product': bool(spec.get('is_verified_product', True)),
                'attributes': attributes,
                'attributes_verified': attributes_verified,
                'attributes_verified_at': now if attributes_verified else None,
                'attributes_verified_by': verifier if attributes_verified else None,
                'views_count': int(spec.get('views_count', 40 + index * 7)),
                'favorites_count': int(spec.get('favorites_count', 4 + index)),
                'shares_count': int(spec.get('shares_count', index % 5)),
            },
        )
        _ensure_seed_image(product, index)
        products.append(product)
    return products


def _rebuild_embeddings(products: Iterable[Product]) -> Dict[str, int]:
    rebuilt = 0
    empty = 0
    failed = 0

    for product in products:
        try:
            vector = generate_product_embedding(product)
            if vector:
                Product.objects.filter(pk=product.pk).update(embedding_vector=vector)
                rebuilt += 1
            else:
                Product.objects.filter(pk=product.pk).update(embedding_vector=[])
                empty += 1
        except Exception:
            Product.objects.filter(pk=product.pk).update(embedding_vector=[])
            failed += 1

    return {'rebuilt': rebuilt, 'empty': empty, 'failed': failed}


def clear_seeded_recommender_eval_data() -> Dict[str, int]:
    products = seeded_product_queryset()
    product_count = products.count()
    products.delete()
    user_count = User.objects.filter(email__endswith=SELLER_DOMAIN).count()
    User.objects.filter(email__endswith=SELLER_DOMAIN).delete()
    return {'products_deleted': product_count, 'users_deleted': user_count}


@transaction.atomic
def seed_recommender_eval_catalog(
    *,
    reset: bool = False,
    rebuild_embeddings: bool = True,
) -> Dict:
    cleared = {'products_deleted': 0, 'users_deleted': 0}
    if reset:
        cleared = clear_seeded_recommender_eval_data()

    locations = _seed_locations()
    categories = _seed_categories()
    verifier = _seed_verifier()
    sellers = _seed_sellers(locations)
    products = _seed_products(sellers, categories, locations, verifier)

    embedding_summary = {'rebuilt': 0, 'empty': 0, 'failed': 0}
    if rebuild_embeddings:
        embedding_summary = _rebuild_embeddings(products)

    active_seeded = seeded_product_queryset().filter(status='active')
    return {
        'dataset_label': DATASET_LABEL,
        'cleared': cleared,
        'locations': len(locations),
        'categories': len(categories),
        'sellers': len(sellers),
        'products': len(products),
        'active_products': active_seeded.count(),
        'images': ProductImage.objects.filter(product__in=seeded_product_queryset()).count(),
        'embeddings': embedding_summary,
    }


def _has_verified_seller(product: Product) -> bool:
    seller = getattr(product, 'seller', None)
    if seller is None:
        return False
    if getattr(seller, 'is_verified_seller', False):
        return True
    try:
        return bool(seller.seller_profile.is_verified_seller)
    except SellerProfile.DoesNotExist:
        return False


def _has_tags(attributes: Dict) -> bool:
    tags = (attributes or {}).get('tags')
    return isinstance(tags, list) and bool([tag for tag in tags if str(tag).strip()])


def _has_product_family(attributes: Dict) -> bool:
    return bool(str((attributes or {}).get('product_family') or '').strip())


def audit_product_recommendation_quality(queryset=None) -> Dict:
    queryset = queryset or Product.objects.filter(status='active')
    products = list(
        queryset.select_related('category', 'location', 'seller', 'seller__seller_profile')
        .prefetch_related('images')
    )
    total = len(products)

    checks = {
        'category': 0,
        'product_family': 0,
        'brand': 0,
        'condition': 0,
        'price': 0,
        'location': 0,
        'verified_seller': 0,
        'verified_product': 0,
        'stock': 0,
        'tags': 0,
        'attributes': 0,
        'images': 0,
        'embeddings': 0,
    }

    for product in products:
        attributes = product.attributes if isinstance(product.attributes, dict) else {}
        checks['category'] += int(bool(product.category_id))
        checks['product_family'] += int(_has_product_family(attributes))
        checks['brand'] += int(bool(str(product.brand or '').strip()))
        checks['condition'] += int(bool(str(product.condition or '').strip()))
        checks['price'] += int(product.price is not None and product.price > 0)
        checks['location'] += int(bool(product.location_id))
        checks['verified_seller'] += int(_has_verified_seller(product))
        checks['verified_product'] += int(bool(product.is_verified_product or product.is_verified))
        checks['stock'] += int(product.quantity > 0)
        checks['tags'] += int(_has_tags(attributes))
        checks['attributes'] += int(bool(attributes) and bool(product.attributes_verified))
        checks['images'] += int(bool(list(product.images.all())))
        checks['embeddings'] += int(bool(product.embedding_vector))

    coverage = {}
    for key, count in checks.items():
        coverage[key] = {
            'count': count,
            'total': total,
            'percent': round((count / total) * 100, 2) if total else 0.0,
        }

    score = round(
        sum(metric['percent'] for metric in coverage.values()) / len(coverage),
        2,
    ) if coverage else 0.0

    return {
        'total_products': total,
        'quality_score_percent': score,
        'coverage': coverage,
        'gaps': [
            key
            for key, metric in coverage.items()
            if total and metric['percent'] < 90.0
        ],
    }


def format_audit_report(audit: Dict) -> str:
    lines = [
        f"Products audited: {audit['total_products']}",
        f"Structured recommendation quality score: {audit['quality_score_percent']}%",
    ]
    for key, metric in audit['coverage'].items():
        lines.append(
            f"- {key}: {metric['count']}/{metric['total']} ({metric['percent']}%)"
        )
    if audit['gaps']:
        lines.append(f"Coverage gaps below 90%: {', '.join(audit['gaps'])}")
    else:
        lines.append("No coverage fields below the 90% threshold in this measured slice.")
    return '\n'.join(lines)


def _eval_key_to_product_ids() -> Dict[str, str]:
    products = seeded_product_queryset().only('id', 'attributes')
    mapping = {}
    for product in products:
        attributes = product.attributes if isinstance(product.attributes, dict) else {}
        eval_key = attributes.get('eval_key')
        if eval_key:
            mapping[str(eval_key)] = str(product.id)
    return mapping


def _serialize_eval_product(product: Product) -> Dict:
    attributes = product.attributes if isinstance(product.attributes, dict) else {}
    return {
        'id': str(product.id),
        'eval_key': attributes.get('eval_key', ''),
        'title': product.title,
        'price': float(product.price),
        'status': product.status,
        'quantity': product.quantity,
        'location': str(product.location) if product.location_id else '',
    }


def run_seeded_recommender_evals(top_k: int = 5) -> Dict:
    from assistant.services.recommendation_service import RecommendationService

    key_to_id = _eval_key_to_product_ids()
    base_queryset = seeded_product_queryset()
    results = []

    for case in EVAL_CASES:
        if case.get('mode') == 'alternatives':
            products = RecommendationService._find_alternatives(
                case['slots'],
                top_k=top_k,
                base_queryset=base_queryset,
            )
        else:
            products = RecommendationService._find_products(
                case['slots'],
                top_k=top_k,
                base_queryset=base_queryset,
            )

        product_ids = [str(product.id) for product in products]
        expected_ids = [key_to_id[key] for key in case.get('expect_any', []) if key in key_to_id]
        excluded_ids = [key_to_id[key] for key in case.get('expect_none', []) if key in key_to_id]
        foreign_results = [
            _serialize_eval_product(product)
            for product in products
            if not (isinstance(product.attributes, dict) and product.attributes.get('dataset_label') == DATASET_LABEL)
        ]

        expected_found = not expected_ids or any(product_id in product_ids for product_id in expected_ids)
        excluded_found = [product_id for product_id in excluded_ids if product_id in product_ids]
        empty_ok = not case.get('expect_empty') or not product_ids
        passed = bool(expected_found and not excluded_found and empty_ok)

        rank_gap = None
        if expected_ids and expected_found:
            first_rank = min(product_ids.index(product_id) + 1 for product_id in expected_ids if product_id in product_ids)
            if first_rank > 1:
                rank_gap = f"expected seeded product found at rank {first_rank}, not rank 1"

        results.append({
            'name': case['name'],
            'passed': passed,
            'mode': case.get('mode', 'direct'),
            'expected_found': expected_found,
            'excluded_found': excluded_found,
            'empty_ok': empty_ok,
            'rank_gap': rank_gap,
            'foreign_results': foreign_results,
            'results': [_serialize_eval_product(product) for product in products],
        })

    passed_count = sum(1 for result in results if result['passed'])
    total = len(results)
    return {
        'dataset_label': DATASET_LABEL,
        'total': total,
        'passed': passed_count,
        'failed': total - passed_count,
        'pass_rate_percent': round((passed_count / total) * 100, 2) if total else 0.0,
        'results': results,
        'remaining_gaps': [
            {
                'case': result['name'],
                'reason': (
                    'failed expected/excluded/empty check'
                    if not result['passed']
                    else result['rank_gap']
                    or 'non-seeded product appeared in seeded eval result set'
                ),
            }
            for result in results
            if (not result['passed']) or result['rank_gap'] or result['foreign_results']
        ],
    }


def dumps_pretty(payload: Dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
