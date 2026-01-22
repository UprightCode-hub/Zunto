from django.urls import path
from .views import DashboardView

app_name = 'dashboard'   # 👈 THIS LINE IS REQUIRED

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]
