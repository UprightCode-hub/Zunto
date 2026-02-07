"""
Zunto AI Assistant - Clean URL Configuration
Ready for production and ngrok deployment
Created by Wisdom Ekwugha
"""

from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    # ============================================================
    # MAIN CHAT INTERFACE (Landing Page)
    # ============================================================
path('', views.chat_interface, name='home'),  # Main landing page
path('demo/', views.chat_interface, name='demo'),
path('chat/', views.chat_interface, name='chat_interface'),  # Alternative demo URL

# ============================================================
# PREMIUM CHAT API
# ============================================================
path('chat/', views.chat_endpoint, name='chat'),
path('chat/session/<str:session_id>/', views.session_status, name='session_status'),
path('chat/session/<str:session_id>/reset/', views.reset_session, name='reset_session'),
path('chat/sessions/', views.list_sessions, name='list_sessions'),
path('chat/health/', views.health_check, name='health_check'),

# ============================================================
# TTS API - Text-to-Speech
# ============================================================
path('tts/', views.tts_endpoint, name='tts'),
path('tts/health/', views.tts_health, name='tts_health'),

# ============================================================
# LEGACY ENDPOINTS - Backward Compatibility
# ============================================================
path('ask/', views.ask_assistant, name='ask'),
path('report/', views.create_report, name='report'),
path('legacy/chat/', views.legacy_chat_endpoint, name='legacy_chat'),

# ============================================================
# ADMIN & MONITORING
# ============================================================
path('admin/logs/', views.recent_logs, name='recent_logs'),
path('admin/reports/', views.recent_reports, name='recent_reports'),

# ============================================================
# DOCUMENTATION & INFO
# ============================================================
path('docs/', views.api_documentation, name='api_docs'),
path('about/', views.about_page, name='about'),
]
