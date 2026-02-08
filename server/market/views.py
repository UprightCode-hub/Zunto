# market/views.py
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render


from .models import (
    Category, Location, Product, ProductImage, 
    ProductVideo, Favorite, ProductView, ProductReport
)
from .serializers import (
    CategorySerializer, LocationSerializer, 
    ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, ProductImageSerializer,
    ProductVideoSerializer, FavoriteSerializer, ProductReportSerializer
)
from .permissions import IsSellerOrReadOnly
from .filters import ProductFilter


class CategoryListView(generics.ListAPIView):
    """List all active categories"""
    
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        # Only return top-level categories
        return Category.objects.filter(is_active=True, parent=None)


class LocationListView(generics.ListAPIView):
    """List all active locations"""
    
    serializer_class = LocationSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Location.objects.filter(is_active=True)
    filter_backends = [filters.SearchFilter]
    search_fields = ['state', 'city', 'area']


class ProductListCreateView(generics.ListCreateAPIView):
    """List and create products"""
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # filterset_class = ProductFilter
    search_fields = ['title', 'description', 'brand']
    ordering_fields = ['created_at', 'price', 'views_count', 'favorites_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateUpdateSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        queryset = Product.objects.filter(status='active').select_related(
            'category', 'location', 'seller'
        ).prefetch_related('images')
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

def product_list_page(request):
    """
    Renders the main product listing HTML page.
    The actual product data is loaded via JavaScript AJAX calls.
    """
    return render(request, 'products.html')

def analytics_dashboard(request):
    return render(request, "Analytic/Analytics dashboard.html")

def product_list(request):
    """
    Displays a list of active products.
    """
    products = Product.objects.filter(status='active', quantity__gt=0).order_by('-created_at')
    context = {
        'products': products,
        'page_title': 'Our Amazing Products',
    }
    return render(request, 'templates/product_list.html', context)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, and delete product"""
    
    permission_classes = [IsSellerOrReadOnly]
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductCreateUpdateSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        return Product.objects.select_related(
            'category', 'location', 'seller'
        ).prefetch_related('images', 'videos')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track view
        self.track_view(instance)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def track_view(self, product):
        """Track product view"""
        user = self.request.user if self.request.user.is_authenticated else None
        ip_address = self.get_client_ip()
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        
        # Don't count seller's own views
        if user and user == product.seller:
            return
        
        # Create view record
        ProductView.objects.create(
            product=product,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Increment view count
        product.views_count += 1
        product.save(update_fields=['views_count'])
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class MyProductsView(generics.ListAPIView):
    """List current user's products"""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'price', 'views_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Product.objects.filter(
            seller=self.request.user
        ).select_related('category', 'location').prefetch_related('images')


class ProductImageUploadView(APIView):
    """Upload product images"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, product_slug):
        product = get_object_or_404(Product, slug=product_slug, seller=request.user)
        
        # Check if max images reached (e.g., 10 images max)
        if product.images.count() >= 10:
            return Response({
                'error': 'Maximum 10 images allowed per product.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProductImageSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, product_slug, image_id):
        product = get_object_or_404(Product, slug=product_slug, seller=request.user)
        image = get_object_or_404(ProductImage, id=image_id, product=product)
        
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductVideoUploadView(APIView):
    """Upload product videos"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, product_slug):
        product = get_object_or_404(Product, slug=product_slug, seller=request.user)
        
        # Check if max videos reached (e.g., 3 videos max)
        if product.videos.count() >= 3:
            return Response({
                'error': 'Maximum 3 videos allowed per product.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProductVideoSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FavoriteToggleView(APIView):
    """Add or remove product from favorites"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, product_slug):
        product = get_object_or_404(Product, slug=product_slug)
        user = request.user
        
        favorite, created = Favorite.objects.get_or_create(
            user=user,
            product=product
        )
        
        if not created:
            # Already favorited, so remove it
            favorite.delete()
            product.favorites_count -= 1
            product.save(update_fields=['favorites_count'])
            return Response({
                'message': 'Product removed from favorites.',
                'is_favorited': False
            }, status=status.HTTP_200_OK)
        else:
            # Newly favorited
            product.favorites_count += 1
            product.save(update_fields=['favorites_count'])
            return Response({'message': 'Product added to favorites.',
                'is_favorited': True
            }, status=status.HTTP_201_CREATED)


class FavoriteListView(generics.ListAPIView):
    """List user's favorite products"""
    
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Favorite.objects.filter(
            user=self.request.user
        ).select_related('product__category', 'product__location', 'product__seller')


class ProductReportCreateView(generics.CreateAPIView):
    """Report a product"""
    
    serializer_class = ProductReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        serializer.save(reporter=self.request.user, product=product)


class FeaturedProductsView(generics.ListAPIView):
    """List featured products"""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Product.objects.filter(
            status='active',
            is_featured=True
        ).select_related('category', 'location', 'seller').prefetch_related('images')[:20]


class BoostedProductsView(generics.ListAPIView):
    """List boosted products"""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        from django.utils import timezone
        return Product.objects.filter(
            status='active',
            is_boosted=True,
            boost_expires_at__gt=timezone.now()
        ).select_related('category', 'location', 'seller').prefetch_related('images')[:20]


class SimilarProductsView(generics.ListAPIView):
    """Get similar products based on category and location"""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        
        # Get similar products from same category or location
        similar_products = Product.objects.filter(
            Q(category=product.category) | Q(location=product.location),
            status='active'
        ).exclude(id=product.id).select_related(
            'category', 'location', 'seller'
        ).prefetch_related('images')[:10]
        
        return similar_products


class ProductStatsView(APIView):
    """Get product statistics"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, product_slug):
        product = get_object_or_404(
            Product, 
            slug=product_slug, 
            seller=request.user
        )
        
        # Get view statistics
        total_views = product.views_count
        unique_users = ProductView.objects.filter(
            product=product, 
            user__isnull=False
        ).values('user').distinct().count()
        
        # Get views over time (last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        recent_views = ProductView.objects.filter(
            product=product,
            viewed_at__gte=seven_days_ago
        ).extra(
            select={'date': 'DATE(viewed_at)'}
        ).values('date').annotate(count=Count('id')).order_by('date')
        
        return Response({
            'total_views': total_views,
            'unique_users': unique_users,
            'favorites_count': product.favorites_count,
            'shares_count': product.shares_count,
            'recent_views': list(recent_views)
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_as_sold(request, product_slug):
    """Mark product as sold"""
    product = get_object_or_404(Product, slug=product_slug, seller=request.user)
    
    if product.status == 'sold':
        return Response({
            'error': 'Product is already marked as sold.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    product.status = 'sold'
    product.save(update_fields=['status'])
    
    return Response({
        'message': 'Product marked as sold successfully.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reactivate_product(request, product_slug):
    """Reactivate a sold or expired product"""
    product = get_object_or_404(Product, slug=product_slug, seller=request.user)
    
    if product.status == 'active':
        return Response({
            'error': 'Product is already active.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    product.status = 'active'
    product.save(update_fields=['status'])
    
    return Response({
        'message': 'Product reactivated successfully.'
    }, status=status.HTTP_200_OK)