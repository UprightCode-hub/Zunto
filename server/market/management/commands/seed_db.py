import io
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import SellerProfile
from assistant.models import ConversationSession, DemandCluster, UserBehaviorProfile
from cart.models import Cart, CartItem
from chat.models import Conversation, Message
from market.models import Category, Location, Product, ProductImage
from orders.models import Order, OrderItem, ShippingAddress
from reviews.models import ProductReview, SellerReview

User = get_user_model()

PASSWORD = 'ZuntoSeed@2026!'
SELLER_DOMAIN = '@zunto-demo.com'
BUYER_DOMAIN = '@zunto-buyer.com'

LOCATIONS = [
    ('Lagos', 'Ikeja', 'Allen Avenue'),
    ('Lagos', 'Eti-Osa', 'Lekki Phase 1'),
    ('Abuja', 'Garki', 'Area 11'),
    ('Rivers', 'Port Harcourt', 'GRA Phase 2'),
    ('Kano', 'Kano Municipal', 'Sabon Gari'),
    ('Oyo', 'Ibadan', 'Bodija'),
]

CATEGORIES = [
    {
        'name': 'Electronics',
        'description': 'Phones, laptops, gaming gear, and devices',
        'icon': 'phone',
        'products': [
            ('iPhone 15 Pro Max 256GB', Decimal('1650000.00'), 'new', 'Apple'),
            ('Samsung Galaxy S24 Ultra', Decimal('1420000.00'), 'new', 'Samsung'),
            ('HP Pavilion 15 Ryzen 7', Decimal('690000.00'), 'good', 'HP'),
            ('Sony PlayStation 5 Slim', Decimal('840000.00'), 'like_new', 'Sony'),
            ('Canon EOS M50 Kit', Decimal('520000.00'), 'good', 'Canon'),
            ('JBL Charge 5 Speaker', Decimal('135000.00'), 'like_new', 'JBL'),
        ],
    },
    {
        'name': 'Fashion & Clothing',
        'description': 'Apparel, shoes, bags, and accessories',
        'icon': 'shirt',
        'products': [
            ('Tailored Agbada Set Royal Blue', Decimal('65000.00'), 'like_new', ''),
            ('Ankara Two-Piece Event Set', Decimal('32000.00'), 'new', ''),
            ('Nike Air Force 1 White', Decimal('98000.00'), 'good', 'Nike'),
            ('Leather Office Handbag', Decimal('47000.00'), 'like_new', ''),
            ('Corporate Suit 3-Piece Charcoal', Decimal('118000.00'), 'new', ''),
            ('Unisex Streetwear Sneaker', Decimal('54000.00'), 'good', ''),
        ],
    },
    {
        'name': 'Home & Furniture',
        'description': 'Furniture, appliances, and decor',
        'icon': 'home',
        'products': [
            ('L-Shaped Living Room Sofa', Decimal('410000.00'), 'good', ''),
            ('6-Seater Dining Table Set', Decimal('355000.00'), 'like_new', ''),
            ('Standing Freezer 210L', Decimal('245000.00'), 'good', 'Hisense'),
            ('Executive Office Desk Set', Decimal('198000.00'), 'like_new', ''),
            ('Orthopedic Mattress 6x6', Decimal('165000.00'), 'new', ''),
            ('Industrial Gas Cooker 5 Burner', Decimal('132000.00'), 'new', ''),
        ],
    },
    {
        'name': 'Vehicles',
        'description': 'Cars, motorcycles, and spare parts',
        'icon': 'car',
        'products': [
            ('Toyota Camry 2018 XLE', Decimal('12800000.00'), 'good', 'Toyota'),
            ('Honda Accord 2016 Touring', Decimal('10500000.00'), 'good', 'Honda'),
            ('Bajaj Boxer Dispatch Bike', Decimal('720000.00'), 'good', 'Bajaj'),
            ('Lexus RX350 2015', Decimal('17500000.00'), 'fair', 'Lexus'),
            ('Hilux Pickup 2017 Diesel', Decimal('19800000.00'), 'good', 'Toyota'),
            ('SUV Brake Pad Set', Decimal('42000.00'), 'new', ''),
        ],
    },
    {
        'name': 'Food & Agriculture',
        'description': 'Farm produce, wholesale groceries, and packaged food',
        'icon': 'leaf',
        'products': [
            ('50kg Premium Basmati Rice', Decimal('58000.00'), 'new', ''),
            ('25L Organic Palm Oil', Decimal('21500.00'), 'new', ''),
            ('Fresh Roma Tomatoes Basket', Decimal('29000.00'), 'new', ''),
            ('Brown Beans 50kg Bag', Decimal('64500.00'), 'new', ''),
            ('Maize Grain Wholesale Sack', Decimal('38500.00'), 'new', ''),
            ('Processed Catfish Crate', Decimal('47000.00'), 'new', ''),
        ],
    },
    {
        'name': 'Health & Beauty',
        'description': 'Beauty products, supplements, and wellness items',
        'icon': 'sparkles',
        'products': [
            ('Vitamin C Brightening Serum', Decimal('14500.00'), 'new', ''),
            ('Raw Shea Butter 1kg', Decimal('9800.00'), 'new', ''),
            ('Hair Growth Oil 250ml', Decimal('12000.00'), 'new', ''),
            ('Daily Multivitamin 90 Tablets', Decimal('17500.00'), 'new', ''),
            ('SPF 50 Sunscreen Bundle', Decimal('22000.00'), 'new', ''),
            ('Premium Barbing Kit Set', Decimal('88000.00'), 'like_new', ''),
        ],
    },
]

