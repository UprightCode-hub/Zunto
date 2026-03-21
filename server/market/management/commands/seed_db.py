"""
ZUNTO MARKETPLACE - DATABASE SEED MANAGEMENT COMMAND

PLACE THIS FILE AT:
  Zunto-main/server/market/management/commands/seed_db.py

RUN WITH:
  python manage.py seed_db

The scripts/ folder already exists in your project, this goes
into market/management/commands/ instead so Django can find it.
"""

import random
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import SellerProfile
from cart.models import Cart, CartItem
from market.models import Category, Location, Product
from orders.models import Order, OrderItem, ShippingAddress
from reviews.models import ProductReview, SellerReview

User = get_user_model()


# ── Data Constants ────────────────────────────────────────────────────────────

NIGERIAN_STATES = [
    ('Lagos', 'Ikeja'), ('Lagos', 'Victoria Island'), ('Lagos', 'Surulere'),
    ('Abuja', 'Garki'), ('Abuja', 'Wuse'), ('Rivers', 'Port Harcourt'),
    ('Oyo', 'Ibadan'), ('Kano', 'Kano City'), ('Anambra', 'Onitsha'),
    ('Edo', 'Benin City'),
]

CATEGORIES_DATA = [
    ('Electronics', '📱', ['Smartphones', 'Laptops', 'Tablets', 'Accessories']),
    ('Fashion', '👗', ['Men Clothing', 'Women Clothing', 'Shoes', 'Bags']),
    ('Home & Living', '🏠', ['Furniture', 'Kitchen', 'Decor']),
    ('Vehicles', '🚗', ['Cars', 'Motorcycles', 'Spare Parts']),
    ('Food & Groceries', '🛒', ['Fresh Produce', 'Packaged Foods', 'Beverages']),
    ('Health & Beauty', '💄', ['Skincare', 'Hair Care', 'Supplements']),
    ('Sports & Outdoors', '⚽', ['Gym Equipment', 'Football', 'Cycling']),
    ('Books & Education', '📚', ['Textbooks', 'Fiction', 'Stationery']),
    ('Agriculture', '🌾', ['Seeds & Seedlings', 'Farm Tools', 'Livestock']),
    ('Services', '🛠', ['Repairs', 'Cleaning', 'Tutoring']),
]

