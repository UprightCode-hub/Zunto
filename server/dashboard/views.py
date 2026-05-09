from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import SellerProfile
from assistant.models import DisputeTicket, Report
from cart.analytics import get_abandonment_summary_with_scores
from core.authentication import CookieJWTAuthentication
from core.audit import audit_event
from core.permissions import IsAdminOrStaff
from market.models import Product, ProductReport, ProductVideo
from orders.models import Order, OrderItem, Refund
from reviews.models import ReviewFlag


User = get_user_model()
DASHBOARD_AUTHENTICATION_CLASSES = [CookieJWTAuthentication, SessionAuthentication]


def _as_float(value):
    return float(value or 0)


def _full_name(user):
    if not user:
        return ''
    return user.get_full_name() or user.email


def _status_counts(queryset):
    return {
        item['status']: item['count']
        for item in queryset.values('status').annotate(count=Count('id')).order_by('status')
    }


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return bool(value)


def _serialize_user(user):
    try:
        seller_profile = user.seller_profile
    except SellerProfile.DoesNotExist:
        seller_profile = None
    return {
        'id': str(user.id),
        'name': _full_name(user),
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'is_suspended': user.is_suspended,
        'suspension_reason': user.suspension_reason,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_seller': user.is_seller,
        'is_verified_seller': user.is_verified_seller,
        'seller_profile_status': getattr(seller_profile, 'status', None),
        'seller_commerce_mode': getattr(seller_profile, 'seller_commerce_mode', getattr(user, 'seller_commerce_mode', 'direct')),
        'is_verified': user.is_verified,
        'is_phone_verified': user.is_phone_verified,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }


def _serialize_product(product):
    return {
        'id': str(product.id),
        'name': product.title,
        'title': product.title,
        'slug': product.slug,
        'seller': _full_name(product.seller),
        'seller_email': product.seller.email if product.seller else '',
        'price': str(product.price),
        'status': product.status,
        'category': product.category.name if product.category else '',
        'product_family': product.product_family.name if product.product_family else '',
        'is_featured': product.is_featured,
        'is_boosted': product.is_boosted,
        'is_verified': product.is_verified,
        'is_verified_product': product.is_verified_product,
        'attributes_verified': product.attributes_verified,
        'created_at': product.created_at.isoformat() if product.created_at else None,
    }


def _serialize_seller_profile(profile):
    user = profile.user
    return {
        'id': str(profile.id),
        'user_id': str(user.id),
        'name': _full_name(user),
        'email': user.email,
        'status': profile.status,
        'is_verified_seller': profile.is_verified_seller,
        'seller_commerce_mode': profile.seller_commerce_mode,
        'active_location': str(profile.active_location) if profile.active_location else '',
        'rating': profile.rating,
        'total_reviews': profile.total_reviews,
        'created_at': profile.created_at.isoformat() if profile.created_at else None,
        'updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
    }


def _paginate(request, queryset, serializer):
    paginator = PageNumberPagination()
    paginator.page_size = 25
    paginator.page_size_query_param = 'page_size'
    paginator.max_page_size = 100
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([serializer(item) for item in page])


class AdminDashboardAPIView(APIView):
    authentication_classes = DASHBOARD_AUTHENTICATION_CLASSES
    permission_classes = [IsAdminOrStaff]


