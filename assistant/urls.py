from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    # Public endpoints
    path('api/ask/', views.ask_assistant, name='ask'),
    path('api/report/', views.create_report, name='report'),
    
    # Admin endpoints
    path('api/admin/recent-logs/', views.recent_logs, name='recent_logs'),
    path('api/admin/recent-reports/', views.recent_reports, name='recent_reports'),
]