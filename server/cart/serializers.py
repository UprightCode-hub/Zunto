#server/cart/serializers.py
from rest_framework import serializers
from market.serializers import ProductListSerializer
from .models import Cart, CartItem, UserScore


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'price_at_addition', 'total_price', 'added_at']
        read_only_fields = ['id', 'price_at_addition', 'added_at', 'total_price']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'updated_at']


class UserScoreSerializer(serializers.ModelSerializer):
    """Serializer for user scoring data"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    score_tier = serializers.CharField(read_only=True)
    
    class Meta:
        model = UserScore
        fields = [
            'user_email', 'user_name', 'abandonment_score', 
            'value_score', 'conversion_score', 'hesitation_score',
            'composite_score', 'score_tier', 'discount_eligibility',
            'recommended_discount', 'promo_code', 'last_calculated'
        ]
        read_only_fields = fields


class ScoreAnalyticsSummarySerializer(serializers.Serializer):
    """Serializer for score analytics summary"""
    averages = serializers.DictField()
    range = serializers.DictField()
    distribution = serializers.DictField()
    total_users_scored = serializers.IntegerField()


class ValueByTierSerializer(serializers.Serializer):
    """Serializer for abandoned value by score tier"""
    high_value = serializers.DictField()
    medium_value = serializers.DictField()
    low_value = serializers.DictField()
    at_risk = serializers.DictField()
