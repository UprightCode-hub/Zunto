#server/market/management/commands/create_sample_categories.py
from django.core.management.base import BaseCommand
from market.models import Category


class Command(BaseCommand):
    help = 'Create sample categories for development'
    
    def handle(self, *args, **kwargs):
        categories_data = [
            {
                'name': 'Electronics',
                'icon': '📱',
                'subcategories': [
                    {'name': 'Phones & Tablets', 'icon': '📱'},
                    {'name': 'Computers & Laptops', 'icon': '💻'},
                    {'name': 'TV & Audio', 'icon': '📺'},
                    {'name': 'Cameras', 'icon': '📷'},
                ]
            },
            {
                'name': 'Fashion',
                'icon': '👔',
                'subcategories': [
                    {'name': 'Men\'s Clothing', 'icon': '👔'},
                    {'name': 'Women\'s Clothing', 'icon': '👗'},
                    {'name': 'Shoes', 'icon': '👟'},
                    {'name': 'Accessories', 'icon': '👜'},
                ]
            },
            {
                'name': 'Home & Living',
                'icon': '🏠',
                'subcategories': [
                    {'name': 'Furniture', 'icon': '🛋️'},
                    {'name': 'Kitchen & Dining', 'icon': '🍽️'},
                    {'name': 'Home Decor', 'icon': '🖼️'},
                    {'name': 'Garden', 'icon': '🌱'},
                ]
            },
            {
                'name': 'Vehicles',
                'icon': '🚗',
                'subcategories': [
                    {'name': 'Cars', 'icon': '🚗'},
                    {'name': 'Motorcycles', 'icon': '🏍️'},
                    {'name': 'Auto Parts', 'icon': '⚙️'},
                ]
            },
            {
                'name': 'Services',
                'icon': '🔧',
                'subcategories': [
                    {'name': 'Repairs & Maintenance', 'icon': '🔧'},
                    {'name': 'Home Services', 'icon': '🏠'},
                    {'name': 'Professional Services', 'icon': '💼'},
                    {'name': 'Events & Entertainment', 'icon': '🎉'},
                ]
            },
            {
                'name': 'Jobs',
                'icon': '💼',
                'subcategories': [
                    {'name': 'Full-time', 'icon': '👔'},
                    {'name': 'Part-time', 'icon': '⏰'},
                    {'name': 'Freelance', 'icon': '💻'},
                    {'name': 'Internship', 'icon': '🎓'},
                ]
            },
        ]
        
        for cat_data in categories_data:
            parent, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon': cat_data['icon'],
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created category: {parent.name}')
                )
            
                                  
            for subcat_data in cat_data.get('subcategories', []):
                subcat, sub_created = Category.objects.get_or_create(
                    name=subcat_data['name'],
                    parent=parent,
                    defaults={
                        'icon': subcat_data['icon'],
                        'is_active': True
                    }
                )
                
                if sub_created:
                    self.stdout.write(
                        self.style.SUCCESS(f'  Created subcategory: {subcat.name}')
                    )