SELLER_IDENTITIES = [
    ('Chukwuemeka', 'Obi'),
    ('Adaeze', 'Nwosu'),
    ('Babatunde', 'Adeyemi'),
    ('Ngozi', 'Eze'),
    ('Oluwaseun', 'Afolabi'),
    ('Amina', 'Musa'),
    ('Emeka', 'Okafor'),
    ('Funmilayo', 'Okonkwo'),
    ('Ibrahim', 'Salisu'),
    ('Chioma', 'Igwe'),
    ('Mariam', 'Yusuf'),
    ('Tobi', 'Adesanya'),
]

BUYER_IDENTITIES = [
    ('Adaora', 'Okafor'),
    ('Kunle', 'Balogun'),
    ('Zainab', 'Suleiman'),
    ('David', 'Eze'),
    ('Sola', 'Adewale'),
    ('Nkechi', 'Obiora'),
    ('Grace', 'Omotosho'),
    ('Femi', 'Ajibola'),
    ('Aisha', 'Garba'),
    ('Tolu', 'Ogundipe'),
    ('Chidera', 'Nnaji'),
    ('Musa', 'Lawal'),
    ('Kemi', 'Ojo'),
    ('Bello', 'Usman'),
    ('Joy', 'Akanbi'),
    ('Uche', 'Nwankwo'),
]

PRODUCT_DESCRIPTORS = [
    'clean, verified, and ready for immediate pickup or delivery',
    'sourced from a trusted Lagos supplier and quality checked',
    'popular with repeat buyers and suitable for personal or business use',
    'priced competitively for quick sale with room for serious negotiations',
]

CHAT_LINES = [
    'Hi, is this item still available?',
    'Yes, it is available and ready for pickup.',
    'Can you share your best last price?',
    'I can reduce it a little for a serious buyer.',
    'Do you offer delivery within my area?',
    'Yes, delivery can be arranged after confirmation.',
]


def make_phone(prefix='080'):
    return f'{prefix}{random.randint(10000000, 99999999)}'


