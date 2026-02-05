# core/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
import redis
from django.http import HttpResponse
from django.conf import settings
import os


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Check health of services"""
    
    health_status = {
        'status': 'healthy',
        'database': 'ok',
        'cache': 'ok',
        'celery': 'ok'
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        health_status['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise Exception('Cache read/write failed')
    except Exception as e:
        health_status['cache'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check Celery
    try:
        from zonto_config.celery import app
        inspect = app.control.inspect()
        if not inspect.active():
            raise Exception('No active Celery workers')
    except Exception as e:
        health_status['celery'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return Response(health_status, status=status_code)



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
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='text/html')
        except FileNotFoundError:
            return HttpResponse('Page not found', status=404)


class MarketplaceView:
    def __call__(self, request, section=None, page=None):
        if section is None:
            section = 'products'
            page = 'index'
        
        if page is None:
            page = 'index'
        
        file_path = os.path.join(
            settings.BASE_DIR, 
            'frontend', 
            'marketplace', 
            section, 
            f'{page}.html'
        )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='text/html')
        except FileNotFoundError:
            return HttpResponse(f'Page not found: {section}/{page}.html', status=404)


assistant_view = AssistantView()
marketplace_view = MarketplaceView()