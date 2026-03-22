#server/market/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Category, Location, Product, ProductImage, 
    ProductVideo, Favorite, ProductReport
)
from core.file_validation import validate_uploaded_file
from accounts.seller_utils import get_seller_profile, is_active_seller, is_pending_seller, is_verified_seller

User = get_user_model()

def _build_media_url(request, image_field):
    image_url = image_field.url
    if request:
        return request.build_absolute_uri(image_url)
    return image_url


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
            malware_scan_mode='async',
        )

    class Meta:
        model = ProductVideo
        fields = [
            'id', 'video', 'thumbnail', 'caption', 'duration',
            'security_scan_status', 'security_scan_reason', 'scanned_at', 'uploaded_at'
        ]
        read_only_fields = ['id', 'security_scan_status', 'security_scan_reason', 'scanned_at', 'uploaded_at']

    def create(self, validated_data):
        instance = super().create(validated_data)

        from market.tasks import schedule_product_video_scan

        schedule_product_video_scan(str(instance.id))
        return instance


class SellerInfoSerializer(serializers.ModelSerializer):
    """Basic seller information"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    isSellerActive = serializers.SerializerMethodField()
    isSellerPending = serializers.SerializerMethodField()
    isVerifiedSeller = serializers.SerializerMethodField()
    sellerProfileStatus = serializers.SerializerMethodField()
    sellerCommerceMode = serializers.SerializerMethodField()
    isManagedCommerceEligible = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'profile_picture', 
            'is_verified', 'is_verified_seller', 'created_at',
            'isSellerActive', 'isSellerPending', 'isVerifiedSeller', 'sellerProfileStatus',
            'sellerCommerceMode', 'isManagedCommerceEligible'
        ]
        read_only_fields = fields

    def get_isSellerActive(self, obj):
        return is_active_seller(obj)

    def get_isSellerPending(self, obj):
        return is_pending_seller(obj)

    def get_isVerifiedSeller(self, obj):
        return is_verified_seller(obj)

    def get_sellerProfileStatus(self, obj):
        seller_profile = get_seller_profile(obj)
        return getattr(seller_profile, 'status', None)

    def get_sellerCommerceMode(self, obj):
        seller_profile = get_seller_profile(obj)
        if seller_profile is not None:
            return seller_profile.seller_commerce_mode
        return getattr(obj, 'seller_commerce_mode', 'direct')

    def get_isManagedCommerceEligible(self, obj):
        seller_profile = get_seller_profile(obj)
        if seller_profile is None:
            return bool(
                getattr(obj, 'role', None) == 'seller'
                and getattr(obj, 'seller_commerce_mode', 'direct') == 'managed'
                and getattr(obj, 'is_verified', False)
            )
        return bool(
            seller_profile.status == 'approved'
            and seller_profile.is_verified_seller
            and seller_profile.seller_commerce_mode == 'managed'
        )


class ProductListSerializer(serializers.ModelSerializer):
    """Serializer for product listing (summary view)"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    location_display = serializers.CharField(source='location.__str__', read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    seller_commerce_mode = serializers.SerializerMethodField()
    seller_profile_status = serializers.SerializerMethodField()
    is_managed_commerce_eligible = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description', 'listing_type', 'price', 'negotiable',
            'condition', 'brand', 'status', 'category_name', 
            'location_display', 'seller_name', 'primary_image',
            'is_featured', 'is_boosted', 'is_verified', 'is_verified_product', 'is_favorited',
            'views_count', 'favorites_count', 'average_rating', 'review_count',
            'seller_commerce_mode', 'seller_profile_status', 'is_managed_commerce_eligible',
             'created_at'
        ]
        read_only_fields = fields
    

    def get_average_rating(self, obj):
        if hasattr(obj, 'avg_rating'):
            return round(float(obj.avg_rating or 0), 2)
        return obj.average_rating

    def get_review_count(self, obj):
        if hasattr(obj, 'approved_review_count'):
            return int(obj.approved_review_count or 0)
        return obj.review_count

    def get_primary_image(self, obj):
        request = self.context.get('request')

        prefetched_images = getattr(obj, 'prefetched_images', None)
        if prefetched_images:
            return _build_media_url(request, prefetched_images[0].image)

        primary_image = obj.images.order_by('-is_primary', 'order', 'uploaded_at').first()
        if primary_image:
            return _build_media_url(request, primary_image.image)

        return None

    def get_is_favorited(self, obj):
        return bool(getattr(obj, 'is_favorited', False))

    def get_seller_commerce_mode(self, obj):
        seller = getattr(obj, 'seller', None)
        if not seller:
            return 'direct'
        seller_profile = get_seller_profile(seller)
        if seller_profile is not None:
            return seller_profile.seller_commerce_mode
        return getattr(seller, 'seller_commerce_mode', 'direct')

    def get_seller_profile_status(self, obj):
        seller = getattr(obj, 'seller', None)
        if not seller:
            return None
        seller_profile = get_seller_profile(seller)
        if seller_profile is not None:
            return seller_profile.status
        return 'missing_profile'

    def get_is_managed_commerce_eligible(self, obj):
        seller = getattr(obj, 'seller', None)
        if not seller:
            return False

        seller_profile = get_seller_profile(seller)
        if seller_profile is None:
            return bool(
                getattr(seller, 'role', None) == 'seller'
                and getattr(seller, 'seller_commerce_mode', 'direct') == 'managed'
                and getattr(seller, 'is_verified', False)
            )

        return bool(
            seller_profile.status == 'approved'
            and seller_profile.is_verified_seller
            and seller_profile.seller_commerce_mode == 'managed'
        )


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer for product detail view"""
    
    category = CategorySerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    seller = SellerInfoSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    videos = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'title', 'slug', 'description', 'listing_type',
            'category', 'location', 'price', 'negotiable', 'condition',
            'brand', 'quantity', 'status', 'is_featured', 'is_boosted',
            'is_verified', 'is_verified_product', 'is_favorited', 'views_count', 'favorites_count',
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

    def get_videos(self, obj):
        request = self.context.get('request')
        clean_videos = obj.videos.filter(security_scan_status=ProductVideo.SCAN_CLEAN)
        return ProductVideoSerializer(clean_videos, many=True, context={'request': request}).data


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


class ProductVideoModerationSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    seller_id = serializers.UUIDField(source='product.seller_id', read_only=True)

    class Meta:
        model = ProductVideo
        fields = [
            'id', 'product', 'product_slug', 'product_title', 'seller_id',
            'video', 'caption', 'duration', 'security_scan_status',
            'security_scan_reason', 'security_quarantine_path', 'scanned_at', 'uploaded_at'
        ]
        read_only_fields = fields
