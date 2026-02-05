# core/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings
from django.template import Template, RequestContext
import os

# --- Health Check (Preserved) ---
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    health_status = {'status': 'healthy', 'database': 'ok', 'cache': 'ok', 'celery': 'ok'}
    
    # 1. Database Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # 2. Cache Check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise Exception('Cache read/write failed')
    except Exception as e:
        health_status['cache'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # 3. Celery Check
    try:
        from zonto_config.celery import app
        inspect = app.control.inspect()
        if not inspect or not inspect.active():
            raise Exception('No active Celery workers')
    except Exception:
        health_status['celery'] = 'error: check failed'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return Response(health_status, status=status_code)


# --- Helper Function for Manual Rendering ---
def render_manual_template(request, file_path):
    """
    Reads a file manually but renders it as a Django template.
    Auto-injects {% load static %} if missing to prevent 'Invalid block tag' errors.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        # SMART FIX: Check if static tag is used but not loaded
        # We only inject if 'extends' is NOT present (extends must be first line)
        if '{% static' in raw_content and '{% load static %}' not in raw_content:
            if '{% extends' not in raw_content:
                raw_content = '{% load static %}\n' + raw_content
            # If extends is present, we assume the parent template loads static
            # or the user must add it manually to avoid breaking template inheritance.

        template = Template(raw_content)
        context = RequestContext(request, {}) 
        return HttpResponse(template.render(context), content_type='text/html')
        
    except FileNotFoundError:
        # Extract meaningful name for error (e.g., 'marketplace/products/index.html')
        relative_path = os.path.relpath(file_path, settings.BASE_DIR)
        return HttpResponse(f'Page not found: {relative_path}', status=404)
    except Exception as e:
        return HttpResponse(f"Error rendering template: {e}", status=500)


# --- Views ---

class AssistantView:
    def __call__(self, request, page='index'):
        page_map = {
            'index': 'index.html',
            'chat': 'chat.html',
            'about': 'about.html',
            'report': 'report.html',
        }
        
        html_file = page_map.get(page, 'index.html')
        file_path = os.path.join(settings.BASE_DIR, 'frontend', 'assistant', html_file)
        
        return render_manual_template(request, file_path)


class MarketplaceView:
    def __call__(self, request, section=None, page=None):
        section = section or 'products'
        page = page or 'index'
        
        file_path = os.path.join(
            settings.BASE_DIR, 
            'frontend', 
            'marketplace', 
            section, 
            f'{page}.html'
        )
        
        return render_manual_template(request, file_path)

assistant_view = AssistantView()
marketplace_view = MarketplaceView()