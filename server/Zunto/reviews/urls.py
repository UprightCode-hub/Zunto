# reviews/urls.py
from django.urls import path
from .views import (
    ProductReviewListCreateView,
    ProductReviewDetailView,
    MyProductReviewsView,
    SellerReviewListCreateView,
    SellerReviewDetailView,
    MySellerReviewsView,
    ReviewsReceivedView,
    ReviewResponseCreateView,
    ReviewHelpfulToggleView,
    ReviewImageUploadView,
    ReviewFlagCreateView,
    ProductReviewStatsView,
    SellerReviewStatsView,
    top_rated_products,
    top_rated_sellers,
)

app_name = 'reviews'

urlpatterns = [
    # Product Reviews
    path('products/<slug:product_slug>/reviews/', ProductReviewListCreateView.as_view(), name='product_review_list_create'),
    path('products/<slug:product_slug>/reviews/stats/', ProductReviewStatsView.as_view(), name='product_review_stats'),
    path('product-reviews/<uuid:pk>/', ProductReviewDetailView.as_view(), name='product_review_detail'),
    path('my-product-reviews/', MyProductReviewsView.as_view(), name='my_product_reviews'),
    
    # Seller Reviews
    path('sellers/<uuid:seller_id>/reviews/', SellerReviewListCreateView.as_view(), name='seller_review_list_create'),
    path('sellers/<uuid:seller_id>/reviews/stats/', SellerReviewStatsView.as_view(), name='seller_review_stats'),
    path('seller-reviews/<uuid:pk>/', SellerReviewDetailView.as_view(), name='seller_review_detail'),
    path('my-seller-reviews/', MySellerReviewsView.as_view(), name='my_seller_reviews'),
    path('reviews-received/', ReviewsReceivedView.as_view(), name='reviews_received'),
    
    # Review Responses
    path('reviews/<str:review_type>/<uuid:review_id>/response/', ReviewResponseCreateView.as_view(), name='review_response'),
    
    # Review Helpful Votes
    path('reviews/<str:review_type>/<uuid:review_id>/helpful/', ReviewHelpfulToggleView.as_view(), name='review_helpful_toggle'),
    
    # Review Images
    path('reviews/<str:review_type>/<uuid:review_id>/images/', ReviewImageUploadView.as_view(), name='review_image_upload'),
    
    # Review Flags
    path('reviews/flag/', ReviewFlagCreateView.as_view(), name='review_flag'),
    
    # Top Rated
    path('top-rated-products/', top_rated_products, name='top_rated_products'),
    path('top-rated-sellers/', top_rated_sellers, name='top_rated_sellers'),
]