#server/orders/services.py
from django.db import transaction
from .models import Order, OrderItem

@transaction.atomic
def create_order_from_cart(cart, payment_method='paystack'):
    if cart.is_empty:
        raise ValueError("Cart is empty")

                                  
    default_shipping = cart.user.shipping_addresses.filter(is_default=True).first()

    order = Order.objects.create(
        customer=cart.user,
        payment_method=payment_method,
        subtotal=cart.subtotal,
        total_amount=cart.subtotal,
        shipping_address_ref=default_shipping
    )

    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.title,
            product_image=item.product.image.url if hasattr(item.product, 'image') and item.product.image else '',
            quantity=item.quantity,
            unit_price=item.price_at_addition,
            total_price=item.total_price,
            seller=item.product.seller
        )

    order.update_totals()
    cart.clear()

    return order
