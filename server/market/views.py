#server/market/views.py
import base64
import hashlib
import hmac
import json
import time
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Q, Count, Avg, F
from django.db.models.functions import Greatest
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render
from django.core.cache import cache


from .models import (
    Category, Location, Product, ProductImage, 
    ProductVideo, Favorite, ProductView, ProductReport, ProductShareEvent
)
from .serializers import (
    CategorySerializer, LocationSerializer, 
    ProductListSerializer, ProductDetailSerializer,
    ProductCreateUpdateSerializer, ProductImageSerializer,
    ProductVideoSerializer, FavoriteSerializer, ProductReportSerializer,
    ProductVideoModerationSerializer
)
from .permissions import IsSellerOrReadOnly
from .filters import ProductFilter
from core.permissions import IsAdminOrStaff, IsSellerOrAdmin
from core.audit import audit_event

MAX_PRODUCT_IMAGES = 5
MAX_PRODUCT_VIDEOS = 2
MAX_PRODUCT_VIDEO_SIZE_BYTES = 20 * 1024 * 1024


def _invalidate_product_stats_cache(product_id):
    cache.delete(f'product_stats:{product_id}')


def _build_direct_upload_key(product_id, filename):
    from pathlib import Path

    suffix = Path(filename or 'upload.bin').suffix.lower() or '.bin'
    token = hashlib.sha256(f"{product_id}:{time.time_ns()}".encode('utf-8')).hexdigest()[:24]
    return f"products/videos/{product_id}/{token}{suffix}"


def _sign_upload_callback_payload(payload):
    secret = str(getattr(settings, 'OBJECT_UPLOAD_HMAC_SECRET', '') or '').encode('utf-8')
    if not secret:
        return ''
    message = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _verify_upload_callback_payload(payload, signature):
    expected = _sign_upload_callback_payload(payload)
    if not expected or not signature:
        return False
    return hmac.compare_digest(expected, signature)

