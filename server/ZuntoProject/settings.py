import os
from pathlib import Path
from decouple import config
from celery.schedules import crontab
import dj_database_url
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================
# ENVIRONMENT DETECTION
# ============================================

IS_PRODUCTION = os.environ.get('RENDER', 'False') == 'True'

if IS_PRODUCTION:
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    ALLOWED_HOSTS = [
        '.onrender.com',
        'zunto-backend.onrender.com',
        'localhost:5174',
    ]
else:
    DEBUG = config('DEBUG', default=True, cast=bool)
    SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-me-in-production')
    ALLOWED_HOSTS = ['*']

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
    SECURE_REFERRER_POLICY = 'same-origin'
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# ============================================
# APPLICATIONS
# ============================================

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'channels',
    'rest_framework',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    'rangefilter',
    'import_export',
    'accounts',
    'market',
    'reviews',
    'cart',
    'orders',
    'notifications',
    'chat',
    'assistant',
    'rest_framework_simplejwt.token_blacklist',  
]

# CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
# CRISPY_TEMPLATE_PACK = "bootstrap5"

# ============================================
# MIDDLEWARE
# ============================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'assistant.middleware.DisableCSRFForAPIMiddleware',
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
ASGI_APPLICATION = 'ZuntoProject.asgi.application'

# ============================================
# TEMPLATES
# ============================================

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates', BASE_DIR / 'frontend'],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#                 'django.template.context_processors.media',
#                 'django.template.context_processors.static',
#             ],
#         },
#     },
# ]

# ============================================
# DATABASE
# ============================================

if IS_PRODUCTION:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=False,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ============================================
# REDIS CONFIGURATION
# ============================================

REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)
REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}'

# ============================================
# CACHING
# ============================================

if IS_PRODUCTION:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'zunto-dev',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'zunto',
        }
    }

# ============================================
# SESSION CONFIGURATION
# ============================================

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1209600
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'

# ============================================
# CHANNELS & WEBSOCKETS
# ============================================

if IS_PRODUCTION:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [config('REDIS_URL', default=REDIS_URL)],
                'capacity': 1500,
                'expiry': 10,
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [(REDIS_HOST, REDIS_PORT)],
                'capacity': 1500,
                'expiry': 10,
            },
        },
    }

# ============================================
# REST FRAMEWORK
# ============================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
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
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), "static_cdn", "media_root")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
MAX_UPLOAD_SIZE = 5242880

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

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ============================================
# CELERY CONFIGURATION
# ============================================

if IS_PRODUCTION:
    CELERY_BROKER_URL = config('REDIS_URL', default=REDIS_URL + '/1')
    CELERY_RESULT_BACKEND = config('REDIS_URL', default=REDIS_URL + '/2')
    CELERY_TASK_ALWAYS_EAGER = False
else:
    CELERY_BROKER_URL = REDIS_URL + '/1'
    CELERY_RESULT_BACKEND = REDIS_URL + '/2'
    CELERY_TASK_ALWAYS_EAGER = True

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60

CELERY_BEAT_SCHEDULE = {
    'detect-abandoned-carts': {
        'task': 'cart.tasks.detect_abandoned_carts',
        'schedule': crontab(hour=2, minute=0),  # Daily 2 AM
    },
    'send-abandonment-reminders': {
        'task': 'cart.tasks.send_abandonment_reminders',
        'schedule': crontab(hour=3, minute=0),  # Daily 3 AM
    },
    'calculate-user-scores': {
        'task': 'cart.tasks.calculate_user_scores_bulk',
        'schedule': crontab(hour=4, minute=0),  # Daily 4 AM
    },
    'cleanup-old-guest-carts': {
        'task': 'cart.tasks.cleanup_old_guest_carts',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),  # Weekly Sunday 5 AM
        'kwargs': {'days': 30}
    },
}
# ============================================
# PAYSTACK CONFIGURATION
# ============================================

PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='')
PAYSTACK_BASE_URL = 'https://api.paystack.co'

# ============================================
# CORS CONFIGURATION
# ============================================

if IS_PRODUCTION:
    CORS_ALLOWED_ORIGINS = [
        'https://zunto-frontend.onrender.com',
    ]
    CSRF_TRUSTED_ORIGINS = [
        'https://zunto-frontend.onrender.com',
    ]
    CORS_ALLOW_ALL_ORIGINS = False
else:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:5174',
        'http://127.0.0.1:5174',
        'http://localhost:5500',
        'http://127.0.0.1:5500',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:5174',
        'http://127.0.0.1:5174',
        'http://localhost:5500',
        'http://127.0.0.1:5500',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]

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
# AI ASSISTANT CONFIGURATION
# ============================================

GROQ_API_KEY = config('GROQ_API_KEY', default='')
GROQ_MODEL = config('GROQ_MODEL', default='llama-3.3-70b-versatile')

FAQ_MATCH_THRESHOLD = config('FAQ_MATCH_THRESHOLD', default=0.7, cast=float)
SENTENCE_TRANSFORMER_MODEL = config(
    'SENTENCE_TRANSFORMER_MODEL', 
    default='all-MiniLM-L6-v2'
)

# Phase 1 Orchestration Feature Flags
PHASE1_UNIFIED_CONFIDENCE = config('PHASE1_UNIFIED_CONFIDENCE', default=True, cast=bool)
PHASE1_CONTEXT_INTEGRATION = config('PHASE1_CONTEXT_INTEGRATION', default=True, cast=bool)
PHASE1_INTENT_CACHING = config('PHASE1_INTENT_CACHING', default=True, cast=bool)
PHASE1_LLM_CONTEXT_ENRICHMENT = config('PHASE1_LLM_CONTEXT_ENRICHMENT', default=True, cast=bool)
PHASE1_RESPONSE_PERSONALIZATION_FIX = config('PHASE1_RESPONSE_PERSONALIZATION_FIX', default=True, cast=bool)
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
            'maxBytes': 1024 * 1024 * 5,
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

LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ============================================
# DATA UPLOAD SETTINGS
# ============================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880

# ============================================
# MISC
# ============================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

ADMIN_SITE_HEADER = "Zunto Administration"
ADMIN_SITE_TITLE = "Zunto Admin Portal"
ADMIN_INDEX_TITLE = "Welcome to Zunto Admin Portal"

ASSISTANT_PORTFOLIO_MODE = True

os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['TRANSFORMERS_CACHE'] = '/tmp'
os.environ['HF_HOME'] = '/tmp'
os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/tmp'

CHAT_HMAC_SECRET = config('CHAT_HMAC_SECRET', default='change-me-in-production')


# ============================================
# JWT CONFIGURATION (ADD THIS NEW SECTION)
# ============================================

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'JTI_CLAIM': 'jti',
}

# ============================================
# FRONTEND URL
# ============================================
if IS_PRODUCTION:
    FRONTEND_URL = 'https://zunto-frontend.onrender.com'
else:
    FRONTEND_URL = 'http://localhost:5173'  # Vite dev server