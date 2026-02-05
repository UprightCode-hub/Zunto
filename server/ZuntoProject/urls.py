from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.generic import RedirectView
from core.views import health_check, assistant_view, marketplace_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
 
    # Root redirect to marketplace
    path('', RedirectView.as_view(url='/marketplace/products/', permanent=False)),
    
    # Frontend: Assistant AI
    path('assistant/', assistant_view, {'page': 'index'}, name='assistant_home'),
    path('assistant/<str:page>/', assistant_view, name='assistant_page'),
    
    # Frontend: Marketplace
    path('marketplace/', marketplace_view, {'section': 'products', 'page': 'index'}, name='marketplace_home'),
    path('marketplace/auth/<str:page>/', marketplace_view, {'section': 'auth'}, name='marketplace_auth'),
    path('marketplace/account/<str:page>/', marketplace_view, {'section': 'account'}, name='marketplace_account'),
    path('marketplace/products/', marketplace_view, {'section': 'products', 'page': 'index'}, name='marketplace_products'),
    path('marketplace/products/<str:page>/', marketplace_view, {'section': 'products'}, name='marketplace_product_page'),
    path('marketplace/seller/<str:page>/', marketplace_view, {'section': 'seller'}, name='marketplace_seller'),
    path('marketplace/shopping/<str:page>/', marketplace_view, {'section': 'shopping'}, name='marketplace_shopping'),
    path('marketplace/chat/<str:page>/', marketplace_view, {'section': 'chat'}, name='marketplace_chat'),
    path('marketplace/reviews/<str:page>/', marketplace_view, {'section': 'reviews'}, name='marketplace_reviews'),
    
    # Dashboard (Executive & Analytics)
    path('dashboard/', include('dashboard.urls')),
    
    # API Routes
    path('', include('accounts.urls')),
    path('api/market/', include('market.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('orders.payment_urls')),
    path('api/notifications/', include('notifications.urls')),
    path('assistant/', include('assistant.urls')),
    path('chat/', include('chat.urls')),
]

if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)