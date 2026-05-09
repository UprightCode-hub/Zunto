"""Deterministic external image URLs for demo and bulk-seeded products.

These URLs are intentionally stored on Product.image_url_locked instead of
downloaded into MEDIA_ROOT. Render free web services have ephemeral local
files, so URL-backed demo images survive restarts and redeploys.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote


LOREMFLICKR_IMAGE_PATTERN = "https://loremflickr.com/400/400/{tags}/all?lock={lock}"
NO_IMAGE_PLACEHOLDER_RE = re.compile(r"placehold\.co/.+[?&]text=No(?:\+|%20)?Image", re.IGNORECASE)
UNSPLASH_IMAGE_RE = re.compile(r"https?://(?:[^/?#]+\.)?unsplash\.com(?:[/?#]|$)", re.IGNORECASE)


def _normalize_category_key(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip()).lower()
    return text.replace(" and ", " & ")


CATEGORY_TAG_GROUPS = {
    "electronics,smartphone": (
        "Phones", "PhonesDebug", "Phones & Tablets", "iPhones", "Android Phones",
        "Feature Phones", "Refurbished Phones",
    ),
    "electronics,gadget": (
        "Tablets",
        "Phone Accessories", "Phone Cases", "Screen Protectors", "Mobile Repairs",
        "Accessories",
        "Power Banks", "UPS & Power Backup", "Chargers & Cables",
        "Earbuds & Headsets", "Headphones", "Electronics", "Electronic Components",
        "Projectors", "Radios", "Streaming Devices", "Drones", "Security Cameras",
        "Solar Electronics", "Televisions", "TV & Audio", "Home Theatre Systems",
        "Audio Speakers", "Cameras", "Photography Services", "Gaming Consoles",
    ),
    "watch,accessories": ("Watches", "Smart Watches"),
    "electronics,laptop": (
        "Laptops", "Computers & Accessories", "Computers & Laptops",
        "Desktop Computers", "Gaming PCs", "Workstations", "Computer Parts",
        "Laptop Bags", "Keyboards & Mice", "Monitors", "Networking Devices",
        "Printers", "Software Licenses", "Storage Drives",
    ),
    "fashion,clothing": (
        "Fashion", "Fashion & Clothing", "Fashion Accessories", "Men Clothing",
        "Women Clothing", "Traditional Wear", "Dresses", "Shirts",
        "Trousers & Jeans", "Caps & Hats", "Belts & Wallets", "Activewear",
        "Baby Clothing", "Maternity",
    ),
    "shoes,footwear": (
        "Shoes", "Shoes & Footwear", "Sneakers", "Formal Shoes", "Sandals",
        "Slippers", "Boots", "Heels", "Running Shoes", "Kids Shoes",
        "Safety Shoes", "Football Boots", "Sports Shoes", "Shoe Care",
        "Shoe Accessories", "Loafers",
    ),
    "bag,fashion": ("Bags", "Handbags"),
    "jewellery,accessories": ("Jewellery", "Jewelry"),
    "beauty,cosmetics": (
        "Beauty", "Beauty & Personal Care", "Health & Beauty", "Skincare",
        "Sunscreen", "Hair Care", "Hair Oils", "Makeup", "Perfumes", "Barbing Kits",
        "Body Creams", "Soaps & Washes", "Natural Beauty", "Nail Care",
        "Beauty Tools", "Oral Care Beauty", "Baby Skincare",
    ),
    "product,shopping": (
        "Health & Wellness", "Vitamins", "Supplements", "Medical Devices",
        "First Aid", "Fitness Nutrition", "Personal Hygiene", "Mobility Aids",
        "Health Monitors", "Massage Products", "Eye Care", "Dental Care",
        "Wellness Herbs", "Services", "Repairs", "Cleaning Services", "Beauty Services",
        "Tutoring", "Logistics", "Event Services", "Home Installation",
        "Vehicle Services", "Business Services", "Freelance Services", "Rentals",
        "Repairs & Maintenance", "Home Services", "Professional Services",
        "Events & Entertainment", "Cleaning", "Industrial & Business",
        "Office Equipment", "Restaurant Equipment", "POS Hardware",
        "Packaging Materials", "Cleaning Supplies", "Industrial Machines",
        "Generators Industrial", "Safety Industrial", "Warehouse Supplies",
        "Printing Equipment", "Salon Equipment", "Retail Fixtures", "Others",
        "Gifts", "Collectibles", "Musical Instruments", "Pet Supplies",
        "Travel Accessories", "Religious Items", "Party Supplies", "Security Services",
        "Digital Products", "Miscellaneous", "Local Crafts", "Seasonal Items",
        "Jobs", "Full-time", "Part-time", "Freelance", "Internship", "Vehicles",
        "Cars", "SUVs", "Buses", "Trucks", "Vehicle Rentals", "Boats",
        "Heavy Vehicles", "Electric Vehicles", "Car Auctions", "Vehicle Accessories",
        "Motorcycles", "Tricycles", "Bicycles", "Auto Parts", "Spare Parts",
        "Tyres", "Batteries", "Brake Parts", "Engine Parts", "Suspension Parts",
        "Car Electronics", "Body Parts", "Oils & Fluids", "Filters", "Lights",
        "Interior Accessories", "Tools & Diagnostics", "Building Materials & Tools",
        "Fasteners & Nails", "Cement", "Paints", "Plumbing Materials",
        "Electrical Materials", "Tiles", "Roofing", "Wood & Boards", "Hand Tools",
        "Power Tools", "Safety Gear", "Doors & Windows", "Baby & Kids", "Diapers",
        "Strollers", "Car Seats", "Toys", "School Bags", "Baby Feeding",
        "Learning Materials", "Children Books",
    ),
    "food,market": (
        "Food & Agriculture", "Groceries", "Groceries & Food", "Rice & Grains",
        "Beans & Legumes", "Oils", "Spices", "Beverages", "Snacks",
        "Frozen Foods", "Fresh Produce", "Meat & Fish", "Baby Food",
        "Breakfast Foods", "Bulk Groceries", "Canned Foods",
    ),
    "furniture,interior": (
        "Home & Furniture", "Home & Living", "Furniture", "Sofas",
        "Beds & Mattresses", "Tables", "Chairs", "Wardrobes", "Home Decor",
        "Curtains & Blinds", "Lighting", "Bathroom Accessories",
        "Storage & Organizers", "Outdoor Furniture", "Bedding", "Kids Furniture",
        "Decor", "Garden",
    ),
    "appliance,home": (
        "Kitchenware", "Kitchen", "Kitchen & Dining",
        "Appliances", "Refrigerators", "Freezers", "Washing Machines",
        "Cookers & Ovens", "Microwaves", "Blenders", "Fans",
        "Air Conditioners", "Generators", "Water Dispensers", "Irons",
        "Vacuum Cleaners", "Small Kitchen Appliances",
    ),
    "sports,fitness": (
        "Sports & Fitness", "Gym Equipment", "Football Gear", "Basketball Gear",
        "Cycling Gear", "Yoga & Pilates", "Swimming Gear", "Outdoor Sports",
        "Treadmills", "Weights", "Camping Gear",
    ),
    "book,education": (
        "Books & Stationery", "Textbooks", "Novels", "Office Stationery",
        "School Supplies", "Art Supplies", "Notebooks", "Printers Paper",
        "Educational Materials", "Religious Books", "Exam Prep", "Writing Tools",
    ),
}


CATEGORY_IMAGE_TAGS = {
    _normalize_category_key(category_name): tags
    for tags, category_names in CATEGORY_TAG_GROUPS.items()
    for category_name in category_names
}


CATEGORY_TAG_RULES = (
    (("phone", "iphone", "android", "smartphone", "mobile"), "electronics,smartphone"),
    (("laptop", "computer", "desktop", "gaming pc", "gaming pcs", "workstation", "monitor", "keyboard", "printer"), "electronics,laptop"),
    (("tablet", "ipad", "tv", "television", "theatre", "speaker", "audio", "headphone", "earbud", "camera", "photo", "gaming", "console", "accessory", "accessories", "charger", "cable", "power bank", "gadget", "electronic"), "electronics,gadget"),
    (("fashion", "clothing", "dress", "shirt", "trouser", "wear"), "fashion,clothing"),
    (("shoe", "sneaker", "sandal", "boot", "heel", "footwear"), "shoes,footwear"),
    (("bag", "handbag"), "bag,fashion"),
    (("watch", "smartwatch"), "watch,accessories"),
    (("jewel", "jewellery", "jewelry"), "jewellery,accessories"),
    (("beauty", "skincare", "makeup", "hair", "perfume", "sunscreen", "cosmetic"), "beauty,cosmetics"),
    (("grocery", "groceries", "food", "rice", "beans", "beverage", "snack", "meat", "fish"), "food,market"),
    (("agriculture", "farm", "seed", "fertilizer", "livestock", "poultry"), "food,market"),
    (("furniture", "sofa", "bed", "mattress", "table", "chair", "wardrobe", "decor"), "furniture,interior"),
    (("appliance", "refrigerator", "freezer", "washing", "cooker", "microwave", "blender", "kitchen"), "appliance,home"),
    (("sport", "fitness", "gym", "football", "cycling", "yoga"), "sports,fitness"),
    (("book", "stationery", "textbook", "notebook", "exam", "writing", "education"), "book,education"),
)


def _matches_any_rule_token(normalized: str, needles: tuple[str, ...]) -> bool:
    for needle in needles:
        escaped = re.escape(needle)
        suffix = "?" if needle.endswith("s") else "s?"
        if re.search(rf"(?<![a-z0-9]){escaped}{suffix}(?![a-z0-9])", normalized):
            return True
    return False


def tags_for_category(category: Any, product_family: Any = "") -> str:
    """Return the stable LoremFlickr tag pair for a category-like value."""

    for raw_value in (product_family, category):
        category_name = getattr(raw_value, "name", raw_value)
        normalized = _normalize_category_key(category_name)
        if not normalized:
            continue

        if normalized in CATEGORY_IMAGE_TAGS:
            return CATEGORY_IMAGE_TAGS[normalized]

        for needles, tags in CATEGORY_TAG_RULES:
            if _matches_any_rule_token(normalized, needles):
                return tags

    return "product,shopping"


def keyword_for_category(category: Any) -> str:
    """Backward-compatible alias for code that still expects a keyword."""

    return tags_for_category(category)


def _lock_value(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "product"
    return re.sub(r"\s+", "-", text)


def image_url_for_category(category: Any, product_identifier: Any = "", product_family: Any = "") -> str:
    tags = tags_for_category(category, product_family=product_family)
    encoded_tags = quote(tags, safe=",")
    encoded_lock = quote(_lock_value(product_identifier), safe="")
    return LOREMFLICKR_IMAGE_PATTERN.format(tags=encoded_tags, lock=encoded_lock)


def is_placeholder_image_url(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(
        NO_IMAGE_PLACEHOLDER_RE.search(text)
        or re.search(r"(^|/)placeholder\.(?:svg|png)(?:[?#].*)?$", text, re.IGNORECASE)
    )


def is_obsolete_unsplash_image_url(value: Any) -> bool:
    return bool(UNSPLASH_IMAGE_RE.search(str(value or "").strip()))


def existing_image_url_or_blank(value: Any) -> str:
    text = str(value or "").strip()
    return "" if is_placeholder_image_url(text) or is_obsolete_unsplash_image_url(text) else text


def image_url_for_product(
    *,
    title: Any = "",
    category: Any = "",
    product_family: Any = "",
    brand: Any = "",
    product_identifier: Any = "",
    slug: Any = "",
    product_id: Any = "",
) -> str:
    """Return a stable LoremFlickr URL using broad category tags and a lock."""

    identifier = product_identifier or slug or product_id or title or category or "product"
    return image_url_for_category(
        category,
        product_identifier=identifier,
        product_family=product_family,
    )
