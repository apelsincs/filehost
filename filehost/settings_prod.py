"""
Production settings for 0123.ru file hosting
"""
import os
from pathlib import Path
from .settings import *

# Import dj_database_url for database configuration
try:
    import dj_database_url
except ImportError:
    dj_database_url = None

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# Production hosts - can be easily updated when domain is available
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL and DATABASE_URL.startswith('postgresql://') and dj_database_url:
    # PostgreSQL для продакшена
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    # Fallback на отдельные переменные
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'filehost'),
            'USER': os.environ.get('DB_USER', 'filehost_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {
                'MAX_CONNS': 20,  # Максимальное количество соединений
                'MIN_CONNS': 5,   # Минимальное количество соединений
                'CONN_MAX_AGE': 600,  # Максимальное время жизни соединения (10 минут)
                'CONN_HEALTH_CHECKS': True,  # Проверка здоровья соединений
            },
            'CONN_MAX_AGE': 600,  # Django connection pooling
            'ATOMIC_REQUESTS': False,  # Отключаем для лучшей производительности
        }
    }

# Database optimization
DB_OPTIMIZATION = {
    'ENABLE_CONNECTION_POOLING': True,
    'MAX_CONNECTIONS': 20,
    'MIN_CONNECTIONS': 5,
    'CONNECTION_TIMEOUT': 30,
    'STATEMENT_TIMEOUT': 30000,  # 30 секунд
    'IDLE_IN_TRANSACTION_SESSION_TIMEOUT': 600000,  # 10 минут
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS settings (enable when SSL is configured)
if os.environ.get('USE_HTTPS', 'False').lower() == 'true':
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Site base URL for generating absolute URLs
SITE_BASE_URL = os.environ.get('SITE_BASE_URL', 'http://localhost:8000')

# File upload settings
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 26214400))  # 25MB default
FILE_EXPIRY_HOURS = int(os.environ.get('FILE_EXPIRY_HOURS', 24))

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Logging configuration
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
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'files': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Sentry configuration (optional)
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=True,
    )

# CORS settings
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else []
CORS_ALLOW_CREDENTIALS = True

# Additional security middleware
MIDDLEWARE += [
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Celery Beat Schedule
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Worker Settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000  # 200MB

# Celery Task Routes
CELERY_TASK_ROUTES = {
    'files.tasks.*': {'queue': 'files'},
    'files.tasks.cleanup_expired_files': {'queue': 'maintenance'},
}

# Celery Queues
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'files': {
        'exchange': 'files',
        'routing_key': 'files',
    },
    'maintenance': {
        'exchange': 'maintenance',
        'routing_key': 'maintenance',
    },
}

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Custom settings for production
TEMPLATES[0]['OPTIONS']['debug'] = False

# Disable Django admin in production (optional security measure)
# ADMIN_ENABLED = os.environ.get('ADMIN_ENABLED', 'False').lower() == 'true'
# if not ADMIN_ENABLED:
#     ADMIN_URL = 'admin/'
#     ADMIN_SITE_HEADER = "0123.ru Administration"
#     ADMIN_SITE_TITLE = "0123.ru Admin Portal"
#     ADMIN_INDEX_TITLE = "Welcome to 0123.ru Administration"