PRODUCT_TEMPLATES = {
    'Smartphones': [
        ('iPhone 15 Pro Max 256GB', 950000, 1800000),
        ('Samsung Galaxy S24 Ultra', 850000, 1600000),
        ('Tecno Camon 20 Pro', 120000, 220000),
        ('Infinix Hot 40 Pro', 85000, 150000),
        ('Xiaomi Redmi Note 13', 110000, 200000),
    ],
    'Laptops': [
        ('MacBook Air M2 8GB RAM', 900000, 1500000),
        ('HP Pavilion 15 Core i5', 350000, 550000),
        ('Dell Inspiron 15 3000', 280000, 450000),
        ('Lenovo ThinkPad E14', 420000, 650000),
        ('ASUS VivoBook 15', 300000, 480000),
    ],
    'Tablets': [
        ('iPad Pro 12.9 M2', 650000, 1100000),
        ('Samsung Galaxy Tab S9', 400000, 700000),
        ('Tecno T40 Pro Tablet', 80000, 140000),
    ],
    'Accessories': [
        ('Wireless Earbuds Pro', 15000, 45000),
        ('USB-C Hub 7-in-1', 8000, 22000),
        ('Phone Case Premium', 3000, 12000),
        ('Screen Protector Pack', 2000, 7000),
    ],
    'Men Clothing': [
        ('Native Ankara Senator Wear', 18000, 45000),
        ('Corporate Suit 3-Piece', 55000, 120000),
        ('Polo Shirt Premium', 6500, 18000),
        ('Agbada Traditional Set', 35000, 80000),
        ('Chinos Trouser Slim Fit', 8000, 20000),
    ],
    'Women Clothing': [
        ('Ankara Gown A-Line', 22000, 55000),
        ('Iro and Buba Set', 28000, 65000),
        ('Lace Blouse Premium', 15000, 38000),
        ('Jumpsuit Casual', 12000, 30000),
        ('George Wrapper Set', 45000, 95000),
    ],
    'Shoes': [
        ('Leather Oxford Men Shoes', 18000, 50000),
        ('Heels Strappy Women', 12000, 35000),
        ('Sneakers Air Max', 25000, 65000),
        ('Sandals Summer', 5000, 18000),
    ],
    'Bags': [
        ('Leather Handbag Women', 22000, 75000),
        ('Backpack Laptop 15 inch', 14000, 40000),
        ('Travel Duffel Bag', 18000, 55000),
    ],
    'Furniture': [
        ('L-Shaped Sofa Set', 280000, 550000),
        ('Queen Bed Frame Wooden', 120000, 280000),
        ('Dining Table 6-Seater', 180000, 380000),
        ('Office Chair Ergonomic', 55000, 130000),
        ('Wardrobe 4-Door', 145000, 320000),
    ],
    'Kitchen': [
        ('Blender Industrial', 18000, 45000),
        ('Gas Cooker 4-Burner', 65000, 140000),
        ('Microwave Oven 20L', 45000, 95000),
        ('Pots and Pans Set', 22000, 60000),
    ],
    'Decor': [
        ('Wall Art Canvas Print', 8000, 25000),
        ('Throw Pillows Set of 4', 5500, 18000),
        ('Indoor Plant Pot Ceramic', 4500, 15000),
    ],
    'Cars': [
        ('Toyota Camry 2019 Clean', 8500000, 16000000),
        ('Honda Civic 2020', 9200000, 18000000),
        ('Hyundai Elantra 2018', 7000000, 14000000),
    ],
    'Motorcycles': [
        ('Bajaj Boxer 150cc', 320000, 580000),
        ('Honda Wave 110cc', 280000, 500000),
    ],
    'Spare Parts': [
        ('Car Battery 15 Plates', 28000, 65000),
        ('Engine Oil 5L Full Synthetic', 12000, 30000),
        ('Brake Pads Set Toyota', 8500, 22000),
    ],
    'Fresh Produce': [
        ('Tomatoes Basket 50kg', 18000, 35000),
        ('Yam Tubers Grade A', 2500, 8000),
        ('Plantain Bunch Fresh', 1500, 4500),
        ('Spinach Bunch', 500, 1800),
    ],
    'Packaged Foods': [
        ('Indomie Noodles Carton 40', 7500, 15000),
        ('Rice 50kg Bag Ofada', 55000, 95000),
        ('Beans 50kg Brown', 48000, 85000),
    ],
    'Beverages': [
        ('Zobo Drink 1 Litre', 1200, 3500),
        ('Tigernut Drink Homemade', 1500, 4000),
    ],
    'Skincare': [
        ('Shea Butter Raw 500g', 3500, 10000),
        ('Vitamin C Serum 30ml', 8000, 22000),
        ('Sunscreen SPF 50 100ml', 5500, 16000),
        ('Face Wash Charcoal', 4500, 14000),
    ],
    'Hair Care': [
        ('Creme of Nature Shampoo', 3500, 9000),
        ('Cantu Leave-in Conditioner', 4500, 12000),
        ('Hair Growth Oil 100ml', 5000, 15000),
    ],
    'Supplements': [
        ('Multivitamin 60 Tablets', 6500, 18000),
        ('Omega-3 Fish Oil 60 Caps', 8000, 22000),
    ],
    'Gym Equipment': [
        ('Dumbbell Set 20kg Adjustable', 35000, 75000),
        ('Resistance Bands Set 5pc', 8000, 22000),
        ('Yoga Mat Non-Slip', 6500, 18000),
        ('Jump Rope Speed', 3000, 8000),
    ],
    'Football': [
        ('Football Size 5 Official', 8000, 22000),
        ('Football Boots Nike', 18000, 50000),
    ],
    'Textbooks': [
        ('JAMB Past Questions 2024', 2500, 7000),
        ('WAEC Biology Textbook', 3500, 9000),
        ('Principles of Economics', 4500, 12000),
    ],
    'Fiction': [
        ('Things Fall Apart Achebe', 2000, 5500),
        ('Purple Hibiscus Adichie', 2500, 7000),
        ('Half of a Yellow Sun', 2800, 7500),
    ],
    'Seeds & Seedlings': [
        ('Tomato Seeds Improved 50g', 1500, 4500),
        ('Pepper Seedlings Tray 50', 3500, 9000),
        ('Maize Seeds Hybrid 2kg', 4500, 12000),
    ],
    'Farm Tools': [
        ('Hoe and Cutlass Set', 8500, 22000),
        ('Watering Can 10L', 4000, 10000),
        ('Wheelbarrow Heavy Duty', 28000, 65000),
    ],
    'Repairs': [
        ('Phone Screen Repair Service', 8000, 25000),
        ('AC Servicing Home Visit', 15000, 35000),
        ('Generator Repair Service', 12000, 30000),
    ],
    'Cleaning': [
        ('Deep House Cleaning Service', 25000, 60000),
        ('Carpet Cleaning Per Room', 8000, 20000),
    ],
    'Tutoring': [
        ('Mathematics Tutoring 1 Month', 25000, 60000),
        ('English Language Tutoring', 20000, 50000),
        ('IELTS Preparation Course', 45000, 95000),
    ],
}