class CategoryListView(generics.ListAPIView):
    """List all active categories"""
    
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
                                          
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
    
    template_name = 'products.html'
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
                                     
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
        if not IsSellerOrAdmin().has_permission(self.request, self):
            raise permissions.PermissionDenied('Seller account required to create product listings.')
        product = serializer.save(seller=self.request.user)
        audit_event(self.request, action='market.product.created', extra={'product_id': str(product.id), 'product_slug': product.slug})


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
        
                    
        self.track_view(instance)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def track_view(self, product):
        """Track product view with short-window deduplication to reduce write amplification."""
        user = self.request.user if self.request.user.is_authenticated else None
        ip_address = self.get_client_ip()
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')

        if user and user == product.seller:
            return

        viewer_key = f"u:{user.id}" if user else f"ip:{ip_address}"
        dedupe_key = f"product_view:{product.id}:{viewer_key}"
        if not cache.add(dedupe_key, True, timeout=60 * 60):
            return

        ProductView.objects.create(
            product=product,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        Product.objects.filter(id=product.id).update(views_count=F('views_count') + 1)
        product.refresh_from_db(fields=['views_count'])
        _invalidate_product_stats_cache(product.id)
    
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
    
    template_name = 'product-detail.html'
    serializer_class = ProductListSerializer
    permission_classes = [IsSellerOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'price', 'views_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'location').prefetch_related('images')
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(seller=self.request.user)


class ProductImageUploadView(APIView):
    """Upload product images"""
    
    permission_classes = [IsSellerOrAdmin]
    
    def post(self, request, product_slug):
        product_qs = Product.objects.filter(slug=product_slug)
        if not request.user.is_staff:
            product_qs = product_qs.filter(seller=request.user)
        product = get_object_or_404(product_qs)
        
                                                           
        if product.images.count() >= MAX_PRODUCT_IMAGES:
            return Response({
                'error': f'Maximum {MAX_PRODUCT_IMAGES} images allowed per product.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ProductImageSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, product_slug, image_id):
        product_qs = Product.objects.filter(slug=product_slug)
        if not request.user.is_staff:
            product_qs = product_qs.filter(seller=request.user)
        product = get_object_or_404(product_qs)
        image = get_object_or_404(ProductImage, id=image_id, product=product)
        
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductVideoUploadView(APIView):
    """Upload product videos"""
    
    permission_classes = [IsSellerOrAdmin]
    
    def post(self, request, product_slug):
        product_qs = Product.objects.filter(slug=product_slug)
        if not request.user.is_staff:
            product_qs = product_qs.filter(seller=request.user)
        product = get_object_or_404(product_qs)
        
                                                          
        if product.videos.count() >= MAX_PRODUCT_VIDEOS:
            return Response({
                'error': f'Maximum {MAX_PRODUCT_VIDEOS} videos allowed per product.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        video_file = request.FILES.get('video')
        if video_file and video_file.size > MAX_PRODUCT_VIDEO_SIZE_BYTES:
            return Response({
                'error': 'Video file must not exceed 20MB.'
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

        with transaction.atomic():
            favorite, created = Favorite.objects.get_or_create(
                user=user,
                product=product,
            )

            if not created:
                favorite.delete()
                Product.objects.filter(id=product.id).update(
                    favorites_count=Greatest(F('favorites_count') - 1, 0)
                )
                product.refresh_from_db(fields=['favorites_count'])
                _invalidate_product_stats_cache(product.id)
                return Response({
                    'message': 'Product removed from favorites.',
                    'is_favorited': False,
                    'favorites_count': product.favorites_count,
                }, status=status.HTTP_200_OK)

            Product.objects.filter(id=product.id).update(
                favorites_count=F('favorites_count') + 1
            )
            product.refresh_from_db(fields=['favorites_count'])
            _invalidate_product_stats_cache(product.id)
            return Response({
                'message': 'Product added to favorites.',
                'is_favorited': True,
                'favorites_count': product.favorites_count,
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
        report = serializer.save(reporter=self.request.user, product=product)
        audit_event(
            self.request,
            action='market.report.created',
            extra={
                'report_id': str(report.id),
                'product_id': str(product.id),
                'reason': report.reason,
            },
        )


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


class AdsProductsView(generics.ListAPIView):
    """List homepage advertisement products."""

    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from django.utils import timezone

        boosted_ids = list(
            Product.objects.filter(
                status='active',
                is_boosted=True,
                boost_expires_at__gt=timezone.now()
            ).values_list('id', flat=True)[:10]
        )

        featured_ids = list(
            Product.objects.filter(
                status='active',
                is_featured=True
            ).exclude(id__in=boosted_ids).values_list('id', flat=True)[:10]
        )

        ordered_ids = boosted_ids + featured_ids
        if not ordered_ids:
            return Product.objects.none()

        preserve_order = {str(pid): index for index, pid in enumerate(ordered_ids)}
        queryset = Product.objects.filter(id__in=ordered_ids).select_related(
            'category', 'location', 'seller'
        ).prefetch_related('images')

        return sorted(queryset, key=lambda item: preserve_order.get(str(item.id), 9999))


class SimilarProductsView(generics.ListAPIView):
    """Get similar products based on category and location"""
    
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        product_slug = self.kwargs.get('product_slug')
        product = get_object_or_404(Product, slug=product_slug)
        
                                                             
        similar_products = Product.objects.filter(
            Q(category=product.category) | Q(location=product.location),
            status='active'
        ).exclude(id=product.id).select_related(
            'category', 'location', 'seller'
        ).prefetch_related('images')[:10]
        
        return similar_products


class ProductStatsView(APIView):
    """Get product statistics"""
    
    permission_classes = [IsSellerOrAdmin]
    
    def get(self, request, product_slug):
        product_qs = Product.objects.filter(slug=product_slug)
        if not request.user.is_staff:
            product_qs = product_qs.filter(seller=request.user)
        product = get_object_or_404(product_qs)
        
                             
        cache_key = f'product_stats:{product.id}'
        cached_stats = cache.get(cache_key)
        if cached_stats is not None:
            return Response(cached_stats)

        total_views = product.views_count
        unique_users = ProductView.objects.filter(
            product=product,
            user__isnull=False,
        ).values('user_id').distinct().count()

        from django.utils import timezone
        from datetime import timedelta
        seven_days_ago = timezone.now() - timedelta(days=7)

        recent_views = list(
            ProductView.objects.filter(
                product=product,
                viewed_at__gte=seven_days_ago,
            )
            .annotate(date=TruncDate('viewed_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        payload = {
            'total_views': total_views,
            'unique_users': unique_users,
            'favorites_count': product.favorites_count,
            'shares_count': product.shares_count,
            'recent_views': recent_views,
        }
        cache.set(cache_key, payload, timeout=120)
        return Response(payload)


@api_view(['POST'])
@permission_classes([IsSellerOrAdmin])
def mark_as_sold(request, product_slug):
    """Mark product as sold"""
    product_qs = Product.objects.filter(slug=product_slug)
    if not request.user.is_staff:
        product_qs = product_qs.filter(seller=request.user)
    product = get_object_or_404(product_qs)
    
    if product.status == 'sold':
        return Response({
            'error': 'Product is already marked as sold.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    previous_status = product.status
    product.status = 'sold'
    product.save(update_fields=['status'])
    audit_event(request, action='market.product.mark_sold', extra={'product_id': str(product.id), 'product_slug': product.slug, 'old_status': previous_status, 'new_status': product.status})

    return Response({
        'message': 'Product marked as sold successfully.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsSellerOrAdmin])
def reactivate_product(request, product_slug):
    """Reactivate a sold or expired product"""
    product_qs = Product.objects.filter(slug=product_slug)
    if not request.user.is_staff:
        product_qs = product_qs.filter(seller=request.user)
    product = get_object_or_404(product_qs)
    
    if product.status == 'active':
        return Response({
            'error': 'Product is already active.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    previous_status = product.status
    product.status = 'active'
    product.save(update_fields=['status'])
    audit_event(request, action='market.product.reactivated', extra={'product_id': str(product.id), 'product_slug': product.slug, 'old_status': previous_status, 'new_status': product.status})

    return Response({
        'message': 'Product reactivated successfully.'
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def share_product(request, product_slug):
    product = get_object_or_404(Product, slug=product_slug)
    user = request.user

    is_seller_share = user.role == 'seller' and product.seller_id == user.id
    is_buyer_share = (
        user.role == 'buyer'
        and ProductView.objects.filter(product=product, user=user).exists()
    )

    if not is_seller_share and not is_buyer_share:
        return Response(
            {'error': 'You do not have permission to share this product.'},
            status=status.HTTP_403_FORBIDDEN
        )

    shared_via = str(request.data.get('shared_via', 'link')).strip()[:30] or 'link'
    share_event, created = ProductShareEvent.objects.get_or_create(
        product=product,
        user=user,
        defaults={'shared_via': shared_via},
    )

    if created:
        Product.objects.filter(id=product.id).update(shares_count=F('shares_count') + 1)
        product.refresh_from_db(fields=['shares_count'])
        _invalidate_product_stats_cache(product.id)

    return Response(
        {
            'message': 'Product shared successfully.' if created else 'Product already shared.',
            'product_slug': product.slug,
            'shares_count': product.shares_count,
            'already_shared': not created,
            'shared_via': share_event.shared_via,
        },
        status=status.HTTP_200_OK
    )


class ProductReportModerationView(generics.ListAPIView):
    """Admin moderation queue for product reports."""

    serializer_class = ProductReportSerializer
    permission_classes = [IsAdminOrStaff]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'resolved_at', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = ProductReport.objects.select_related('product', 'reporter')

        status_filter = (self.request.query_params.get('status') or '').strip().lower()
        if status_filter in {'pending', 'reviewing', 'resolved', 'dismissed'}:
            queryset = queryset.filter(status=status_filter)

        reason_filter = (self.request.query_params.get('reason') or '').strip().lower()
        valid_reasons = {choice[0] for choice in ProductReport.REASON_CHOICES}
        if reason_filter in valid_reasons:
            queryset = queryset.filter(reason=reason_filter)

        audit_event(
            self.request,
            action='market.report.moderation_queue_viewed',
            extra={
                'status_filter': status_filter or None,
                'reason_filter': reason_filter or None,
            },
        )

        return queryset


class ProductReportModerationDetailView(APIView):
    """Update moderation status for a single product report."""

    permission_classes = [IsAdminOrStaff]

    _ALLOWED_TRANSITIONS = {
        'pending': {'reviewing', 'resolved', 'dismissed'},
        'reviewing': {'resolved', 'dismissed'},
        'resolved': set(),
        'dismissed': set(),
    }

    def patch(self, request, report_id):
        target_status = str(request.data.get('status', '')).strip().lower()
        if target_status not in {'reviewing', 'resolved', 'dismissed'}:
            return Response(
                {'error': 'Invalid moderation status. Use reviewing, resolved, or dismissed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            report = get_object_or_404(
                ProductReport.objects.select_for_update().select_related('product', 'reporter'),
                id=report_id,
            )

            allowed_targets = self._ALLOWED_TRANSITIONS.get(report.status, set())
            if target_status not in allowed_targets:
                return Response(
                    {'error': f'Cannot transition report from {report.status} to {target_status}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            admin_notes = str(request.data.get('admin_notes', '') or '').strip()
            old_status = report.status
            report.status = target_status

            from django.utils import timezone

            if target_status in {'resolved', 'dismissed'}:
                report.resolved_at = timezone.now()
            else:
                report.resolved_at = None

            if admin_notes:
                report.admin_notes = admin_notes

            report.moderated_by = request.user
            report.save(update_fields=['status', 'resolved_at', 'admin_notes', 'moderated_by'])

        audit_event(
            request,
            action='market.report.moderated',
            extra={
                'report_id': str(report.id),
                'product_id': str(report.product_id),
                'old_status': old_status,
                'new_status': target_status,
                'report_reason': report.reason,
                'moderator_id': str(request.user.id),
            },
        )

        serializer = ProductReportSerializer(report, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductVideoModerationQueueView(generics.ListAPIView):
    """Admin moderation queue for product video malware-scan statuses."""

    serializer_class = ProductVideoModerationSerializer
    permission_classes = [IsAdminOrStaff]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['uploaded_at', 'scanned_at', 'security_scan_status']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        queryset = ProductVideo.objects.select_related('product', 'product__seller')

        status_filter = (self.request.query_params.get('status') or '').strip().lower()
        valid_statuses = {choice[0] for choice in ProductVideo.SECURITY_SCAN_STATUS_CHOICES}
        if status_filter in valid_statuses:
            queryset = queryset.filter(security_scan_status=status_filter)

        audit_event(
            self.request,
            action='market.video_scan.queue_viewed',
            extra={'status_filter': status_filter or None},
        )
        return queryset


class ProductVideoModerationDetailView(APIView):
    """Admin-only review actions for product video scan outcomes."""

    permission_classes = [IsAdminOrStaff]

    def patch(self, request, video_id):
        action = str(request.data.get('action', '')).strip().lower()
        if action not in {'mark_clean', 'mark_rejected'}:
            return Response(
                {'error': 'Invalid action. Use mark_clean or mark_rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_notes = str(request.data.get('reason', '') or '').strip()

        with transaction.atomic():
            video = get_object_or_404(
                ProductVideo.objects.select_for_update().select_related('product', 'product__seller'),
                id=video_id,
            )
            old_status = video.security_scan_status

            if action == 'mark_clean':
                video.security_scan_status = ProductVideo.SCAN_CLEAN
                video.security_quarantine_path = ''
                if admin_notes:
                    video.security_scan_reason = admin_notes
            else:
                video.security_scan_status = ProductVideo.SCAN_REJECTED
                if admin_notes:
                    video.security_scan_reason = admin_notes

            from django.utils import timezone
            video.scanned_at = timezone.now()
            video.save(update_fields=['security_scan_status', 'security_scan_reason', 'security_quarantine_path', 'scanned_at'])

        audit_event(
            request,
            action='market.video_scan.moderated',
            extra={
                'video_id': str(video.id),
                'product_id': str(video.product_id),
                'old_status': old_status,
                'new_status': video.security_scan_status,
                'moderator_id': str(request.user.id),
            },
        )

        serializer = ProductVideoModerationSerializer(video, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductVideoDirectUploadTicketView(APIView):
    """Issue signed direct-upload ticket for object-storage video upload."""

    permission_classes = [IsSellerOrAdmin]

    def post(self, request, product_slug):
        if not getattr(settings, 'USE_OBJECT_STORAGE', False):
            return Response({'error': 'Object storage direct upload is not enabled.'}, status=status.HTTP_400_BAD_REQUEST)

        product_qs = Product.objects.filter(slug=product_slug)
        if not request.user.is_staff:
            product_qs = product_qs.filter(seller=request.user)
        product = get_object_or_404(product_qs)

        filename = str(request.data.get('filename', '') or '').strip()
        if not filename:
            return Response({'error': 'filename is required.'}, status=status.HTTP_400_BAD_REQUEST)

        content_type = str(request.data.get('content_type', '') or '').strip().lower()
        if content_type not in {'video/mp4', 'video/webm', 'video/quicktime'}:
            return Response({'error': 'Unsupported video content_type.'}, status=status.HTTP_400_BAD_REQUEST)

        object_key = _build_direct_upload_key(product.id, filename)

        import boto3

        client = boto3.client(
            's3',
            endpoint_url=getattr(settings, 'OBJECT_STORAGE_ENDPOINT_URL', '') or None,
            region_name=getattr(settings, 'OBJECT_STORAGE_REGION', 'auto') or None,
            aws_access_key_id=getattr(settings, 'OBJECT_STORAGE_ACCESS_KEY_ID', ''),
            aws_secret_access_key=getattr(settings, 'OBJECT_STORAGE_SECRET_ACCESS_KEY', ''),
        )

        expires_in = int(getattr(settings, 'OBJECT_UPLOAD_SIGNED_UPLOAD_EXP_SECONDS', 900))
        post = client.generate_presigned_post(
            Bucket=getattr(settings, 'OBJECT_STORAGE_BUCKET_NAME', ''),
            Key=object_key,
            Fields={'Content-Type': content_type},
            Conditions=[
                {'Content-Type': content_type},
                ['content-length-range', 1, MAX_PRODUCT_VIDEO_SIZE_BYTES],
            ],
            ExpiresIn=expires_in,
        )

        exp = int(time.time()) + expires_in
        callback_payload = {
            'product_id': str(product.id),
            'product_slug': product.slug,
            'uploader_id': str(request.user.id),
            'key': object_key,
            'content_type': content_type,
            'exp': exp,
        }
        callback_token = _sign_upload_callback_payload(callback_payload)

        audit_event(request, action='market.video_upload.ticket_issued', extra={'product_id': str(product.id), 'object_key': object_key})

        return Response({
            'upload': post,
            'object_key': object_key,
            'callback': {
                'payload': callback_payload,
                'signature': callback_token,
            },
        }, status=status.HTTP_200_OK)


class ProductVideoDirectUploadCallbackView(APIView):
    """Verify signed direct-upload callback and persist pending ProductVideo record."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, product_slug):
        payload = request.data.get('payload') or {}
        signature = str(request.data.get('signature', '') or '')

        if not isinstance(payload, dict):
            return Response({'error': 'payload must be an object.'}, status=status.HTTP_400_BAD_REQUEST)

        required = {'product_id', 'product_slug', 'uploader_id', 'key', 'content_type', 'exp'}
        if not required.issubset(payload.keys()):
            return Response({'error': 'Incomplete callback payload.'}, status=status.HTTP_400_BAD_REQUEST)

        if payload.get('product_slug') != product_slug:
            return Response({'error': 'Payload slug mismatch.'}, status=status.HTTP_400_BAD_REQUEST)

        if str(payload.get('uploader_id')) != str(request.user.id):
            return Response({'error': 'Uploader mismatch.'}, status=status.HTTP_403_FORBIDDEN)

        if int(payload.get('exp') or 0) < int(time.time()):
            return Response({'error': 'Callback token expired.'}, status=status.HTTP_400_BAD_REQUEST)

        if not _verify_upload_callback_payload(payload, signature):
            return Response({'error': 'Invalid callback signature.'}, status=status.HTTP_403_FORBIDDEN)

        product_qs = Product.objects.filter(id=payload.get('product_id'), slug=product_slug)
        if not request.user.is_staff:
            product_qs = product_qs.filter(seller=request.user)
        product = get_object_or_404(product_qs)

        video = ProductVideo.objects.create(
            product=product,
            video=payload.get('key'),
            security_scan_status=ProductVideo.SCAN_PENDING,
            security_scan_reason='direct-upload-pending-scan',
        )

        from market.tasks import schedule_product_video_scan

        transaction.on_commit(lambda: schedule_product_video_scan(str(video.id)))

        audit_event(request, action='market.video_upload.callback_verified', extra={'product_id': str(product.id), 'video_id': str(video.id), 'object_key': payload.get('key')})

        serializer = ProductVideoSerializer(video, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
