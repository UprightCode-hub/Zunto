#server/core/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings
from django.template import Template, RequestContext
import os


def _is_admin_request(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, 'is_staff', False) or getattr(user, 'role', None) == 'admin')


def _check_database_health():
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return 'ok', None
    except Exception:
        return 'error', 'database-check-failed'


def _check_cache_health():
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') != 'ok':
            raise RuntimeError('cache roundtrip failed')
        return 'ok', None
    except Exception:
        return 'error', 'cache-check-failed'


def _check_celery_health(include_details=False):
    try:
        from ZuntoProject.celery import app

        inspect = app.control.inspect(timeout=1.0)
        active = inspect.active() or {}
        if not active:
            return 'error', ({'error': 'no-active-workers'} if include_details else None)

        if not include_details:
            return 'ok', None

        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}

        details = {
            'workers': sorted(active.keys()),
            'active_tasks': sum(len(tasks or []) for tasks in active.values()),
            'scheduled_tasks': sum(len(tasks or []) for tasks in scheduled.values()),
            'reserved_tasks': sum(len(tasks or []) for tasks in reserved.values()),
        }
        return 'ok', details
    except Exception:
        if include_details:
            return 'error', {'error': 'celery-check-failed'}
        return 'error', None


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    db_status, db_error = _check_database_health()
    cache_status, cache_error = _check_cache_health()

    include_details = _is_admin_request(request)
    celery_status, celery_details = _check_celery_health(include_details=include_details)

    status_value = 'healthy' if all(v == 'ok' for v in [db_status, cache_status, celery_status]) else 'unhealthy'
    status_code = 200 if status_value == 'healthy' else 503

    if not include_details:
        return Response({'status': status_value}, status=status_code)

    payload = {
        'status': status_value,
        'database': db_status,
        'cache': cache_status,
        'celery': celery_status,
    }
    diagnostics = {}
    if db_error:
        diagnostics['database'] = db_error
    if cache_error:
        diagnostics['cache'] = cache_error
    if celery_details:
        diagnostics['celery'] = celery_details
    if diagnostics:
        payload['diagnostics'] = diagnostics

    return Response(payload, status=status_code)


# Keep static/manual template serving below as-is for legacy UI paths.
def render_manual_template(request, file_path):
    """
    Reads a file manually but renders it as a Django template.
    Auto-injects {% load static %} if missing to prevent 'Invalid block tag' errors.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        if '{% static' in raw_content and '{% load static %}' not in raw_content:
            if '{% extends' not in raw_content:
                raw_content = '{% load static %}\n' + raw_content

        template = Template(raw_content)
        context = RequestContext(request, {})
        return HttpResponse(template.render(context), content_type='text/html')

    except FileNotFoundError:
        relative_path = os.path.relpath(file_path, settings.BASE_DIR)
        return HttpResponse(f'Page not found: {relative_path}', status=404)
    except Exception as e:
        return HttpResponse(f'Error rendering template: {e}', status=500)


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
