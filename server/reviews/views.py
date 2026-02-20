#server/reviews/views.py
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.throttling import SimpleRateThrottle

from .models import (
    ProductReview, SellerReview, ReviewResponse, 
    ReviewHelpful, ReviewImage, ReviewFlag
)
from .serializers import (
    ProductReviewSerializer, SellerReviewSerializer,
    ReviewResponseSerializer, ReviewImageSerializer,
    ReviewFlagSerializer, ProductReviewStatsSerializer,
    SellerReviewStatsSerializer
)
from .permissions import IsReviewerOrReadOnly, IsSellerOrReadOnly
from market.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()


class PublicReviewStatsThrottle(SimpleRateThrottle):
    scope = 'public_review_stats'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': f'ip:{ident}:{request.path}'}


class ProductReviewListCreateView(generics.ListCreateAPIView):
    """List and create product reviews"""
    
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rating', 'is_verified_purchase']
    ordering_fields = ['created_at', 'rating', 'helpful_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        return ProductReview.objects.filter(
            product__slug=product_slug,
            is_approved=True
        ).select_related('reviewer', 'product').prefetch_related('images', 'response')

    def perform_create(self, serializer):
        review = serializer.save()
        
                              
        EmailService.send_seller_review_email(review)

class ProductReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, and delete product review"""
    
    serializer_class = ProductReviewSerializer
    permission_classes = [IsReviewerOrReadOnly]
    
    def get_queryset(self):
        return ProductReview.objects.select_related(
            'reviewer', 'product'
        ).prefetch_related('images', 'response')


class MyProductReviewsView(generics.ListAPIView):
    """List current user's product reviews"""
    
    serializer_class = ProductReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return ProductReview.objects.filter(
            reviewer=self.request.user
        ).select_related('product').prefetch_related('images')


