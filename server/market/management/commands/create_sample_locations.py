#server/market/management/commands/create_sample_locations.py
from django.core.management.base import BaseCommand
from market.models import Location


class Command(BaseCommand):
    help = 'Create sample locations for development'
    
    def handle(self, *args, **kwargs):
        locations_data = [
            {'state': 'Lagos', 'city': 'Ikeja', 'area': 'Allen Avenue'},
            {'state': 'Lagos', 'city': 'Ikeja', 'area': 'Computer Village'},
            {'state': 'Lagos', 'city': 'Lekki', 'area': 'Phase 1'},
            {'state': 'Lagos', 'city': 'Victoria Island', 'area': ''},
            {'state': 'Lagos', 'city': 'Surulere', 'area': ''},
            {'state': 'Abuja', 'city': 'Wuse', 'area': 'Wuse 2'},
            {'state': 'Abuja', 'city': 'Garki', 'area': ''},
            {'state': 'Abuja', 'city': 'Maitama', 'area': ''},
            {'state': 'Rivers', 'city': 'Port Harcourt', 'area': 'GRA'},
            {'state': 'Oyo', 'city': 'Ibadan', 'area': 'Bodija'},
        ]
        
        for loc_data in locations_data:
            location, created = Location.objects.get_or_create(
                state=loc_data['state'],
                city=loc_data['city'],
                area=loc_data['area'],
                defaults={'is_active': True}
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created location: {location}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Location already exists: {location}')
                )