class DashboardAPI(AdminDashboardAPIView):
    """API for main dashboard overview."""

    def get(self, request, *args, **kwargs):
        time_range = request.GET.get('range', 'week')
        today = timezone.now()

        if time_range == 'day':
            start_date = today - timedelta(days=1)
        elif time_range == 'week':
            start_date = today - timedelta(days=7)
        elif time_range == 'month':
            start_date = today - timedelta(days=30)
        else:
            start_date = today - timedelta(days=365)

        abandonment_data = get_abandonment_summary_with_scores()
        scoring_data = abandonment_data.get('scoring', {})
        score_averages = scoring_data.get('averages', {})

        order_queryset = Order.objects.all()
        paid_orders = order_queryset.filter(Q(payment_status='paid') | Q(status__in=['paid', 'processing', 'shipped', 'delivered']))
        total_orders = order_queryset.count()
        paid_order_count = paid_orders.count()
        total_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or 0

        data = {
            'total_users': User.objects.count(),
            'total_products': Product.objects.count(),
            'total_orders': total_orders,
            'paid_orders': paid_order_count,
            'pending_orders': order_queryset.filter(status='pending').count(),
            'total_revenue': _as_float(total_revenue),
            'conversion_rate': round((paid_order_count / total_orders) * 100, 2) if total_orders else 0,
            'total_abandoned_carts': abandonment_data['total_abandoned'],
            'total_recovered_carts': abandonment_data['total_recovered'],
            'abandonment_rate': abandonment_data['abandonment_rate'],
            'recovery_rate': abandonment_data['recovery_rate'],
            'avg_abandoned_value': abandonment_data['avg_abandoned_value'],
            'avg_composite_score': score_averages.get('composite', 0),
            'sales': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'data': [4200, 3800, 5200, 4600, 6800, 7200, 5900],
            },
            'categories': {
                'labels': ['Electronics', 'Clothing', 'Home & Garden', 'Sports'],
                'data': [35, 28, 20, 17],
            },
            'orders': {
                'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                'data': [24, 21, 32, 28, 42, 48, 38],
            },
            'top_products': [
                {
                    'name': item['product_name'],
                    'sales': int(item['sales'] or 0),
                    'revenue': _as_float(item['revenue']),
                }
                for item in OrderItem.objects.values('product_name')
                .annotate(sales=Sum('quantity'), revenue=Sum('total_price'))
                .order_by('-sales')[:5]
            ],
            'current_range': time_range,
            'range_start': start_date.isoformat(),
            'range_end': today.isoformat(),
        }

        audit_event(request, action='dashboard.overview.viewed', extra={'range': time_range})
        audit_event(request, action='dashboard.admin.overview.viewed', extra={'range': time_range})
        return Response(data)


class AnalyticsDashboardAPI(AdminDashboardAPIView):
    """API for analytics dashboard."""

    def get(self, request, *args, **kwargs):
        abandonment_data = get_abandonment_summary_with_scores()
        scoring_data = abandonment_data.get('scoring', {})
        order_queryset = Order.objects.all()
        paid_orders = order_queryset.filter(Q(payment_status='paid') | Q(status__in=['paid', 'processing', 'shipped', 'delivered']))
        total_orders = order_queryset.count()
        paid_order_count = paid_orders.count()
        total_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or 0

        data = {
            'total_users': User.objects.count(),
            'total_products': Product.objects.count(),
            'total_orders': total_orders,
            'paid_orders': paid_order_count,
            'pending_orders': order_queryset.filter(status='pending').count(),
            'total_revenue': _as_float(total_revenue),
            'conversion_rate': round((paid_order_count / total_orders) * 100, 2) if total_orders else 0,
            'orders_by_status': _status_counts(order_queryset),
            'products_by_status': _status_counts(Product.objects.all()),
            'users_by_role': {
                item['role']: item['count']
                for item in User.objects.values('role').annotate(count=Count('id')).order_by('role')
            },
            'score_distribution': scoring_data.get('distribution', {}),
            'value_by_tier': abandonment_data.get('value_by_tier', {}),
            'avg_composite_score': scoring_data.get('averages', {}).get('composite', 0),
            'total_abandoned_carts': abandonment_data['total_abandoned'],
            'total_recovered_carts': abandonment_data['total_recovered'],
            'abandonment_rate': abandonment_data['abandonment_rate'],
            'recovery_rate': abandonment_data['recovery_rate'],
            'avg_abandoned_value': abandonment_data['avg_abandoned_value'],
        }

        audit_event(request, action='dashboard.analytics.viewed')
        audit_event(request, action='dashboard.admin.analytics.viewed')
        # Backward compatibility for legacy analytics audit consumers/tests.
        audit_event(request, action='dashboard.analytics_legacy.viewed')
        audit_event(request, action='dashboard.admin.analytics_legacy.viewed')
        return Response(data)


