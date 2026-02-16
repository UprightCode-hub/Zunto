#server/cart/urls.py
from django.urls import path
from . import api_views as views

app_name = 'cart'

urlpatterns = [
                     
    path('', views.get_cart, name='cart'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('update/<uuid:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove/<uuid:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    
                                      
    path('analytics/scores/summary/', views.score_analytics_summary, name='score_analytics_summary'),
    path('analytics/scores/value-by-tier/', views.value_by_tier, name='value_by_tier'),
    path('analytics/scores/top-users/', views.top_users, name='top_users'),
    path('analytics/scores/recovery-targets/', views.recovery_targets, name='recovery_targets'),
    path('analytics/abandonment/enhanced/', views.enhanced_abandonment_summary, name='enhanced_abandonment_summary'),
]
