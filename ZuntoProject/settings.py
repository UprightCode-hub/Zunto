"""
Django settings for ZuntoProject.

Updated for Python 3.12 and Django 5.1.3
Includes: Chat, Assistant (Groq AI), WebSockets, Channels
Preserves all your features + adds stability improvements from other developer
"""

import os
from pathlib import Path
from decouple import config
from celery.schedules import crontab
from dotenv import load_dotenv
import dj_database_url

load_dotenv()


import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
# Render.com deployment settings
RENDER = os.environ.get('RENDER', False)

if RENDER:
    DEBUG = False
    ALLOWED_HOSTS = ['.onrender.com', 'localhost', '127.0.0.1']
    
    # Database from environment
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    
    # Static files
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# ============================================
# BASE & SECURITY
# ============================================



SECRET_KEY = config('SECRET_KEY', default='your-secret-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,*,.herokuapp.com,unevinced-propraetorial-milda.ngrok-free.dev').split(',')

# Production Security Settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ============================================
# APPLICATIONS
# ============================================

INSTALLED_APPS = [
    # Channels (must be first for WebSocket support)
    'daphne',
    
    # Core Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Development Tools
    'django_extensions',

    # Third-Party Apps
    'channels',  # WebSockets for real-time chat
    'rest_framework',  # API support
    'corsheaders',  # CORS for API/frontend separation
    'crispy_forms',
    'crispy_bootstrap5',
    'rangefilter',  # Admin date range filter
    'import_export',  # Import/Export data in admin

    # Local Apps
    'accounts',
    'market',
    'reviews',
    'cart',
    'orders',
    'notifications',
    'chat',  # Your WebSocket chat feature
    'assistant',  # Your AI assistant with Groq + FAQ
]

# Crispy Forms Configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ============================================
# MIDDLEWARE
# ============================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS (if using separate frontend)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ============================================
# URL & WSGI/ASGI
# ============================================

ROOT_URLCONF = 'ZuntoProject.urls'
WSGI_APPLICATION = 'ZuntoProject.wsgi.application'
ASGI_APPLICATION = 'ZuntoProject.asgi.application'  # Required for Channels/WebSockets

# ============================================
# TEMPLATES
# ============================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

# ============================================
# DATABASE
# ============================================

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///' + str(BASE_DIR / 'db.sqlite3')),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ============================================
# CACHING (Redis for production performance)
# ============================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'db': 1,
            'parser_class': 'redis.connection.PythonParser',
            'pool_class': 'redis.BlockingConnectionPool',
        }
    }
}

# ============================================
# CHANNELS & WEBSOCKETS
# ============================================

CHANNEL_LAYERS = {
    'default': {
        # Use Redis if REDIS_URL is provided (Heroku), otherwise in-memory
        'BACKEND': 'channels_redis.core.RedisChannelLayer' if config('REDIS_URL', default=None) else 'channels.layers.InMemoryChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://127.0.0.1:6379')],
        } if config('REDIS_URL', default=None) else {},
    },
}

# ============================================
# REST FRAMEWORK (for API endpoints)
# ============================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# ============================================
# AUTHENTICATION
# ============================================

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Password Reset Timeout (1 hour)
PASSWORD_RESET_TIMEOUT = 3600

# ============================================
# INTERNATIONALIZATION
# ============================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# ============================================
# STATIC & MEDIA FILES
# ============================================

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static_my_project"]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), "static_cdn", "media_root")

# WhiteNoise Static Files Storage
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Allowed file upload extensions
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
MAX_UPLOAD_SIZE = 5242880  # 5MB

# ============================================
# EMAIL CONFIGURATION
# ============================================

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='ZONTO <noreply@zonto.com>')
ADMIN_EMAIL = config('ADMIN_EMAIL', default='admin@zonto.com')

# For development - console backend
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================
# CELERY CONFIGURATION
# ============================================

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

CELERY_BEAT_SCHEDULE = {
    'send-cart-abandonment-emails': {
        'task': 'notifications.tasks.send_cart_abandonment_emails',
        'schedule': crontab(hour=10, minute=0),
    },
    'calculate-daily-statistics': {
        'task': 'analytics.tasks.calculate_daily_statistics',
        'schedule': crontab(hour=0, minute=5),
    },
    'calculate-yesterday-statistics': {
        'task': 'analytics.tasks.calculate_yesterday_statistics',
        'schedule': crontab(hour=1, minute=0),
    },
}

# ============================================
# PAYSTACK CONFIGURATION
# ============================================

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

# ============================================
# SESSIONS
# ============================================

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

# Use cache for sessions in production (optional)
# SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
# SESSION_CACHE_ALIAS = 'default'

# ============================================
# CORS CONFIGURATION (for separate frontend)
# ============================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000,https://unevinced-propraetoorial-milda.ngrok-free.dev'
).split(',')

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============================================
# CSRF CONFIGURATION
# ============================================

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000,https://unevinced-propraetorial-milda.ngrok-free.dev'
).split(',')

# ============================================
# AI ASSISTANT CONFIGURATION
# ============================================

# Groq AI Configuration (Cloud-based LLM)
GROQ_API_KEY = config('GROQ_API_KEY', default='')
GROQ_MODEL = config('GROQ_MODEL', default='mixtral-8x7b-32768')

# FAQ Matching Configuration (Local semantic search)
FAQ_MATCH_THRESHOLD = config('FAQ_MATCH_THRESHOLD', default=0.7, cast=float)
SENTENCE_TRANSFORMER_MODEL = config(
    'SENTENCE_TRANSFORMER_MODEL', 
    default='all-MiniLM-L6-v2'
)

# ============================================
# LOGGING
# ============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ============================================
# DATA UPLOAD SETTINGS
# ============================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# ============================================
# MISC
# ============================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Message Framework Tags (for Bootstrap 5)
from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Admin Site Customization
ADMIN_SITE_HEADER = "Zunto Administration"
ADMIN_SITE_TITLE = "Zunto Admin Portal"
ADMIN_INDEX_TITLE = "Welcome to Zunto Admin Portal"