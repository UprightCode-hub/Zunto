from django.urls import path
from . import api_views as views

app_name = 'cart'

urlpatterns = [
    # Cart operations
    path('', views.get_cart, name='cart'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('update/<uuid:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove/<uuid:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),

    # Save for later (Commented out until API implementation is ready)
    # path('items/<uuid:item_id>/save-later/', views.save_for_later, name='save_for_later'),
    # path('saved/', views.saved_for_later_list, name='saved_list'),
    # path('saved/<uuid:saved_id>/move-to-cart/', views.move_to_cart, name='move_to_cart'),
]