def generate_image_bytes(seed, label='Demo Product', variant=1):
    try:
        from PIL import Image, ImageDraw, ImageFont

        width, height = 1280, 960
        palette = [
            (30, 58, 138),
            (124, 45, 18),
            (20, 83, 45),
            (88, 28, 135),
            (22, 78, 99),
            (120, 53, 15),
        ]
        background = palette[seed % len(palette)]
        image = Image.new('RGB', (width, height), background)
        draw = ImageDraw.Draw(image)
        font_title = ImageFont.load_default()
        font_meta = ImageFont.load_default()

        # Framed hero card.
        draw.rounded_rectangle((60, 60, width - 60, height - 60), radius=36, outline=(255, 255, 255), width=8)
        draw.rounded_rectangle((120, 120, width - 120, height - 120), radius=30, fill=(255, 255, 255, 32), outline=(255, 255, 255), width=4)

        # Stylized product block so images are visibly different.
        accent = palette[(seed + 2) % len(palette)]
        draw.rounded_rectangle((220, 240, width - 220, height - 300), radius=28, fill=accent)
        draw.ellipse((280, 300, 520, 540), fill=(255, 255, 255))
        draw.rectangle((560, 320, 980, 400), fill=(255, 255, 255))
        draw.rectangle((560, 440, 900, 500), fill=(240, 240, 240))
        draw.rectangle((560, 540, 840, 590), fill=(230, 230, 230))

        # Product title and image variant label.
        display_label = (label or 'Demo Product')[:48]
        draw.text((180, 150), display_label, fill=(255, 255, 255), font=font_title)
        draw.text((180, 190), f'Zunto mock image {variant}', fill=(230, 230, 230), font=font_meta)

        # Bottom information strip.
        draw.rounded_rectangle((180, height - 240, width - 180, height - 160), radius=18, fill=(18, 18, 18))
        draw.text((220, height - 215), 'Locally generated media for UI testing', fill=(255, 255, 255), font=font_meta)
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=82)
        return buffer.getvalue()
    except ImportError:
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


