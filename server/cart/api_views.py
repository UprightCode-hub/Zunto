#server/cart/api_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from market.models import Product
from .models import Cart, CartItem
from .serializers import (
    CartSerializer, 
    CartItemSerializer,
    UserScoreSerializer,
    ScoreAnalyticsSummarySerializer,
    ValueByTierSerializer
)
from .analytics import (
    get_score_analytics_summary,
    get_value_by_tier,
    get_top_users_by_score,
    get_recovery_targets,
    get_abandonment_summary_with_scores
)
from .utils import log_cart_event
import uuid


def get_or_create_cart(request):
    """Get or create cart for authenticated or guest user"""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        session_id = request.session.get('cart_session_id')
        if session_id:
            try:
                guest_cart = Cart.objects.get(session_id=session_id, user=None)
                for guest_item in guest_cart.items.all():
                    user_item = cart.items.filter(product=guest_item.product).first()
                    if user_item:
                        user_item.quantity += guest_item.quantity
                        user_item.save()
                    else:
                        guest_item.cart = cart
                        guest_item.save()
                guest_cart.delete()
                del request.session['cart_session_id']
            except Cart.DoesNotExist:
                pass
    else:
        session_id = request.session.get('cart_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session['cart_session_id'] = session_id
        cart, _ = Cart.objects.get_or_create(session_id=session_id, user=None)
    return cart


@api_view(['GET'])
@permission_classes([AllowAny])
def get_cart(request):
    """Get current user's cart"""
    cart = get_or_create_cart(request)
    serializer = CartSerializer(cart)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_to_cart(request):
    """Add item to cart"""
    cart = get_or_create_cart(request)

    product_id = request.data.get('product_id') or request.data.get('product')
    quantity = request.data.get('quantity', 1)

    if not product_id:
        return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        product = Product.objects.get(id=product_id)
    except (Product.DoesNotExist, ValueError):
        product = get_object_or_404(Product, slug=product_id)

    if not product.is_available:
        return Response({'error': 'Product is not available'}, status=status.HTTP_400_BAD_REQUEST)

    if product.quantity < int(quantity):
        return Response({'error': f'Only {product.quantity} items available'}, status=status.HTTP_400_BAD_REQUEST)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': int(quantity), 'price_at_addition': product.price}
    )

    if not created:
        new_quantity = cart_item.quantity + int(quantity)
        if new_quantity > product.quantity:
            return Response({'error': f'Only {product.quantity} items available'}, status=status.HTTP_400_BAD_REQUEST)
        cart_item.quantity = new_quantity
        cart_item.save()
        log_cart_event('cart_item_updated', cart, request.user if request.user.is_authenticated else None, {
            'product_id': str(product.id),
            'quantity': new_quantity,
            'price': float(product.price)
        })
    else:
        log_cart_event('cart_item_added', cart, request.user if request.user.is_authenticated else None, {
            'product_id': str(product.id),
            'quantity': int(quantity),
            'price': float(product.price)
        })

    serializer = CartSerializer(cart)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([AllowAny])
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    quantity = request.data.get('quantity')

    if quantity is None:
        return Response({'error': 'Quantity is required'}, status=status.HTTP_400_BAD_REQUEST)

    qty = int(quantity)
    if qty < 1:
        log_cart_event('cart_item_removed', cart, request.user if request.user.is_authenticated else None, {
            'product_id': str(item.product.id),
            'quantity': item.quantity
        })
        item.delete()
    else:
        if qty > item.product.quantity:
            return Response({'error': f'Only {item.product.quantity} items available'}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = qty
        item.save()
        log_cart_event('cart_item_updated', cart, request.user if request.user.is_authenticated else None, {
            'product_id': str(item.product.id),
            'quantity': qty,
            'price': float(item.product.price)
        })

    return Response(CartSerializer(cart).data)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart = get_or_create_cart(request)
    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
        log_cart_event('cart_item_removed', cart, request.user if request.user.is_authenticated else None, {
            'product_id': str(item.product.id),
            'quantity': item.quantity
        })
        item.delete()
    except CartItem.DoesNotExist:
        pass

    return Response(CartSerializer(cart).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def clear_cart(request):
    """Clear all items from cart"""
    cart = get_or_create_cart(request)
    cart.clear()
    return Response(CartSerializer(cart).data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def score_analytics_summary(request):
    """Get comprehensive scoring analytics (admin only)"""
    summary = get_score_analytics_summary()
    serializer = ScoreAnalyticsSummarySerializer(summary)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def value_by_tier(request):
    """Get abandoned cart value by user tier (admin only)"""
    data = get_value_by_tier()
    serializer = ValueByTierSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def top_users(request):
    """Get top users by score (admin only)"""
    limit = int(request.query_params.get('limit', 10))
    users = get_top_users_by_score(limit=limit)
    serializer = UserScoreSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def recovery_targets(request):
    """Get high-value users for recovery campaigns (admin only)"""
    min_score = int(request.query_params.get('min_score', 50))
    limit = int(request.query_params.get('limit', 50))
    targets = get_recovery_targets(min_score=min_score, limit=limit)
    serializer = UserScoreSerializer(targets, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def enhanced_abandonment_summary(request):
    """Get abandonment summary with scoring data (admin only)"""
    summary = get_abandonment_summary_with_scores()
    return Response(summary)
