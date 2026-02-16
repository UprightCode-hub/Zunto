#server/notifications/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet,
    NotificationPreferenceView,
    EmailLogListView,
    TestEmailView,
    email_templates_list,
    email_statistics,
)

app_name = 'notifications'

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    
                              
    path('preferences/', NotificationPreferenceView.as_view(), name='preferences'),
    
                
    path('logs/', EmailLogListView.as_view(), name='email_logs'),
    
             
    path('test-email/', TestEmailView.as_view(), name='test_email'),
    
           
    path('templates/', email_templates_list, name='templates_list'),
    path('statistics/', email_statistics, name='statistics'),
]
