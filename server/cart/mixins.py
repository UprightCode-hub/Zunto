# cart/mixins.py
class CartMixin:
    """Mixin for cart-related operations"""
    
    def get_or_create_cart(self, request):
        """Get or create cart for user or guest"""
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # If user just logged in, merge guest cart
            session_id = request.session.get('cart_session_id')
            if session_id:
                self.merge_guest_cart(cart, session_id)
                request.session.pop('cart_session_id', None)
            
            return cart
        else:
            session_id = request.session.get('cart_session_id')
            
            if not session_id:
                import secrets
                session_id = secrets.token_urlsafe(32)
                request.session['cart_session_id'] = session_id
            
            cart, created = Cart.objects.get_or_create(
                session_id=session_id,
                user=None
            )
            
            return cart
    
    def merge_guest_cart(self, user_cart, session_id):
        """Merge guest cart into user cart when user logs in"""
        try:
            guest_cart = Cart.objects.get(session_id=session_id, user=None)
            
            for guest_item in guest_cart.items.all():
                user_item = user_cart.items.filter(product=guest_item.product).first()
                
                if user_item:
                    user_item.quantity += guest_item.quantity
                    user_item.save()
                else:
                    guest_item.cart = user_cart
                    guest_item.save()
            
            guest_cart.delete()
        except Cart.DoesNotExist:
            pass