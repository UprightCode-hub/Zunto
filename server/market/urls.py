# market/urls.py
from django.urls import path
from .views import (
    CategoryListView,
    LocationListView,
    ProductListCreateView,
    ProductDetailView,
    MyProductsView,
    ProductImageUploadView,
    ProductVideoUploadView,
    FavoriteToggleView,
    FavoriteListView,
    ProductReportCreateView,
    FeaturedProductsView,
    BoostedProductsView,
    SimilarProductsView,
    ProductStatsView,
    mark_as_sold,
    reactivate_product,
)


urlpatterns = [
    # Categories & Locations
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('locations/', LocationListView.as_view(), name='location_list'),
    
    # Products
    path('products/', ProductListCreateView.as_view(), name='product_list_create'),
    # path('product_list/', product_list, name='product_list'),
    path('products/my-products/', MyProductsView.as_view(), name='my_products'),
    path('products/featured/', FeaturedProductsView.as_view(), name='featured_products'),
    path('products/boosted/', BoostedProductsView.as_view(), name='boosted_products'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('products/<slug:product_slug>/similar/', SimilarProductsView.as_view(), name='similar_products'),
    path('products/<slug:product_slug>/stats/', ProductStatsView.as_view(), name='product_stats'),
    path('products/<slug:product_slug>/mark-sold/', mark_as_sold, name='mark_as_sold'),
    path('products/<slug:product_slug>/reactivate/', reactivate_product, name='reactivate_product'),
    
    # Media uploads
    path('products/<slug:product_slug>/images/', ProductImageUploadView.as_view(), name='product_image_upload'),
    path('products/<slug:product_slug>/images/<uuid:image_id>/', ProductImageUploadView.as_view(), name='product_image_delete'),
    path('products/<slug:product_slug>/videos/', ProductVideoUploadView.as_view(), name='product_video_upload'),
    
    # Favorites
    path('products/<slug:product_slug>/favorite/', FavoriteToggleView.as_view(), name='favorite_toggle'),
    path('favorites/', FavoriteListView.as_view(), name='favorite_list'),
    
    # Reports
    path('products/<slug:product_slug>/report/', ProductReportCreateView.as_view(), name='product_report'),
]
# path('products/', ProductListCreateView.as_view(), name='product_list_create'),

#  {% url 'deals' %}
#  {% url 'cart' %}'
#  {% url 'home' %}