class Command(BaseCommand):
    help = 'Seed a rich deterministic demo marketplace dataset with media, orders, chat, and recommendation signals.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Delete existing demo buyers and sellers first.')

    def log(self, message):
        self.stdout.write(self.style.SUCCESS(message))

    def warn(self, message):
        self.stdout.write(self.style.WARNING(message))

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(20260322)

        if options['clear']:
            self.clear_demo_users()

        locations = self.seed_locations()
        categories = self.seed_categories()
        sellers = self.seed_sellers(locations)
        buyers = self.seed_buyers(locations)
        products = self.seed_products(sellers, categories)
        self.seed_shipping_addresses(buyers, locations)
        orders = self.seed_orders(buyers, products)
        self.seed_reviews(orders)
        self.seed_carts(buyers, products)
        self.seed_conversations(buyers, products)
        self.seed_recommendation_profiles(buyers, categories, locations)
        self.print_summary(sellers, buyers, products)

    def clear_demo_users(self):
        demo_users = User.objects.filter(email__endswith=SELLER_DOMAIN) | User.objects.filter(email__endswith=BUYER_DOMAIN)
        count = demo_users.count()
        demo_users.delete()
        self.log(f'Cleared {count} existing demo users and related seeded records.')

    def seed_locations(self):
        locations = []
        for state, city, area in LOCATIONS:
            location, _ = Location.objects.get_or_create(
                state=state,
                city=city,
                area=area,
                defaults={'is_active': True},
            )
            locations.append(location)
        self.log(f'Locations ready: {len(locations)}')
        return locations

    def seed_categories(self):
        categories = {}
        for index, category_data in enumerate(CATEGORIES, start=1):
            category, _ = Category.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'description': category_data['description'],
                    'icon': category_data['icon'],
                    'order': index,
                    'is_active': True,
                },
            )
            categories[category.name] = category
        self.log(f'Categories ready: {len(categories)}')
        return categories

    def seed_sellers(self, locations):
        sellers = []
        for index, (first_name, last_name) in enumerate(SELLER_IDENTITIES, start=1):
            email = f'{first_name.lower()}.{last_name.lower()}{SELLER_DOMAIN}'
            location = locations[(index - 1) % len(locations)]
            commerce_mode = 'managed' if index % 3 == 0 else 'direct'

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': make_phone('081'),
                    'role': 'seller',
                    'is_seller': True,
                    'is_verified': True,
                    'is_verified_seller': True,
                    'seller_commerce_mode': commerce_mode,
                    'address': f'{20 + index} Demo Plaza',
                    'city': location.city,
                    'state': location.state,
                    'country': 'Nigeria',
                    'bio': f'{first_name} focuses on verified marketplace sales with responsive buyer communication.',
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save(update_fields=['password'])

            SellerProfile.objects.update_or_create(
                user=user,
                defaults={
                    'status': SellerProfile.STATUS_APPROVED,
                    'is_verified_seller': True,
                    'verified': True,
                    'seller_commerce_mode': commerce_mode,
                    'active_location': location,
                    'rating': round(random.uniform(4.0, 4.9), 1),
                    'total_reviews': random.randint(6, 40),
                },
            )
            sellers.append(user)
        self.log(f'Sellers ready: {len(sellers)}')
        return sellers

    def seed_buyers(self, locations):
        buyers = []
        for index, (first_name, last_name) in enumerate(BUYER_IDENTITIES, start=1):
            email = f'{first_name.lower()}.{last_name.lower()}{BUYER_DOMAIN}'
            location = locations[(index * 2 - 1) % len(locations)]
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone': make_phone('090'),
                    'role': 'buyer',
                    'is_verified': True,
                    'address': f'{100 + index} Buyer Close',
                    'city': location.city,
                    'state': location.state,
                    'country': 'Nigeria',
                    'bio': f'{first_name} frequently buys electronics, fashion, and household items.',
                },
            )
            if created:
                user.set_password(PASSWORD)
                user.save(update_fields=['password'])
            buyers.append(user)
        self.log(f'Buyers ready: {len(buyers)}')
        return buyers

    def seed_products(self, sellers, categories):
        products = []
        image_seed = 0
        for seller_index, seller in enumerate(sellers):
            seller_category = CATEGORIES[seller_index % len(CATEGORIES)]
            category = categories[seller_category['name']]

            for template_index, (title, base_price, condition, brand) in enumerate(seller_category['products'], start=1):
                unique_title = f'{title} #{seller_index + 1}'
                product, created = Product.objects.get_or_create(
                    seller=seller,
                    title=unique_title,
                    defaults={
                        'description': f'{unique_title} is {random.choice(PRODUCT_DESCRIPTORS)}.',
                        'listing_type': 'product',
                        'category': category,
                        'price': base_price + Decimal(str((seller_index % 4) * 2500)),
                        'negotiable': template_index % 2 == 0,
                        'condition': condition,
                        'brand': brand,
                        'quantity': random.randint(1, 18) if base_price < Decimal('1000000.00') else 1,
                        'status': 'active',
                        'is_featured': template_index == 1,
                        'is_boosted': template_index == 2,
                        'is_verified': True,
                        'is_verified_product': True,
                        'views_count': random.randint(20, 1800),
                        'favorites_count': random.randint(0, 120),
                        'shares_count': random.randint(0, 35),
                    },
                )
                if created:
                    for image_order in range(3):
                        image_bytes = generate_image_bytes(
                            image_seed,
                            label=unique_title,
                            variant=image_order + 1,
                        )
                        image_seed += 1
                        ProductImage.objects.create(
                            product=product,
                            image=ContentFile(image_bytes, name=f'demo_product_{image_seed:04d}.jpg'),
                            caption=f'{unique_title} image {image_order + 1}',
                            order=image_order,
                            is_primary=image_order == 0,
                        )
                products.append(product)
        self.log(f'Products ready: {len(products)}')
        return products

    def seed_shipping_addresses(self, buyers, locations):
        for index, buyer in enumerate(buyers, start=1):
            location = locations[index % len(locations)]
            ShippingAddress.objects.get_or_create(
                user=buyer,
                label='Home',
                defaults={
                    'full_name': buyer.get_full_name(),
                    'phone': buyer.phone or make_phone('070'),
                    'address': f'{index + 10} Demo Estate Road',
                    'city': location.city,
                    'state': location.state,
                    'country': 'Nigeria',
                    'postal_code': f'{100000 + index}',
                    'is_default': True,
                },
            )
        self.log(f'Shipping addresses ready: {len(buyers)}')

    def seed_orders(self, buyers, products):
        orders = []
        for buyer_index, buyer in enumerate(buyers):
            address = buyer.shipping_addresses.filter(is_default=True).first()
            if not address:
                continue

            for order_index in range(2):
                sample_size = min(2 + (order_index % 2), len(products))
                selected_products = random.sample(products, sample_size)
                order = Order.objects.create(
                    customer=buyer,
                    status=random.choice(['paid', 'processing', 'shipped', 'delivered']),
                    payment_method=random.choice(['paystack', 'cash_on_delivery']),
                    payment_status='paid',
                    shipping_address_ref=address,
                    shipping_address=address.address,
                    shipping_city=address.city,
                    shipping_state=address.state,
                    shipping_country=address.country,
                    shipping_phone=address.phone,
                    shipping_email=buyer.email,
                    shipping_full_name=buyer.get_full_name(),
                    shipping_postal_code=address.postal_code,
                    paid_at=timezone.now() - timedelta(days=random.randint(1, 60)),
                )
                for product in selected_products:
                    quantity = 1 if product.price > Decimal('1000000.00') else random.randint(1, 2)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        seller=product.seller,
                        product_name=product.title,
                        product_image=product.images.order_by('order').first().image.url if product.images.exists() else '',
                        quantity=quantity,
                        unit_price=product.price,
                        total_price=product.price * quantity,
                        status='shipped',
                    )
                order.tax_amount = (order.subtotal * Decimal('0.075')).quantize(Decimal('0.01'))
                order.total_amount = order.subtotal + order.tax_amount
                if order.status == 'delivered':
                    order.delivered_at = timezone.now() - timedelta(days=random.randint(1, 30))
                elif order.status == 'shipped':
                    order.shipped_at = timezone.now() - timedelta(days=random.randint(1, 10))
                order.save()
                orders.append(order)
        self.log(f'Orders ready: {len(orders)}')
        return orders

    def seed_reviews(self, orders):
        product_review_count = 0
        seller_review_count = 0
        for order in orders:
            if order.status != 'delivered':
                continue

            for item in order.items.select_related('product', 'seller'):
                rating = random.choice([4, 4, 5, 5, 5])
                _, product_created = ProductReview.objects.get_or_create(
                    product=item.product,
                    reviewer=order.customer,
                    defaults={
                        'rating': rating,
                        'title': 'Excellent experience',
                        'comment': 'Arrived as described, seller responded quickly, and the quality matched the listing.',
                        'quality_rating': rating,
                        'value_rating': max(3, rating - 1),
                        'accuracy_rating': rating,
                        'is_verified_purchase': True,
                        'is_approved': True,
                    },
                )
                product_review_count += int(product_created)

                _, seller_created = SellerReview.objects.get_or_create(
                    seller=item.seller,
                    reviewer=order.customer,
                    product=item.product,
                    defaults={
                        'rating': rating,
                        'title': 'Responsive seller',
                        'comment': 'Seller communicated clearly and completed the transaction smoothly.',
                        'communication_rating': rating,
                        'reliability_rating': rating,
                        'professionalism_rating': rating,
                        'is_verified_transaction': True,
                        'is_approved': True,
                    },
                )
                seller_review_count += int(seller_created)
        self.log(f'Product reviews ready: {product_review_count}')
        self.log(f'Seller reviews ready: {seller_review_count}')

    def seed_carts(self, buyers, products):
        for buyer in buyers:
            cart, _ = Cart.objects.get_or_create(user=buyer)
            for product in random.sample(products, min(3, len(products))):
                CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={
                        'quantity': 1 if product.price > Decimal('1000000.00') else random.randint(1, 2),
                        'price_at_addition': product.price,
                    },
                )
        self.log(f'Carts ready: {len(buyers)}')

    def seed_conversations(self, buyers, products):
        conversation_count = 0
        for buyer in buyers[:8]:
            for product in random.sample(products, 2):
                if product.seller_id == buyer.id:
                    continue
                conversation, created = Conversation.objects.get_or_create(
                    buyer=buyer,
                    seller=product.seller,
                    product=product,
                )
                if created:
                    for idx, line in enumerate(CHAT_LINES[:4], start=1):
                        sender = buyer if idx % 2 else product.seller
                        Message.objects.create(
                            conversation=conversation,
                            sender=sender,
                            content=line,
                        )
                    conversation_count += 1
        self.log(f'Buyer-seller conversations ready: {conversation_count}')

    def seed_recommendation_profiles(self, buyers, categories, locations):
        category_list = list(categories.values())
        for index, buyer in enumerate(buyers, start=1):
            preferred = random.sample(category_list, k=min(2, len(category_list)))
            UserBehaviorProfile.objects.update_or_create(
                user=buyer,
                defaults={
                    'ai_search_count': random.randint(5, 18),
                    'normal_search_count': random.randint(1, 8),
                    'dominant_categories': [category.name for category in preferred],
                    'avg_budget_min': Decimal(str(random.randint(15000, 120000))),
                    'avg_budget_max': Decimal(str(random.randint(150000, 900000))),
                    'ai_conversion_rate': round(random.uniform(0.25, 0.72), 2),
                    'normal_conversion_rate': round(random.uniform(0.05, 0.28), 2),
                    'switch_frequency': round(random.uniform(0.1, 0.5), 2),
                    'ai_high_intent_no_conversion': index % 5 == 0,
                    'last_aggregated_at': timezone.now(),
                },
            )
            ConversationSession.objects.get_or_create(
                session_id=f'demo-reco-{buyer.id.hex[:12]}',
                defaults={
                    'user': buyer,
                    'assistant_mode': 'homepage_reco',
                    'assistant_lane': 'inbox',
                    'context_type': ConversationSession.CONTEXT_TYPE_RECOMMENDATION,
                    'conversation_title': 'Homepage recommendation thread',
                    'current_state': 'chat_mode',
                    'message_count': 4,
                    'context': {'seeded': True},
                    'constraint_state': {'budget': 'seeded'},
                    'intent_state': {'type': 'recommendation'},
                },
            )

        for index, category in enumerate(category_list):
            DemandCluster.objects.update_or_create(
                category=category,
                location=locations[index % len(locations)],
                defaults={
                    'demand_count': random.randint(8, 24),
                    'last_gap_at': timezone.now() - timedelta(hours=index + 1),
                    'hot_score': round(random.uniform(1.2, 3.9), 2),
                    'is_hot': True,
                },
            )
        self.log(f'Recommendation profiles ready: {len(buyers)}')

    def print_summary(self, sellers, buyers, products):
        self.stdout.write('')
        self.log('Seed complete.')
        self.stdout.write(f'Sellers: {len(sellers)}')
        self.stdout.write(f'Buyers: {len(buyers)}')
        self.stdout.write(f'Products: {len(products)}')
        self.stdout.write(f'Images: {ProductImage.objects.filter(product__seller__email__endswith=SELLER_DOMAIN).count()}')
        self.stdout.write(f'Orders: {Order.objects.filter(customer__email__endswith=BUYER_DOMAIN).count()}')
        self.stdout.write(f'Conversations: {Conversation.objects.filter(buyer__email__endswith=BUYER_DOMAIN).count()}')
        self.stdout.write('')
        self.stdout.write(f'Seller login example: {sellers[0].email} / {PASSWORD}')
        self.stdout.write(f'Buyer login example: {buyers[0].email} / {PASSWORD}')
