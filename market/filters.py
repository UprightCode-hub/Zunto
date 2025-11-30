# market/filters.py
import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    """Filter for products"""
    
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = django_filters.CharFilter(field_name='category__slug')
    location = django_filters.CharFilter(field_name='location__id')
    state = django_filters.CharFilter(field_name='location__state', lookup_expr='iexact')
    city = django_filters.CharFilter(field_name='location__city', lookup_expr='iexact')
    condition = django_filters.MultipleChoiceFilter(choices=Product.CONDITION_CHOICES)
    listing_type = django_filters.ChoiceFilter(choices=Product.LISTING_TYPE_CHOICES)
    is_negotiable = django_filters.BooleanFilter(field_name='negotiable')
    
    class Meta:
        model = Product
        fields = [
            'min_price', 'max_price', 'category', 'location', 
            'state', 'city', 'condition', 'listing_type', 'is_negotiable'
        ]