@api_view(['GET'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def sales_report_api(request):
    """API endpoint for sales report."""
    order_queryset = Order.objects.all()
    paid_orders = order_queryset.filter(Q(payment_status='paid') | Q(status__in=['paid', 'processing', 'shipped', 'delivered']))
    total_orders = order_queryset.count()
    paid_order_count = paid_orders.count()
    total_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or 0

    audit_event(request, action='dashboard.sales.viewed')
    audit_event(request, action='dashboard.admin.sales.viewed')
    return Response({
        'page_title': 'Sales Report',
        'total_orders': total_orders,
        'paid_orders': paid_order_count,
        'pending_orders': order_queryset.filter(status='pending').count(),
        'cancelled_orders': order_queryset.filter(status='cancelled').count(),
        'refunded_orders': order_queryset.filter(status='refunded').count(),
        'total_revenue': _as_float(total_revenue),
        'conversion_rate': round((paid_order_count / total_orders) * 100, 2) if total_orders else 0,
        'orders_by_status': _status_counts(order_queryset),
    })


@api_view(['GET'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def products_list_api(request):
    """API endpoint for products list."""
    queryset = Product.objects.select_related('seller', 'category', 'product_family').order_by('-created_at')

    status_filter = (request.GET.get('status') or '').strip().lower()
    valid_statuses = {choice[0] for choice in Product.STATUS_CHOICES}
    if status_filter in valid_statuses:
        queryset = queryset.filter(status=status_filter)

    audit_event(request, action='dashboard.products.viewed')
    audit_event(request, action='dashboard.admin.products.viewed')
    return _paginate(request, queryset, _serialize_product)


@api_view(['GET'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def orders_list_api(request):
    """API endpoint for orders list."""
    queryset = Order.objects.select_related('customer').order_by('-created_at')

    audit_event(request, action='dashboard.orders.viewed')
    audit_event(request, action='dashboard.admin.orders.viewed')
    return _paginate(request, queryset, lambda order: {
        'id': str(order.id),
        'order_number': order.order_number,
        'customer': _full_name(order.customer),
        'customer_email': order.customer.email if order.customer else '',
        'status': order.status,
        'payment_status': order.payment_status,
        'payment_method': order.payment_method,
        'total_amount': str(order.total_amount),
        'created_at': order.created_at.isoformat() if order.created_at else None,
    })


@api_view(['GET'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def customers_list_api(request):
    """API endpoint for customers list."""
    queryset = User.objects.order_by('-created_at')

    role_filter = (request.GET.get('role') or '').strip()
    if role_filter in {choice[0] for choice in User.ROLE_CHOICES}:
        queryset = queryset.filter(role=role_filter)

    status_filter = (request.GET.get('status') or '').strip().lower()
    if status_filter == 'suspended':
        queryset = queryset.filter(is_suspended=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)
    elif status_filter == 'unverified':
        queryset = queryset.filter(is_verified=False)

    audit_event(request, action='dashboard.customers.viewed')
    audit_event(request, action='dashboard.admin.customers.viewed')
    return _paginate(request, queryset, _serialize_user)


@api_view(['PATCH'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def user_admin_update_api(request, user_id):
    """Admin user controls: verify, suspend/activate, and role changes."""
    user = get_object_or_404(User, id=user_id)
    action = str(request.data.get('action', '') or '').strip().lower()
    requested_fields = set(request.data.keys())
    self_lockout_fields = {'is_active', 'is_suspended', 'role', 'is_staff', 'is_superuser'}

    if user.id == request.user.id and (action == 'suspend' or self_lockout_fields & requested_fields):
        return Response(
            {'error': 'Admins cannot change their own access controls from this panel.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    update_fields = set()

    if action == 'verify_email':
        user.is_verified = True
        update_fields.add('is_verified')
    elif action == 'verify_phone':
        user.is_phone_verified = True
        update_fields.add('is_phone_verified')
    elif action == 'suspend':
        user.is_suspended = True
        user.is_active = False
        user.suspension_reason = str(request.data.get('suspension_reason') or 'Suspended by admin').strip()
        update_fields.update({'is_suspended', 'is_active', 'suspension_reason'})
    elif action == 'activate':
        user.is_active = True
        user.is_suspended = False
        user.suspension_reason = ''
        update_fields.update({'is_active', 'is_suspended', 'suspension_reason'})
    elif action:
        return Response({'error': 'Unsupported user action.'}, status=status.HTTP_400_BAD_REQUEST)

    for field_name in ['is_active', 'is_suspended', 'is_verified', 'is_phone_verified', 'is_staff', 'is_superuser']:
        if field_name in request.data:
            setattr(user, field_name, _parse_bool(request.data.get(field_name)))
            update_fields.add(field_name)

    if 'suspension_reason' in request.data:
        user.suspension_reason = str(request.data.get('suspension_reason') or '').strip()
        update_fields.add('suspension_reason')

    if 'role' in request.data:
        role = str(request.data.get('role') or '').strip()
        valid_roles = {choice[0] for choice in User.ROLE_CHOICES}
        if role not in valid_roles:
            return Response({'error': 'Invalid role.'}, status=status.HTTP_400_BAD_REQUEST)
        user.role = role
        user.is_seller = role == 'seller'
        update_fields.update({'role', 'is_seller'})

    if 'is_verified_seller' in request.data:
        user.is_verified_seller = _parse_bool(request.data.get('is_verified_seller'))
        update_fields.add('is_verified_seller')

    if not update_fields:
        return Response({'error': 'No supported user update was provided.'}, status=status.HTTP_400_BAD_REQUEST)

    update_fields.add('updated_at')
    user.save(update_fields=list(update_fields))

    audit_event(
        request,
        action='dashboard.admin.user.updated',
        extra={'user_id': str(user.id), 'action': action or None, 'fields': sorted(update_fields)},
    )
    return Response(_serialize_user(user), status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def seller_applications_api(request):
    """Admin queue for seller profile approval."""
    queryset = SellerProfile.objects.select_related('user', 'active_location').order_by('-created_at')
    status_filter = (request.GET.get('status') or '').strip().lower()
    if status_filter in {choice[0] for choice in SellerProfile.STATUS_CHOICES}:
        queryset = queryset.filter(status=status_filter)

    audit_event(request, action='dashboard.admin.seller_applications.viewed', extra={'status_filter': status_filter or None})
    return _paginate(request, queryset, _serialize_seller_profile)


@api_view(['PATCH'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def seller_application_decision_api(request, profile_id):
    """Approve, reject, or return seller applications to pending."""
    profile = get_object_or_404(SellerProfile.objects.select_related('user'), id=profile_id)
    target_status = str(request.data.get('status') or '').strip().lower()
    valid_statuses = {choice[0] for choice in SellerProfile.STATUS_CHOICES}
    if target_status not in valid_statuses:
        return Response({'error': 'Invalid seller status.'}, status=status.HTTP_400_BAD_REQUEST)

    commerce_mode = str(request.data.get('seller_commerce_mode') or profile.seller_commerce_mode).strip().lower()
    valid_modes = {choice[0] for choice in SellerProfile.SELLER_COMMERCE_MODE_CHOICES}
    if commerce_mode not in valid_modes:
        return Response({'error': 'Invalid seller commerce mode.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        old_status = profile.status
        profile.status = target_status
        profile.seller_commerce_mode = commerce_mode
        if target_status == SellerProfile.STATUS_APPROVED:
            profile.is_verified_seller = _parse_bool(request.data.get('is_verified_seller'), default=True)
        elif target_status == SellerProfile.STATUS_REJECTED:
            profile.is_verified_seller = False
        elif 'is_verified_seller' in request.data:
            profile.is_verified_seller = _parse_bool(request.data.get('is_verified_seller'))
        profile.verified = profile.is_verified_seller
        profile.save(update_fields=['status', 'seller_commerce_mode', 'is_verified_seller', 'verified', 'updated_at'])

        user = profile.user
        user.role = 'seller'
        user.is_seller = True
        user.is_verified_seller = profile.is_verified_seller
        user.seller_commerce_mode = profile.seller_commerce_mode
        user.save(update_fields=['role', 'is_seller', 'is_verified_seller', 'seller_commerce_mode', 'updated_at'])

    audit_event(
        request,
        action='dashboard.admin.seller_application.updated',
        extra={
            'profile_id': str(profile.id),
            'user_id': str(profile.user_id),
            'old_status': old_status,
            'new_status': profile.status,
            'is_verified_seller': profile.is_verified_seller,
        },
    )
    return Response(_serialize_seller_profile(profile), status=status.HTTP_200_OK)


@api_view(['PATCH'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def product_admin_update_api(request, product_id):
    """Admin product controls matching the high-use Django admin actions."""
    product = get_object_or_404(Product.objects.select_related('seller', 'category', 'product_family'), id=product_id)
    update_fields = set()

    if 'status' in request.data:
        target_status = str(request.data.get('status') or '').strip().lower()
        valid_statuses = {choice[0] for choice in Product.STATUS_CHOICES}
        if target_status not in valid_statuses:
            return Response({'error': 'Invalid product status.'}, status=status.HTTP_400_BAD_REQUEST)
        product.status = target_status
        update_fields.add('status')

    for field_name in ['is_featured', 'is_boosted']:
        if field_name in request.data:
            setattr(product, field_name, _parse_bool(request.data.get(field_name)))
            update_fields.add(field_name)

    requested_verification_fields = {'is_verified', 'is_verified_product'} & set(request.data.keys())
    if requested_verification_fields:
        desired_verified = any(_parse_bool(request.data.get(field_name)) for field_name in requested_verification_fields)
        product.is_verified = desired_verified
        product.is_verified_product = desired_verified
        update_fields.update({'is_verified', 'is_verified_product'})

    corrections = request.data.get('attribute_corrections')
    if isinstance(corrections, dict) and corrections:
        current_attributes = product.attributes or {}
        current_attributes.update(corrections)
        product.attributes = current_attributes
        update_fields.add('attributes')

    if 'attributes_verified' in request.data:
        attributes_verified = _parse_bool(request.data.get('attributes_verified'))
        product.attributes_verified = attributes_verified
        product.attributes_verified_at = timezone.now() if attributes_verified else None
        product.attributes_verified_by = request.user if attributes_verified else None
        update_fields.update({'attributes_verified', 'attributes_verified_at', 'attributes_verified_by'})

    if not update_fields:
        return Response({'error': 'No supported product update was provided.'}, status=status.HTTP_400_BAD_REQUEST)

    update_fields.add('updated_at')
    product.save(update_fields=list(update_fields))

    audit_event(
        request,
        action='dashboard.admin.product.updated',
        extra={'product_id': str(product.id), 'product_slug': product.slug, 'fields': sorted(update_fields)},
    )
    return Response(_serialize_product(product), status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def analytics_api(request):
    """API endpoint for legacy analytics."""
    audit_event(request, action='dashboard.analytics_legacy.viewed')
    audit_event(request, action='dashboard.admin.analytics_legacy.viewed')
    return Response({'page_title': 'Analytics'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@authentication_classes(DASHBOARD_AUTHENTICATION_CLASSES)
@permission_classes([IsAdminOrStaff])
def company_admin_operations_api(request):
    """Company-admin operational queue summary (frontend ops center)."""
    payload = {
        'seller_applications': {
            'pending': SellerProfile.objects.filter(status=SellerProfile.STATUS_PENDING).count(),
            'approved': SellerProfile.objects.filter(status=SellerProfile.STATUS_APPROVED).count(),
            'rejected': SellerProfile.objects.filter(status=SellerProfile.STATUS_REJECTED).count(),
        },
        'product_reports': {
            'pending': ProductReport.objects.filter(status='pending').count(),
            'reviewing': ProductReport.objects.filter(status='reviewing').count(),
        },
        'review_flags': {
            'pending': ReviewFlag.objects.filter(status='pending').count(),
            'reviewing': ReviewFlag.objects.filter(status='reviewing').count(),
        },
        'refunds': {
            'pending': Refund.objects.filter(status='pending').count(),
            'processing': Refund.objects.filter(status='processing').count(),
        },
        'assistant_reports': {
            'pending': Report.objects.filter(status='pending').count(),
            'reviewing': Report.objects.filter(status='reviewing').count(),
        },
        'dispute_tickets': {
            'open': DisputeTicket.objects.filter(status=DisputeTicket.STATUS_OPEN).count(),
            'under_review': DisputeTicket.objects.filter(status=DisputeTicket.STATUS_UNDER_REVIEW).count(),
            'escalated': DisputeTicket.objects.filter(status=DisputeTicket.STATUS_ESCALATED).count(),
        },
        'product_videos': {
            'pending_scan': ProductVideo.objects.filter(security_scan_status=ProductVideo.SCAN_PENDING).count(),
            'quarantined': ProductVideo.objects.filter(security_scan_status=ProductVideo.SCAN_QUARANTINED).count(),
        },
    }

    audit_event(request, action='dashboard.company_ops.viewed', extra={'queues': payload})
    audit_event(request, action='dashboard.admin.company_ops.viewed', extra={'queues': payload})
    return Response(payload)
