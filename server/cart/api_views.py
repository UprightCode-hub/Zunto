from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from market.models import Product
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
import uuid

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        # Check for guest cart in session to merge
        session_id = request.session.get('cart_session_id')
        if session_id:
            try:
                guest_cart = Cart.objects.get(session_id=session_id, user=None)
                for guest_item in guest_cart.items.all():
                    # Check if item exists in user cart
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
    cart = get_or_create_cart(request)
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def add_to_cart(request):
    cart = get_or_create_cart(request)
    
    # Handle different data formats (React vs form-data)
    product_id = request.data.get('product_id') or request.data.get('product')
    quantity = request.data.get('quantity', 1)

    if not product_id:
        return Response({'error': 'Product ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        product = Product.objects.get(id=product_id)
    except (Product.DoesNotExist, ValueError):
         # Try looking up by slug if UUID fails
        product = get_object_or_404(Product, slug=product_id)

    # Check availability
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
    
    serializer = CartSerializer(cart)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
@permission_classes([AllowAny])
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    quantity = request.data.get('quantity')

    if quantity is None:
        return Response({'error': 'Quantity is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    qty = int(quantity)
    if qty < 1:
        item.delete()
    else:
        if qty > item.product.quantity:
             return Response({'error': f'Only {item.product.quantity} items available'}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = qty
        item.save()
    
    return Response(CartSerializer(cart).data)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def remove_from_cart(request, item_id):
    cart = get_or_create_cart(request)
    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
        item.delete()
    except CartItem.DoesNotExist:
        pass # Already deleted
        
    return Response(CartSerializer(cart).data)

@api_view(['POST'])
@permission_classes([AllowAny])
def clear_cart(request):
    cart = get_or_create_cart(request)
    cart.clear()
    return Response(CartSerializer(cart).data)
