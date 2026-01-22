"""
URL configuration for ZuntoProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import health_check
# from analytics.admin import admin_site
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('admin/', admin.site.urls),

    path('health/', health_check, name='health_check'),

    # path('api/accounts/', include('accounts.urls')),

    path('', include('accounts.urls')),

    # path('api/admin/', include('accounts.admin_urls')),
    # path('api/admin/', include('market.admin_urls')),
    # path('api/admin/', include('orders.admin_urls')),

    path('api/market/', include('market.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/payments/', include('orders.payment_urls')),
    path('api/notifications/', include('notifications.urls')),
    # path('api/analytics/', include('analytics.urls')),
    path('assistant/', include('assistant.urls')),
    path('chat/', include ('chat.urls')),
    path('health/', health_check),

]

if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
