from django.urls import path
from .views import analytics_dashboard

urlpatterns = [
    path("analytics/", analytics_dashboard, name="analytics_dashboard"),
]
