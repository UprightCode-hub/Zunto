"""
Zunto AI Assistant - Complete URL Configuration
Production-ready endpoints for ngrok deployment
Created by Wisdom Ekwugha
"""

from django.urls import path, include
from . import views

app_name = 'assistant'

urlpatterns = [
    # ============================================================
    # MAIN CHAT INTERFACE (Landing Page)
    # ============================================================
    # This will be your main ngrok link for LinkedIn
    path('', views.chat_interface, name='home'),  # Main landing page
    path('demo/', views.chat_interface, name='demo'),
    path('chat/', views.chat_interface, name='chat_interface'),  # Alternative demo URL
    
    # ============================================================
    # PREMIUM CHAT API - NEW ENDPOINTS
    # Parallel Ninja endpoints (non-breaking rollout)
    path('ninja/', include('assistant.ninja_urls')),

    # ============================================================
    path('api/chat/', views.chat_endpoint, name='chat'),
    path('api/chat/session/<str:session_id>/', views.session_status, name='session_status'),
    path('api/chat/session/<str:session_id>/reset/', views.reset_session, name='reset_session'),
    path('api/chat/sessions/', views.list_sessions, name='list_sessions'),
    path('api/chat/health/', views.health_check, name='health_check'),
    
    # ============================================================
    # TTS API - Text-to-Speech for Assistant (NEW!)
    # ============================================================
    path('api/tts/', views.tts_endpoint, name='tts'),
    path('api/tts/health/', views.tts_health, name='tts_health'),
    
    # ============================================================
    # LEGACY ENDPOINTS - Backward Compatibility
    # ============================================================
    path('api/ask/', views.ask_assistant, name='ask'),
    path('api/report/', views.create_report, name='report'),
    # Dispute evidence endpoints (Phase 3)
    path('api/report/<int:report_id>/evidence/', views.upload_report_evidence, name='upload_report_evidence'),
    path('api/report/<int:report_id>/evidence/list/', views.list_report_evidence, name='list_report_evidence'),
    path('api/report/<int:report_id>/close/', views.close_report, name='close_report'),

    path('api/legacy/chat/', views.legacy_chat_endpoint, name='legacy_chat'),
    
    # ============================================================
    # ADMIN & MONITORING ENDPOINTS
    # ============================================================
    path('api/admin/logs/', views.recent_logs, name='recent_logs'),
    path('api/admin/reports/', views.recent_reports, name='recent_reports'),
    
    # ============================================================
    # DOCUMENTATION & INFO
    # ============================================================
    path('api/docs/', views.api_documentation, name='api_docs'),
    path('api/about/', views.about_page, name='about'),
]