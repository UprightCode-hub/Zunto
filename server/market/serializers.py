#server/market/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Category, Location, Product, ProductImage, 
    ProductVideo, Favorite, ProductReport
)
from core.file_validation import validate_uploaded_file

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for categories"""
    
    subcategories = serializers.SerializerMethodField()
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 
            'parent', 'full_path', 'subcategories', 'is_active', 
            'order', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']
    
    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return CategorySerializer(
                obj.subcategories.filter(is_active=True), 
                many=True
            ).data
        return []


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for locations"""
    
    full_address = serializers.SerializerMethodField()
    
    class Meta:
        model = Location
        fields = [
            'id', 'state', 'city', 'area', 'full_address',
            'latitude', 'longitude', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_full_address(self, obj):
        return str(obj)


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product images"""

    def validate_image(self, value):
        return validate_uploaded_file(
            value,
            allowed_mime_types={'image/jpeg', 'image/png', 'image/webp'},
            allowed_extensions={'.jpg', '.jpeg', '.png', '.webp'},
            max_bytes=5 * 1024 * 1024,
            field_name='image',
        )

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'caption', 'order', 'is_primary', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ProductVideoSerializer(serializers.ModelSerializer):
    """Serializer for product videos"""

    def validate_video(self, value):
        return validate_uploaded_file(
            value,
            allowed_mime_types={'video/mp4', 'video/webm', 'video/quicktime'},
            allowed_extensions={'.mp4', '.webm', '.mov'},
            max_bytes=20 * 1024 * 1024,
            field_name='video',
        )

    class Meta:
        model = ProductVideo
        fields = ['id', 'video', 'thumbnail', 'caption', 'duration', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class SellerInfoSerializer(serializers.ModelSerializer):
    """Basic seller information"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'profile_picture', 
            'is_verified', 'created_at'
        ]
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product listing (summary view)"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    location_display = serializers.CharField(source='location.__str__', read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description', 'listing_type', 'price', 'negotiable',
            'condition', 'brand', 'status', 'category_name', 
            'location_display', 'seller_name', 'primary_image',
            'is_featured', 'is_boosted', 'is_verified', 'is_favorited',
            'views_count', 'favorites_count', 'average_rating', 'review_count',
             'created_at'
        ]
        read_only_fields = fields
    
    def get_primary_image(self, obj):
        primary = obj.images.filter(is_primary=True).first()
        if primary:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        
                                 
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first_image.image.url)
            return first_image.image.url
        
        return None
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, 
                product=obj
            ).exists()
        return False


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail view"""
    
    category = CategorySerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    seller = SellerInfoSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    videos = ProductVideoSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'title', 'slug', 'description', 'listing_type',
            'category', 'location', 'price', 'negotiable', 'condition',
            'brand', 'quantity', 'status', 'is_featured', 'is_boosted',
            'is_verified', 'is_favorited', 'views_count', 'favorites_count',
            'shares_count', 'images', 'videos', 'created_at', 'updated_at'
        ]
        read_only_fields = fields
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(
                user=request.user, 
                product=obj
            ).exists()
        return False


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating products"""
    
    class Meta:
        model = Product
        fields = [
            'title', 'description', 'listing_type', 'category', 'location',
            'price', 'negotiable', 'condition', 'brand', 'quantity', 'status'
        ]
    
    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value
    
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1.")
        return value
    
    def validate(self, attrs):
                                          
        if attrs.get('listing_type') == 'service' and attrs.get('condition'):
            raise serializers.ValidationError({
                "condition": "Services cannot have a condition."
            })
        
                                        
        if attrs.get('listing_type') == 'product' and not attrs.get('condition'):
            raise serializers.ValidationError({
                "condition": "Products must have a condition."
            })
        
        return attrs
    
    def create(self, validated_data):
                                        
        validated_data['seller'] = self.context['request'].user
        return super().create(validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    """Serializer for favorites"""
    
    product = ProductListSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'product', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductReportSerializer(serializers.ModelSerializer):
    """Serializer for product reports"""
    
    reporter_name = serializers.CharField(source='reporter.get_full_name', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    moderated_by_name = serializers.CharField(source='moderated_by.get_full_name', read_only=True)
    
    class Meta:
        model = ProductReport
        fields = [
            'id', 'product', 'product_title', 'reporter', 'reporter_name',
            'reason', 'description', 'status', 'admin_notes', 'moderated_by', 'moderated_by_name',
            'created_at', 'resolved_at'
        ]
        read_only_fields = ['id', 'reporter', 'reporter_name', 'product_title', 'moderated_by', 'moderated_by_name',
                           'status', 'admin_notes', 'created_at', 'resolved_at']
    
    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)