NIGERIAN_FIRST_NAMES = [
    'Chukwuemeka', 'Oluwaseun', 'Abubakar', 'Chidinma', 'Yusuf',
    'Adaeze', 'Emeka', 'Fatimah', 'Babatunde', 'Ngozi',
    'Usman', 'Amaka', 'Tunde', 'Blessing', 'Ibrahim',
    'Chiamaka', 'Segun', 'Hafsat', 'Chidi', 'Olusegun',
]

NIGERIAN_LAST_NAMES = [
    'Okonkwo', 'Adeyemi', 'Musa', 'Okafor', 'Danjuma',
    'Nwosu', 'Bakare', 'Abdullahi', 'Eze', 'Olawale',
    'Suleiman', 'Chukwu', 'Lawal', 'Obiora', 'Yakubu',
    'Obi', 'Adesanya', 'Uche', 'Garba', 'Adeleke',
]

REVIEW_COMMENTS = [
    "Excellent product, exactly as described. Very fast delivery!",
    "Good quality for the price. Seller was responsive and professional.",
    "I am very impressed with this purchase. Highly recommend.",
    "Product arrived in perfect condition. Will buy again.",
    "Great value for money. The seller packaged it very well.",
    "Decent product but took a bit longer than expected to arrive.",
    "Quality is good, seller communicated well throughout.",
    "Amazing! This is exactly what I needed. Five stars.",
    "The product is as advertised. Seller is trustworthy.",
    "Good experience overall. The item works perfectly.",
    "Very satisfied with my purchase. Quality exceeded expectations.",
    "Fast delivery and well-packaged. Product is top quality.",
    "Not bad for the price. Would consider buying again.",
    "Excellent service and great product quality. Highly recommended!",
    "Item looks even better in person. Seller was super helpful.",
]

FAKE_PARAGRAPHS = [
    "This is a high quality product sourced directly from trusted suppliers. It has been tested and verified to meet all standard requirements. Suitable for everyday use and built to last.",
    "Premium grade item available at a competitive market price. Comes with full manufacturer guarantee. Perfect for personal use or as a gift for loved ones.",
    "Authentic product in excellent condition. We pride ourselves on delivering only the best to our valued customers across Nigeria and beyond.",
    "Top quality item that speaks for itself. Thousands of satisfied customers have already purchased this product. Do not miss out on this great deal.",
    "Carefully selected and quality-checked before listing. We offer fast delivery across all Nigerian states. Contact us for bulk orders and discounts.",
]