class SellerReviewListCreateView(generics.ListCreateAPIView):
    """List and create seller reviews"""
    
    serializer_class = SellerReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rating', 'is_verified_transaction']
    ordering_fields = ['created_at', 'rating', 'helpful_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        seller_id = self.kwargs.get('seller_id')
        return SellerReview.objects.filter(
            seller__id=seller_id,
            is_approved=True
        ).select_related('reviewer', 'seller', 'product').prefetch_related('images', 'response')

    def perform_create(self, serializer):
        review = serializer.save()
        
                              
        EmailService.send_seller_review_email(review)

class SellerReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, and delete seller review"""
    
    serializer_class = SellerReviewSerializer
    permission_classes = [IsReviewerOrReadOnly]
    
    def get_queryset(self):
        return SellerReview.objects.select_related(
            'reviewer', 'seller', 'product'
        ).prefetch_related('images', 'response')


class MySellerReviewsView(generics.ListAPIView):
    """List current user's seller reviews"""
    
    serializer_class = SellerReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return SellerReview.objects.filter(
            reviewer=self.request.user
        ).select_related('seller', 'product').prefetch_related('images')


class ReviewsReceivedView(generics.ListAPIView):
    """List reviews received by current user (as seller)"""
    
    serializer_class = SellerReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']
    
    def get_queryset(self):
        return SellerReview.objects.filter(
            seller=self.request.user
        ).select_related('reviewer', 'product').prefetch_related('images', 'response')


class ReviewResponseCreateView(APIView):
    """Create or update response to a review"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, review_type, review_id):
                        
        if review_type == 'product':
            review = get_object_or_404(ProductReview, id=review_id)
                                             
            if review.product.seller != request.user:
                return Response({
                    'error': 'Only the product seller can respond to this review.'
                }, status=status.HTTP_403_FORBIDDEN)
            
                                              
            if hasattr(review, 'response'):
                                          
                review.response.response = request.data.get('response')
                review.response.save()
                serializer = ReviewResponseSerializer(review.response)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
                                 
            response_obj = ReviewResponse.objects.create(
                product_review=review,
                responder=request.user,
                response=request.data.get('response')
            )
        
        elif review_type == 'seller':
            review = get_object_or_404(SellerReview, id=review_id)
                                                        
            if review.seller != request.user:
                return Response({
                    'error': 'Only the seller can respond to this review.'
                }, status=status.HTTP_403_FORBIDDEN)
            
                                              
            if hasattr(review, 'response'):
                                          
                review.response.response = request.data.get('response')
                review.response.save()
                serializer = ReviewResponseSerializer(review.response)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
                                 
            response_obj = ReviewResponse.objects.create(
                seller_review=review,
                responder=request.user,
                response=request.data.get('response')
            )
        else:
            return Response({
                'error': 'Invalid review type. Must be "product" or "seller".'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ReviewResponseSerializer(response_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReviewHelpfulToggleView(APIView):
    """Vote if review is helpful or not"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, review_type, review_id):
        vote_type = request.data.get('vote')                              
        
        if vote_type not in ['helpful', 'not_helpful']:
            return Response({
                'error': 'Vote must be "helpful" or "not_helpful".'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if review_type == 'product':
            review = get_object_or_404(ProductReview, id=review_id)
            existing_vote = ReviewHelpful.objects.filter(
                product_review=review,
                user=request.user
            ).first()
            
            if existing_vote:
                             
                old_vote = existing_vote.vote
                existing_vote.vote
                old_vote = existing_vote.vote
                existing_vote.vote = vote_type
                existing_vote.save()
                
                               
                if old_vote == 'helpful':
                    review.helpful_count -= 1
                else:
                    review.not_helpful_count -= 1
                
                if vote_type == 'helpful':
                    review.helpful_count += 1
                else:
                    review.not_helpful_count += 1
                
                review.save(update_fields=['helpful_count', 'not_helpful_count'])
                
                return Response({
                    'message': 'Vote updated successfully.',
                    'vote': vote_type
                }, status=status.HTTP_200_OK)
            else:
                                 
                ReviewHelpful.objects.create(
                    product_review=review,
                    user=request.user,
                    vote=vote_type
                )
                
                               
                if vote_type == 'helpful':
                    review.helpful_count += 1
                else:
                    review.not_helpful_count += 1
                
                review.save(update_fields=['helpful_count', 'not_helpful_count'])
                
                return Response({
                    'message': 'Vote recorded successfully.',
                    'vote': vote_type
                }, status=status.HTTP_201_CREATED)
        
        elif review_type == 'seller':
            review = get_object_or_404(SellerReview, id=review_id)
            existing_vote = ReviewHelpful.objects.filter(
                seller_review=review,
                user=request.user
            ).first()
            
            if existing_vote:
                             
                old_vote = existing_vote.vote
                existing_vote.vote = vote_type
                existing_vote.save()
                
                               
                if old_vote == 'helpful':
                    review.helpful_count -= 1
                else:
                    review.not_helpful_count -= 1
                
                if vote_type == 'helpful':
                    review.helpful_count += 1
                else:
                    review.not_helpful_count += 1
                
                review.save(update_fields=['helpful_count', 'not_helpful_count'])
                
                return Response({
                    'message': 'Vote updated successfully.',
                    'vote': vote_type
                }, status=status.HTTP_200_OK)
            else:
                                 
                ReviewHelpful.objects.create(
                    seller_review=review,
                    user=request.user,
                    vote=vote_type
                )
                
                               
                if vote_type == 'helpful':
                    review.helpful_count += 1
                else:
                    review.not_helpful_count += 1
                
                review.save(update_fields=['helpful_count', 'not_helpful_count'])
                
                return Response({
                    'message': 'Vote recorded successfully.',
                    'vote': vote_type
                }, status=status.HTTP_201_CREATED)
        
        else:
            return Response({
                'error': 'Invalid review type. Must be "product" or "seller".'
            }, status=status.HTTP_400_BAD_REQUEST)


class ReviewImageUploadView(APIView):
    """Upload images to reviews"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, review_type, review_id):
        if review_type == 'product':
            review = get_object_or_404(ProductReview, id=review_id, reviewer=request.user)
            
                                                          
            if review.images.count() >= 5:
                return Response({
                    'error': 'Maximum 5 images allowed per review.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ReviewImageSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(product_review=review)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        elif review_type == 'seller':
            review = get_object_or_404(SellerReview, id=review_id, reviewer=request.user)
            
                              
            if review.images.count() >= 5:
                return Response({
                    'error': 'Maximum 5 images allowed per review.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ReviewImageSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(seller_review=review)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            return Response({
                'error': 'Invalid review type.'
            }, status=status.HTTP_400_BAD_REQUEST)


class ReviewFlagCreateView(generics.CreateAPIView):
    """Flag a review as inappropriate"""
    
    serializer_class = ReviewFlagSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductReviewStatsView(APIView):
    """Get statistics for product reviews"""
    
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PublicReviewStatsThrottle]

    def get(self, request, product_slug):
        product = get_object_or_404(Product, slug=product_slug)
        
        reviews = ProductReview.objects.filter(
            product=product,
            is_approved=True
        )

        stats = reviews.aggregate(
            total_reviews=Count('id'),
            average_rating=Avg('rating'),
            rating_5=Count('id', filter=Q(rating=5)),
            rating_4=Count('id', filter=Q(rating=4)),
            rating_3=Count('id', filter=Q(rating=3)),
            rating_2=Count('id', filter=Q(rating=2)),
            rating_1=Count('id', filter=Q(rating=1)),
            verified_purchases=Count('id', filter=Q(is_verified_purchase=True)),
        )

        total_reviews = stats.get('total_reviews') or 0
        if total_reviews == 0:
            return Response({
                'total_reviews': 0,
                'average_rating': 0,
                'rating_distribution': {
                    '5': 0, '4': 0, '3': 0, '2': 0, '1': 0
                },
                'verified_purchases': 0
            })

        data = {
            'total_reviews': total_reviews,
            'average_rating': round(stats.get('average_rating') or 0, 2),
            'rating_distribution': {
                '5': stats.get('rating_5') or 0,
                '4': stats.get('rating_4') or 0,
                '3': stats.get('rating_3') or 0,
                '2': stats.get('rating_2') or 0,
                '1': stats.get('rating_1') or 0,
            },
            'verified_purchases': stats.get('verified_purchases') or 0,
        }
        
        serializer = ProductReviewStatsSerializer(data)
        return Response(serializer.data)


class SellerReviewStatsView(APIView):
    """Get statistics for seller reviews"""
    
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PublicReviewStatsThrottle]

    def get(self, request, seller_id):
        seller = get_object_or_404(User, id=seller_id)
        
        reviews = SellerReview.objects.filter(
            seller=seller,
            is_approved=True
        )

        stats = reviews.aggregate(
            total_reviews=Count('id'),
            average_rating=Avg('rating'),
            rating_5=Count('id', filter=Q(rating=5)),
            rating_4=Count('id', filter=Q(rating=4)),
            rating_3=Count('id', filter=Q(rating=3)),
            rating_2=Count('id', filter=Q(rating=2)),
            rating_1=Count('id', filter=Q(rating=1)),
            average_communication=Avg('communication_rating'),
            average_reliability=Avg('reliability_rating'),
            average_professionalism=Avg('professionalism_rating'),
            verified_transactions=Count('id', filter=Q(is_verified_transaction=True)),
        )

        total_reviews = stats.get('total_reviews') or 0
        if total_reviews == 0:
            return Response({
                'total_reviews': 0,
                'average_rating': 0,
                'rating_distribution': {
                    '5': 0, '4': 0, '3': 0, '2': 0, '1': 0
                },
                'average_communication': 0,
                'average_reliability': 0,
                'average_professionalism': 0,
                'verified_transactions': 0
            })

        data = {
            'total_reviews': total_reviews,
            'average_rating': round(stats.get('average_rating') or 0, 2),
            'rating_distribution': {
                '5': stats.get('rating_5') or 0,
                '4': stats.get('rating_4') or 0,
                '3': stats.get('rating_3') or 0,
                '2': stats.get('rating_2') or 0,
                '1': stats.get('rating_1') or 0,
            },
            'average_communication': round(stats.get('average_communication') or 0, 2),
            'average_reliability': round(stats.get('average_reliability') or 0, 2),
            'average_professionalism': round(stats.get('average_professionalism') or 0, 2),
            'verified_transactions': stats.get('verified_transactions') or 0,
        }
        
        serializer = SellerReviewStatsSerializer(data)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@throttle_classes([PublicReviewStatsThrottle])
def top_rated_products(request):
    """Get top rated products"""
    
    from market.models import Product
    from market.serializers import ProductListSerializer
    
                                                
    products = Product.objects.filter(
        status='active',
        reviews__is_approved=True
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).filter(
        review_count__gte=5,                      
        avg_rating__gte=4.0                  
    ).order_by('-avg_rating', '-review_count')[:20]
    
    serializer = ProductListSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@throttle_classes([PublicReviewStatsThrottle])
def top_rated_sellers(request):
    """Get top rated sellers"""
    
    from accounts.serializers import SellerInfoSerializer
    
                                               
    sellers = User.objects.filter(
        role__in=['seller', 'service_provider'],
        seller_reviews_received__is_approved=True
    ).annotate(
        avg_rating=Avg('seller_reviews_received__rating'),
        review_count=Count('seller_reviews_received')
    ).filter(
        review_count__gte=5,                      
        avg_rating__gte=4.0                  
    ).order_by('-avg_rating', '-review_count')[:20]
    
    serializer = SellerInfoSerializer(sellers, many=True)
    return Response(serializer.data)
