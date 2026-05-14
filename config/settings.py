"""
Django settings for Delchris Ecommerce Platform

Configured to use Supabase PostgreSQL database with Django REST Framework
"""

import os
from pathlib import Path
from decouple import config

# Load environment variables from .env.local file
env_file = os.path.join(os.path.dirname(__file__), '..', '.env.local')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-gwcy(bh&w^7)@ohk#t0_d6^p(_t^&c9wefq@*qu(5(r5=bnx*9')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)


ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Paystack Payment Gateway
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='', cast=str)
PAYSTACK_PUBLIC_KEY = config('PAYSTACK_PUBLIC_KEY', default='', cast=str)

# Supabase Storage Configuration
# Service role key bypasses RLS policies for write operations (uploads/deletes)
NEXT_PUBLIC_SUPABASE_URL = config('NEXT_PUBLIC_SUPABASE_URL', default='', cast=str)
NEXT_PUBLIC_SUPABASE_ANON_KEY = config('NEXT_PUBLIC_SUPABASE_ANON_KEY', default='', cast=str)
SUPABASE_SERVICE_ROLE_KEY = config('SUPABASE_SERVICE_ROLE_KEY', default='', cast=str)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
'django.contrib.messages',
    'django.contrib.staticfiles',
    
# Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_celery_beat',
    
    # Local apps
    'users.apps.UsersConfig',
    'products.apps.ProductsConfig',
    'orders.apps.OrdersConfig',
    'payments.apps.PaymentsConfig',
    'reviews.apps.ReviewsConfig',
    'analytics.apps.AnalyticsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# Database Configuration - Supabase PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('SUPABASE_DB_NAME', default='postgres'),
        'USER': config('SUPABASE_DB_USER', default='postgres'),
        'PASSWORD': config('SUPABASE_DB_PASSWORD', default=''),
        'HOST': config('SUPABASE_DB_HOST', default='localhost'),
        'PORT': config('SUPABASE_DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'sslmode': 'require',
            'connect_timeout': 10,
        }
    }
}

# Force IPv4 for Supabase connection
import socket
socket.setdefaulttimeout(30)


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CORS_ALLOW_CREDENTIALS = True

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ----------------------------
# Emailing (Resend)
# ----------------------------
# Required env vars (set in .env.local or deployment env):
# RESEND_API_KEY=...
# RESEND_FROM_EMAIL="Your Brand <no-reply@domain.com>"
# EMAILING_ADMIN_EMAILS="admin1@domain.com,admin2@domain.com"
RESEND_API_KEY = config('RESEND_API_KEY', default='', cast=str)
RESEND_FROM_EMAIL = config('RESEND_FROM_EMAIL', default='', cast=str)
EMAILING_ADMIN_EMAILS = config('EMAILING_ADMIN_EMAILS', default='', cast=str)

# ----------------------------
# Celery (Broker)
# ----------------------------
REDIS_URL = config("REDIS_URL", default="", cast=str)

# Configure Celery broker based on REDIS_URL presence:
# - If REDIS_URL is explicitly set, always use Redis (works in both DEBUG=True/False)
# - If no REDIS_URL, always use localhost Redis (not in-memory!)
# IMPORTANT: In-memory broker ("memory://") does NOT persist tasks and will cause
# emails to never send. Always use Redis for task persistence.
if REDIS_URL:
    # Explicit Redis URL provided - use it (recommended for both dev and prod)
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
else:
    # Always use localhost Redis - never use in-memory broker!
    # In-memory causes tasks to be lost immediately
    CELERY_BROKER_URL = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_ENABLE_UTC = True

# If you don't create PeriodicTask records in admin, this schedule will still work.
CELERY_BEAT_SCHEDULE = {
    "abandoned-cart-reminder-every-3-days": {
        "task": "emailing.send_abandoned_cart_reminders_batch",
        "schedule": 60 * 60 * 24 * 3,  # seconds
    }
}

# Custom User Model
AUTH_USER_MODEL = 'users.CustomUser'
