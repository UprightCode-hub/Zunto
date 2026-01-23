from django import forms
from .models import CartItem, SavedForLater, Cart
from market.models import Product


# ---------- Add to Cart ----------
class AddToCartForm(forms.Form):
    product_id = forms.UUIDField()
    quantity = forms.IntegerField(min_value=1, max_value=100, initial=1)

    def clean_product_id(self):
        product_id = self.cleaned_data['product_id']
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise forms.ValidationError("Product does not exist.")
        self.cleaned_data['product'] = product
        return product_id

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        if qty > 100:
            raise forms.ValidationError("Maximum quantity is 100.")
        return qty


# ---------- Update Cart Item ----------
class UpdateCartItemForm(forms.ModelForm):
    class Meta:
        model = CartItem
        fields = ['quantity']

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        if qty > 100:
            raise forms.ValidationError("Maximum quantity is 100.")
        return qty


# ---------- Saved for Later ----------
class SavedForLaterForm(forms.ModelForm):
    class Meta:
        model = SavedForLater
        fields = []  # automatically handled


# ---------- Cart Summary Helper ----------
def cart_summary(cart):
    """
    Returns a dictionary with cart totals and stock info,
    equivalent to CartSummarySerializer.
    """
    total_items = sum(item.quantity for item in cart.items.all())
    subtotal = sum(item.quantity * item.product.price for item in cart.items.all())
    
    # Example tax/shipping calculations
    estimated_tax = subtotal * 0.075  # 7.5%
    estimated_shipping = 500  # flat shipping fee
    
    total = subtotal + estimated_tax + estimated_shipping

    unavailable_items = [item for item in cart.items.all() if not item.is_available]
    out_of_stock_items = [item for item in cart.items.all() if not item.has_sufficient_stock]

    return {
        'total_items': total_items,
        'subtotal': subtotal,
        'estimated_tax': estimated_tax,
        'estimated_shipping': estimated_shipping,
        'total': total,
        'unavailable_items': unavailable_items,
        'out_of_stock_items': out_of_stock_items,
        'is_empty': cart.items.count() == 0
    }


# ---------- Cart Item Product Helper ----------
def cart_item_product_data(cart_item, request=None):
    """
    Returns a dictionary with product info for template rendering,
    equivalent to CartItemProductSerializer.
    """
    product = cart_item.product
    images = product.images.all()
    primary_image = images.filter(is_primary=True).first() or images.first()
    image_url = None
    if primary_image:
        if request:
            image_url = request.build_absolute_uri(primary_image.image.url)
        else:
            image_url = primary_image.image.url

    return {
        'id': product.id,
        'title': product.title,
        'slug': product.slug,
        'price': product.price,
        'condition': product.condition,
        'brand': product.brand,
        'status': product.status,
        'quantity': cart_item.quantity,
        'seller_name': product.seller.get_full_name(),
        'seller_id': product.seller.id,
        'primary_image': image_url,
    }