FAKE_STREETS = [
    "12 Broad Street", "45 Adeola Odeku", "7 Ahmadu Bello Way",
    "23 Allen Avenue", "91 Otigba Street", "15 Awolowo Road",
    "3 Isaac John Street", "88 Bode Thomas Street", "56 Toyin Street",
    "19 Obafemi Awolowo Way", "67 Agege Motor Road", "4 Ladoke Akintola Blvd",
]


class Command(BaseCommand):
    help = 'Seed the Zunto database with realistic Nigerian marketplace test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing seed data before seeding (emails ending in @zuntotest.com)',
        )

    def log(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  checkmark  {msg}'))

    def warn(self, msg):
        self.stdout.write(self.style.WARNING(f'  warning  {msg}'))

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('  ZUNTO MARKETPLACE SEED SCRIPT')
        self.stdout.write('  Generating large dataset...')
        self.stdout.write('=' * 60 + '\n')

        if options['clear']:
            self.clear_seed_data()

        locations = self.create_locations()
        all_subcategories = self.create_categories()
        sellers = self.create_sellers(locations)
        buyers = self.create_buyers()
        products = self.create_products(sellers, all_subcategories, locations)
        shipping_map = self.create_shipping_addresses(buyers)
        all_orders = self.create_orders(buyers, products, shipping_map)
        self.create_product_reviews(all_orders)
        self.create_seller_reviews(all_orders)
        self.create_carts(buyers, products)
        self.print_summary()

    def clear_seed_data(self):
        self.stdout.write('Clearing existing seed data...')
        test_users = User.objects.filter(email__endswith='@zuntotest.com')
        count = test_users.count()
        test_users.delete()
        self.log(f'Cleared {count} test users and all related data')

    def create_locations(self):
        self.stdout.write('Creating locations...')
        locations = []
        for state, city in NIGERIAN_STATES:
            loc, _ = Location.objects.get_or_create(
                state=state,
                city=city,
                area='',
                defaults={'is_active': True},
            )
            locations.append(loc)
        self.log(f'{len(locations)} locations ready')
        return locations

    def create_categories(self):
        self.stdout.write('Creating categories...')
        all_subcategories = []
        for idx, (cat_name, icon, subcats) in enumerate(CATEGORIES_DATA):
            parent, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={
                    'slug': slugify(cat_name),
                    'icon': icon,
                    'is_active': True,
                    'order': idx,
                },
            )
            for sub_name in subcats:
                sub, _ = Category.objects.get_or_create(
                    name=sub_name,
                    defaults={
                        'slug': slugify(sub_name),
                        'parent': parent,
                        'is_active': True,
                    },
                )
                all_subcategories.append(sub)
        self.log(f'{len(all_subcategories)} subcategories ready')
        return all_subcategories

    def create_sellers(self, locations):
        self.stdout.write('Creating 20 seller accounts...')
        sellers = []
        seller_locations = {}

        for i in range(20):
            first = NIGERIAN_FIRST_NAMES[i]
            last = NIGERIAN_LAST_NAMES[i]
            email = f'seller{i + 1}@zuntotest.com'

            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                self.warn(f'{email} already exists, skipping')
            else:
                phone = f'+2347{random.randint(10000000, 99999999)}'
                while User.objects.filter(phone=phone).exists():
                    phone = f'+2347{random.randint(10000000, 99999999)}'

                user = User.objects.create_user(
                    email=email,
                    password='TestPass123!',
                    first_name=first,
                    last_name=last,
                    phone=phone,
                    role='seller',
                    is_seller=True,
                    is_verified=True,
                    is_verified_seller=True,
                    city=random.choice(NIGERIAN_STATES)[1],
                    state=random.choice(NIGERIAN_STATES)[0],
                    country='Nigeria',
                    seller_commerce_mode='managed',
                )

            loc = random.choice(locations)
            seller_locations[user.id] = loc

            profile, created = SellerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'status': SellerProfile.STATUS_APPROVED,
                    'is_verified_seller': True,
                    'verified': True,
                    'seller_commerce_mode': 'managed',
                    'active_location': loc,
                    'rating': round(random.uniform(3.5, 5.0), 1),
                    'total_reviews': random.randint(5, 80),
                },
            )
            if not created and profile.active_location != loc:
                profile.active_location = loc
                profile.save(update_fields=['active_location'])

            sellers.append(user)

        self.log(f'{len(sellers)} sellers ready')
        return sellers

    def create_buyers(self):
        self.stdout.write('Creating 20 buyer accounts...')
        buyers = []
        buyer_first = [
            'Adaora', 'Kunle', 'Zainab', 'Emeka', 'Sola',
            'Funke', 'Dayo', 'Nkechi', 'Bello', 'Grace',
            'Sunday', 'Chinwe', 'Musa', 'Lola', 'Ade',
            'Kemi', 'Femi', 'Amina', 'Chidi', 'Tobi',
        ]
        buyer_last = [
            'Okafor', 'Balogun', 'Suleiman', 'Eze', 'Adeyemi',
            'Nwosu', 'Afolabi', 'Obiora', 'Garba', 'Omotosho',
            'Ikenna', 'Oluwole', 'Ibrahim', 'Adeleke', 'Salami',
            'Odunsi', 'Fadahunsi', 'Yakubu', 'Obi', 'Adesanya',
        ]

        for i in range(20):
            email = f'buyer{i + 1}@zuntotest.com'
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                self.warn(f'{email} already exists, skipping')
            else:
                phone = f'+2348{random.randint(10000000, 99999999)}'
                while User.objects.filter(phone=phone).exists():
                    phone = f'+2348{random.randint(10000000, 99999999)}'

                user = User.objects.create_user(
                    email=email,
                    password='TestPass123!',
                    first_name=buyer_first[i],
                    last_name=buyer_last[i],
                    phone=phone,
                    role='buyer',
                    is_verified=True,
                    city=random.choice(NIGERIAN_STATES)[1],
                    state=random.choice(NIGERIAN_STATES)[0],
                    country='Nigeria',
                )
            buyers.append(user)

        self.log(f'{len(buyers)} buyers ready')
        return buyers

    def create_products(self, sellers, all_subcategories, locations):
        self.stdout.write('Creating 100+ products...')
        products = []
        sub_category_map = {sub.name: sub for sub in all_subcategories}

        for sub_name, templates in PRODUCT_TEMPLATES.items():
            sub_cat = sub_category_map.get(sub_name)
            if not sub_cat:
                continue

            is_service = (
                sub_cat.parent and sub_cat.parent.name == 'Services'
            )
            listing_type = 'service' if is_service else 'product'

            for title, min_price, max_price in templates:
                seller = random.choice(sellers)
                price = Decimal(str(random.randint(min_price, max_price)))
                qty = random.randint(1, 50)
                condition = random.choice(['new', 'like_new', 'good', 'fair'])

                base_slug = slugify(title)
                slug = base_slug
                counter = 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{counter}'
                    counter += 1

                try:
                    seller_loc = seller.seller_profile.active_location
                except Exception:
                    seller_loc = random.choice(locations)

                product = Product(
                    seller=seller,
                    title=title,
                    slug=slug,
                    description=random.choice(FAKE_PARAGRAPHS),
                    listing_type=listing_type,
                    category=sub_cat,
                    location=seller_loc,
                    price=price,
                    negotiable=random.choice([True, False]),
                    condition=condition,
                    quantity=qty,
                    status='active',
                    is_featured=random.random() > 0.8,
                    is_verified=True,
                    is_verified_product=True,
                    views_count=random.randint(0, 2000),
                    favorites_count=random.randint(0, 200),
                )
                product.save()
                products.append(product)

        self.log(f'{len(products)} products created')
        return products

    def create_shipping_addresses(self, buyers):
        self.stdout.write('Creating shipping addresses...')
        shipping_map = {}
        for buyer in buyers:
            state, city = random.choice(NIGERIAN_STATES)
            addr, _ = ShippingAddress.objects.get_or_create(
                user=buyer,
                label='Home',
                defaults={
                    'full_name': buyer.get_full_name(),
                    'phone': buyer.phone or f'+2347{random.randint(10000000, 99999999)}',
                    'address': random.choice(FAKE_STREETS),
                    'city': city,
                    'state': state,
                    'country': 'Nigeria',
                    'postal_code': str(random.randint(100000, 999999)),
                    'is_default': True,
                },
            )
            shipping_map[buyer.id] = addr
        self.log(f'{len(shipping_map)} shipping addresses ready')
        return shipping_map

    def create_orders(self, buyers, products, shipping_map):
        self.stdout.write('Creating orders...')
        all_orders = []
        order_statuses = [
            'pending', 'paid', 'processing',
            'shipped', 'delivered', 'delivered', 'delivered',
        ]

        for buyer in buyers:
            addr = shipping_map[buyer.id]
            num_orders = random.randint(2, 5)

            for _ in range(num_orders):
                status = random.choice(order_statuses)
                payment_status = (
                    'paid'
                    if status in ['paid', 'processing', 'shipped', 'delivered']
                    else 'unpaid'
                )

                date_str = timezone.now().strftime('%Y%m%d')
                order_number = f'ORD-{date_str}-{str(uuid.uuid4())[:4].upper()}'
                while Order.objects.filter(order_number=order_number).exists():
                    order_number = f'ORD-{date_str}-{str(uuid.uuid4())[:4].upper()}'

                order = Order.objects.create(
                    order_number=order_number,
                    customer=buyer,
                    status=status,
                    payment_method=random.choice(['paystack', 'cash_on_delivery']),
                    payment_status=payment_status,
                    tax_amount=Decimal('0'),
                    shipping_fee=Decimal('0'),
                    discount_amount=Decimal('0'),
                    subtotal=Decimal('0'),
                    total_amount=Decimal('0'),
                    shipping_address=addr.address,
                    shipping_city=addr.city,
                    shipping_state=addr.state,
                    shipping_country=addr.country,
                    shipping_phone=addr.phone,
                    shipping_email=buyer.email,
                    shipping_full_name=buyer.get_full_name(),
                    paid_at=timezone.now() if payment_status == 'paid' else None,
                )

                num_items = random.randint(1, 4)
                chosen_products = random.sample(products, min(num_items, len(products)))

                for product in chosen_products:
                    unit_price = product.price
                    qty = random.randint(1, 3)
                    item_status = 'pending' if status == 'pending' else 'shipped'
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        seller=product.seller,
                        product_name=product.title,
                        product_image='',
                        quantity=qty,
                        unit_price=unit_price,
                        total_price=unit_price * qty,
                        status=item_status,
                    )

                order.update_totals()
                tax = (order.subtotal * Decimal('0.075')).quantize(Decimal('0.01'))
                order.tax_amount = tax
                order.total_amount = order.subtotal + tax
                order.save(update_fields=['tax_amount', 'total_amount'])
                all_orders.append(order)

        self.log(f'{len(all_orders)} orders created')
        return all_orders

    def create_product_reviews(self, all_orders):
        self.stdout.write('Creating product reviews...')
        review_count = 0
        reviewed_pairs = set()
        delivered_orders = [o for o in all_orders if o.status == 'delivered']

        for order in delivered_orders:
            buyer = order.customer
            for item in order.items.select_related('product').all():
                product = item.product
                if not product:
                    continue
                pair = (product.id, buyer.id)
                if pair in reviewed_pairs:
                    continue
                reviewed_pairs.add(pair)

                rating = random.choices([3, 4, 4, 5, 5, 5], k=1)[0]
                title = 'Great product!' if rating >= 4 else 'Decent product'
                ProductReview.objects.get_or_create(
                    product=product,
                    reviewer=buyer,
                    defaults={
                        'rating': rating,
                        'title': title,
                        'comment': random.choice(REVIEW_COMMENTS),
                        'quality_rating': random.randint(3, 5),
                        'value_rating': random.randint(3, 5),
                        'accuracy_rating': random.randint(3, 5),
                        'is_verified_purchase': True,
                        'is_approved': True,
                        'helpful_count': random.randint(0, 30),
                    },
                )
                review_count += 1

        self.log(f'{review_count} product reviews created')

    def create_seller_reviews(self, all_orders):
        self.stdout.write('Creating seller reviews...')
        seller_review_count = 0
        seller_reviewed_pairs = set()
        delivered_orders = [o for o in all_orders if o.status == 'delivered']

        for order in delivered_orders:
            buyer = order.customer
            for item in order.items.select_related('product', 'seller').all():
                seller = item.seller
                product = item.product
                if not seller or not product:
                    continue
                if seller.id == buyer.id:
                    continue
                pair = (seller.id, buyer.id, product.id)
                if pair in seller_reviewed_pairs:
                    continue
                seller_reviewed_pairs.add(pair)

                rating = random.choices([3, 4, 4, 5, 5], k=1)[0]
                title = 'Excellent seller' if rating >= 4 else 'Good seller'
                SellerReview.objects.get_or_create(
                    seller=seller,
                    reviewer=buyer,
                    product=product,
                    defaults={
                        'rating': rating,
                        'title': title,
                        'comment': random.choice(REVIEW_COMMENTS),
                        'communication_rating': random.randint(3, 5),
                        'reliability_rating': random.randint(3, 5),
                        'professionalism_rating': random.randint(3, 5),
                        'is_verified_transaction': True,
                        'is_approved': True,
                        'helpful_count': random.randint(0, 20),
                    },
                )
                seller_review_count += 1

        self.log(f'{seller_review_count} seller reviews created')

    def create_carts(self, buyers, products):
        self.stdout.write('Creating carts for buyers...')
        cart_count = 0
        for buyer in buyers:
            cart, _ = Cart.objects.get_or_create(user=buyer)
            chosen = random.sample(products, random.randint(1, 3))
            for product in chosen:
                if product.status == 'active' and product.quantity > 0:
                    CartItem.objects.get_or_create(
                        cart=cart,
                        product=product,
                        defaults={
                            'quantity': random.randint(1, 2),
                            'price_at_addition': product.price,
                        },
                    )
            cart_count += 1
        self.log(f'{cart_count} carts with items created')

    def print_summary(self):
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('  SEED COMPLETE!'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'  Locations        : {Location.objects.count()}')
        self.stdout.write(f'  Categories       : {Category.objects.count()}')
        self.stdout.write(f'  Total Users      : {User.objects.count()}')
        self.stdout.write(f'  Sellers          : {User.objects.filter(role="seller").count()}')
        self.stdout.write(f'  Buyers           : {User.objects.filter(role="buyer").count()}')
        self.stdout.write(f'  Products         : {Product.objects.count()}')
        self.stdout.write(f'  Orders           : {Order.objects.count()}')
        self.stdout.write(f'  Product Reviews  : {ProductReview.objects.count()}')
        self.stdout.write(f'  Seller Reviews   : {SellerReview.objects.count()}')
        self.stdout.write(f'  Carts            : {Cart.objects.count()}')
        self.stdout.write('\n  TEST CREDENTIALS (password: TestPass123!)')
        self.stdout.write('  Sellers : seller1@zuntotest.com -> seller20@zuntotest.com')
        self.stdout.write('  Buyers  : buyer1@zuntotest.com  -> buyer20@zuntotest.com')
        self.stdout.write('=' * 60 + '\n')