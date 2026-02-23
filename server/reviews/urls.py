#server/reviews/urls.py
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
    ReviewFlagModerationQueueView,
    ReviewFlagModerationDetailView,
    ProductReviewStatsView,
    SellerReviewStatsView,
    top_rated_products,
    top_rated_sellers,
)

app_name = 'reviews'

urlpatterns = [
                     
    path('products/<slug:product_slug>/reviews/', ProductReviewListCreateView.as_view(), name='product_review_list_create'),
    path('products/<slug:product_slug>/reviews/stats/', ProductReviewStatsView.as_view(), name='product_review_stats'),
    path('product-reviews/<uuid:pk>/', ProductReviewDetailView.as_view(), name='product_review_detail'),
    path('my-product-reviews/', MyProductReviewsView.as_view(), name='my_product_reviews'),
    
                    
    path('sellers/<uuid:seller_id>/reviews/', SellerReviewListCreateView.as_view(), name='seller_review_list_create'),
    path('sellers/<uuid:seller_id>/reviews/stats/', SellerReviewStatsView.as_view(), name='seller_review_stats'),
    path('seller-reviews/<uuid:pk>/', SellerReviewDetailView.as_view(), name='seller_review_detail'),
    path('my-seller-reviews/', MySellerReviewsView.as_view(), name='my_seller_reviews'),
    path('reviews-received/', ReviewsReceivedView.as_view(), name='reviews_received'),
    
                      
    path('reviews/<str:review_type>/<uuid:review_id>/response/', ReviewResponseCreateView.as_view(), name='review_response'),
    
                          
    path('reviews/<str:review_type>/<uuid:review_id>/helpful/', ReviewHelpfulToggleView.as_view(), name='review_helpful_toggle'),
    
                   
    path('reviews/<str:review_type>/<uuid:review_id>/images/', ReviewImageUploadView.as_view(), name='review_image_upload'),
    
                  
    path('reviews/flag/', ReviewFlagCreateView.as_view(), name='review_flag'),
    path('reviews/flags/moderation/', ReviewFlagModerationQueueView.as_view(), name='review_flag_moderation_queue'),
    path('reviews/flags/moderation/<uuid:flag_id>/', ReviewFlagModerationDetailView.as_view(), name='review_flag_moderation_detail'),
    
               
    path('top-rated-products/', top_rated_products, name='top_rated_products'),
    path('top-rated-sellers/', top_rated_sellers, name='top_rated_sellers'),
]
