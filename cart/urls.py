# cart/urls.py
from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    # Cart operations
    path('', views.cart_view, name='cart'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('items/<uuid:item_id>/update/', views.update_cart_item, name='update_cart_item'),
    path('items/<uuid:item_id>/remove/', views.remove_cart_item, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),

    # Save for later
    path('items/<uuid:item_id>/save-later/', views.save_for_later, name='save_for_later'),
    path('saved/', views.saved_for_later_list, name='saved_list'),
    path('saved/<uuid:saved_id>/move-to-cart/', views.move_to_cart, name='move_to_cart'),
]
