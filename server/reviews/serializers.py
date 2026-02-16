# reviews/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Avg
from .models import (
    ProductReview, SellerReview, ReviewResponse, 
    ReviewHelpful, ReviewImage, ReviewFlag
)
from chat.models import has_completed_confirmation

User = get_user_model()


class ReviewerSerializer(serializers.ModelSerializer):
    """Basic reviewer information"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'full_name', 'profile_picture', 'is_verified']
        read_only_fields = fields


class ReviewImageSerializer(serializers.ModelSerializer):
    """Serializer for review images"""
    
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ReviewResponseSerializer(serializers.ModelSerializer):
    """Serializer for review responses"""
    
    responder_name = serializers.CharField(source='responder.get_full_name', read_only=True)
    
    class Meta:
        model = ReviewResponse
        fields = ['id', 'responder', 'responder_name', 'response', 'created_at', 'updated_at']
        read_only_fields = ['id', 'responder', 'responder_name', 'created_at', 'updated_at']


class ProductReviewSerializer(serializers.ModelSerializer):
    """Serializer for product reviews"""
    
    reviewer = ReviewerSerializer(read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = ReviewResponseSerializer(read_only=True)
    has_voted = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    average_detailed_rating = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'reviewer', 'rating', 'title', 'comment',
            'quality_rating', 'value_rating', 'accuracy_rating',
            'average_detailed_rating', 'is_verified_purchase',
            'helpful_count', 'not_helpful_count', 'has_voted', 'user_vote',
            'images', 'response', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'reviewer', 'is_verified_purchase', 'helpful_count', 
            'not_helpful_count', 'created_at', 'updated_at'
        ]
    
    def get_has_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ReviewHelpful.objects.filter(
                product_review=obj,
                user=request.user
            ).exists()
        return False
    
    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = ReviewHelpful.objects.filter(
                product_review=obj,
                user=request.user
            ).first()
            return vote.vote if vote else None
        return None
    
    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def validate(self, attrs):
        # Check if user already reviewed this product
        request = self.context.get('request')
        product = attrs.get('product')
        
        if ProductReview.objects.filter(
            product=product,
            reviewer=request.user
        ).exists():
            raise serializers.ValidationError(
                "You have already reviewed this product."
            )
        
        # User cannot review their own product
        if product.seller == request.user:
            raise serializers.ValidationError(
                "You cannot review your own product."
            )

        if not has_completed_confirmation(
            buyer=request.user,
            seller=product.seller,
            product=product,
        ):
            raise serializers.ValidationError(
                "Review is only available after both buyer and seller confirm completion for this product."
            )

        return attrs
    
    def create(self, validated_data):
        validated_data['reviewer'] = self.context['request'].user
        validated_data['is_verified_purchase'] = True
        return super().create(validated_data)


class SellerReviewSerializer(serializers.ModelSerializer):
    """Serializer for seller reviews"""
    
    reviewer = ReviewerSerializer(read_only=True)
    seller_name = serializers.CharField(source='seller.get_full_name', read_only=True)
    product_title = serializers.CharField(source='product.title', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = ReviewResponseSerializer(read_only=True)
    has_voted = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    average_detailed_rating = serializers.FloatField(read_only=True)
    
    class Meta:
        model = SellerReview
        fields = [
            'id', 'seller', 'seller_name', 'reviewer', 'product', 'product_title',
            'rating', 'title', 'comment', 'communication_rating', 
            'reliability_rating', 'professionalism_rating', 'average_detailed_rating',
            'is_verified_transaction', 'helpful_count', 'not_helpful_count',
            'has_voted', 'user_vote', 'images', 'response', 
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'reviewer', 'seller_name', 'product_title', 
            'is_verified_transaction', 'helpful_count', 'not_helpful_count',
            'created_at', 'updated_at'
        ]
    
    def get_has_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ReviewHelpful.objects.filter(
                seller_review=obj,
                user=request.user
            ).exists()
        return False
    
    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            vote = ReviewHelpful.objects.filter(
                seller_review=obj,
                user=request.user
            ).first()
            return vote.vote if vote else None
        return None
    
    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def validate(self, attrs):
        request = self.context.get('request')
        seller = attrs.get('seller')
        product = attrs.get('product')
        
        # User cannot review themselves
        if seller == request.user:
            raise serializers.ValidationError(
                "You cannot review yourself."
            )
        
        # Check if user already reviewed this seller for this product
        if product and SellerReview.objects.filter(
            seller=seller,
            reviewer=request.user,
            product=product
        ).exists():
            raise serializers.ValidationError(
                "You have already reviewed this seller for this product."
            )

        if product and product.seller != seller:
            raise serializers.ValidationError(
                "Selected product does not belong to the selected seller."
            )

        if product and not has_completed_confirmation(
            buyer=request.user,
            seller=seller,
            product=product,
        ):
            raise serializers.ValidationError(
                "Seller review is only available after both buyer and seller confirm completion for this product."
            )

        return attrs
    
    def create(self, validated_data):
        validated_data['reviewer'] = self.context['request'].user
        validated_data['is_verified_transaction'] = True
        return super().create(validated_data)


class ReviewFlagSerializer(serializers.ModelSerializer):
    """Serializer for flagging reviews"""
    
    flagger_name = serializers.CharField(source='flagger.get_full_name', read_only=True)
    
    class Meta:
        model = ReviewFlag
        fields = [
            'id', 'product_review', 'seller_review', 'flagger', 'flagger_name',
            'reason', 'description', 'status', 'admin_notes',
            'created_at', 'resolved_at'
        ]
        read_only_fields = [
            'id', 'flagger', 'flagger_name', 'status', 
            'admin_notes', 'created_at', 'resolved_at'
        ]
    
    def validate(self, attrs):
        # Must flag either product review or seller review, not both
        if not attrs.get('product_review') and not attrs.get('seller_review'):
            raise serializers.ValidationError(
                "Must specify either product_review or seller_review."
            )
        
        if attrs.get('product_review') and attrs.get('seller_review'):
            raise serializers.ValidationError(
                "Cannot flag both product_review and seller_review at once."
            )
        
        return attrs
    
    def create(self, validated_data):
        validated_data['flagger'] = self.context['request'].user
        return super().create(validated_data)


class ProductReviewStatsSerializer(serializers.Serializer):
    """Statistics for product reviews"""
    
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField()
    verified_purchases = serializers.IntegerField()


class SellerReviewStatsSerializer(serializers.Serializer):
    """Statistics for seller reviews"""
    
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField()
    average_communication = serializers.FloatField()
    average_reliability = serializers.FloatField()
    average_professionalism = serializers.FloatField()
    verified_transactions = serializers.IntegerField()
