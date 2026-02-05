# cart/views.py (COMPLETE FILE)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from .models import Cart, CartItem, SavedForLater
from .forms import AddToCartForm, UpdateCartItemForm, cart_summary
from .utils import log_cart_event
from market.models import Product


def get_or_create_cart(request):
    """Get or create cart for user or guest"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
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
                request.session.pop('cart_session_id', None)
            except Cart.DoesNotExist:
                pass
        return cart
    else:
        session_id = request.session.get('cart_session_id')
        if not session_id:
            import secrets
            session_id = secrets.token_urlsafe(32)
            request.session['cart_session_id'] = session_id
        cart, created = Cart.objects.get_or_create(session_id=session_id, user=None)
        return cart


def cart_view(request):
    cart = get_or_create_cart(request)
    summary = cart_summary(cart)
    return render(request, "cart/cart.html", {"cart": cart, "summary": summary})


@require_POST
def add_to_cart(request):
    form = AddToCartForm(request.POST)
    if form.is_valid():
        product = form.cleaned_data['product']
        quantity = form.cleaned_data['quantity']
        cart = get_or_create_cart(request)

        if request.user.is_authenticated and product.seller == request.user:
            messages.error(request, "You cannot add your own product to cart.")
            return redirect("cart:cart")

        if not product.is_available:
            messages.error(request, "Product is not available.")
            return redirect("cart:cart")

        if product.quantity < quantity:
            messages.error(request, f"Only {product.quantity} items available in stock.")
            return redirect("cart:cart")

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity}
        )
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.quantity:
                messages.error(request, f"Cannot add {quantity} more. Only {product.quantity - cart_item.quantity} available.")
            else:
                cart_item.quantity = new_quantity
                cart_item.save()
                messages.success(request, "Cart item quantity updated.")
                log_cart_event('cart_item_updated', cart, request.user if request.user.is_authenticated else None, {
                    'product_id': str(product.id),
                    'quantity': new_quantity,
                    'price': float(product.price)
                })
        else:
            messages.success(request, "Product added to cart.")
            log_cart_event('cart_item_added', cart, request.user if request.user.is_authenticated else None, {
                'product_id': str(product.id),
                'quantity': quantity,
                'price': float(product.price)
            })

    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    return redirect("cart:cart")


@require_POST
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(
        CartItem, id=item_id, cart=get_or_create_cart(request)
    )
    form = UpdateCartItemForm(request.POST, instance=cart_item)
    if form.is_valid():
        form.save()
        messages.success(request, "Cart item updated.")
        log_cart_event('cart_item_updated', cart_item.cart, request.user if request.user.is_authenticated else None, {
            'product_id': str(cart_item.product.id),
            'quantity': cart_item.quantity,
            'price': float(cart_item.product.price)
        })
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    return redirect("cart:cart")


@require_POST
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(
        CartItem, id=item_id, cart=get_or_create_cart(request)
    )
    log_cart_event('cart_item_removed', cart_item.cart, request.user if request.user.is_authenticated else None, {
        'product_id': str(cart_item.product.id),
        'quantity': cart_item.quantity
    })
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect("cart:cart")


@require_POST
def clear_cart(request):
    cart = get_or_create_cart(request)
    cart.clear()
    messages.success(request, "Cart cleared successfully.")
    return redirect("cart:cart")


@login_required
@require_POST
def save_for_later(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    log_cart_event('cart_item_saved', cart_item.cart, request.user, {
        'product_id': str(cart_item.product.id),
        'quantity': cart_item.quantity
    })
    SavedForLater.objects.get_or_create(user=request.user, product=cart_item.product)
    cart_item.delete()
    messages.success(request, "Item saved for later.")
    return redirect("cart:cart")


@login_required
@require_POST
def move_to_cart(request, saved_id):
    saved_item = get_object_or_404(SavedForLater, id=saved_id, user=request.user)
    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=saved_item.product, defaults={"quantity": 1})
    if not created and cart_item.quantity < saved_item.product.quantity:
        cart_item.quantity += 1
        cart_item.save()
    saved_item.delete()
    messages.success(request, "Item moved to cart.")
    return redirect("cart:cart")


@login_required
def saved_for_later_list(request):
    saved_items = SavedForLater.objects.filter(user=request.user).select_related('product')
    return render(request, "cart/saved_for_later.html", {"saved_items": saved_items})


def cart_summary_view(request):
    cart = get_or_create_cart(request)
    if cart.is_empty:
        messages.info(request, "Your cart is empty.")
        return redirect("cart:cart")
    summary = cart_summary(cart)
    return render(request, "cart/cart_summary.html", {"cart": cart, "summary": summary})


def cart_count(request):
    cart = get_or_create_cart(request)
    count = cart.total_items if cart else 0
    return render(request, "cart/cart_count.html", {"count": count})