# AltiusOne/settings.py
from django.utils.translation import gettext_lazy as _
import os
from pathlib import Path
# from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-gb34+&(pz_003zf^$uu!wbkm2!_vf@9eg)p47%h^49@r8p8)x1'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

MAIN_APPS = [
    'modeltranslation',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django.contrib.humanize",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.contrib.postgres",
]

EXTERNAL_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "django_cotton",
    "widget_tweaks",
    "django_json_widget",
    "pwa",
    "drf_yasg",
    'corsheaders',
    "celery",
]

LOCAL_APPS = [
    "comptabilite",
    "documents",
    "facturation",
    "salaires",
    "tva",
    "fiscalite",
    "core",
    "analytics",
]


INSTALLED_APPS = MAIN_APPS + LOCAL_APPS + EXTERNAL_APPS

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'AltiusOne.urls'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
            ],
        },
    },
]

WSGI_APPLICATION = 'AltiusOne.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "altiusone",
        "USER": "MainFiDuUser",
        "PASSWORD": "Z@mbie92FiDu",
        "HOST": "altiusone_postgres",
        "PORT": "5432",
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/


LANGUAGE_CODE = 'fr'

TIME_ZONE = 'Europe/Zurich'

USE_I18N = True
USE_L10N = True
USE_TZ = True


LANGUAGES = [
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("en", "English"),
]

MODELTRANSLATION_DEFAULT_LANGUAGE = "fr"
MODELTRANSLATION_LANGUAGES = ("fr", "de", "it", "en")
MODELTRANSLATION_FALLBACK_LANGUAGES = ("fr", "en")

# Application specific settings
ALTIUSFIDU_VERSION = "1.0.0"
ALTIUSFIDU_SUPPORT_EMAIL = "support@altiusone.ch"
 
LOCALE_PATHS = (
    os.path.join(
        BASE_DIR, "locale"
    ),  # Répertoire où les fichiers de traduction seront stockés
)


LANGUAGE_COOKIE_NAME = "django_language"
LANGUAGE_COOKIE_AGE = None
LANGUAGE_COOKIE_PATH = "/"
LANGUAGE_COOKIE_SECURE = True
LANGUAGE_COOKIE_HTTPONLY = True
LANGUAGE_COOKIE_SAMESITE = "Lax"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

# Static files configuration
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Additional directories for static files
STATICFILES_DIRS = [
    BASE_DIR / "static",  # Si vous avez un dossier static à la racine
]

# Static files finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Configuration pour phonenumber_field
PHONENUMBER_DEFAULT_REGION = "CH"  # La Suisse comme région par défaut
PHONENUMBER_DEFAULT_FORMAT = "INTERNATIONAL"  # Format par défaut

# Redis Configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'altiusone',
        'TIMEOUT': 300,
    }
}
 

# Email Configuration
# EMAIL_BACKEND = config(
#     "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
# )
# EMAIL_HOST = config("EMAIL_HOST", default="localhost")
# EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
# EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
# EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
# EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
# DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@altiusone.ch")

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Zurich'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes



# Configuration du modèle User personnalisé
AUTH_USER_MODEL = 'core.User'


# ============================================================================
# AUTHENTICATION CONFIGURATION
# ============================================================================

# Login/Logout URLs
LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"

# Password reset timeout (en secondes) - 24 heures
PASSWORD_RESET_TIMEOUT = 86400

# Session configuration
SESSION_COOKIE_AGE = 1209600  # 2 semaines
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG  # True en production
SESSION_SAVE_EVERY_REQUEST = False

# CSRF Configuration
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True

# ============================================================================
# SOCIAL AUTH CONFIGURATION (désactivé par défaut)
# ============================================================================

# Décommenter ces lignes quand vous aurez configuré les clés OAuth
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # Django par défaut
    # "social_core.backends.google.GoogleOAuth2",  # Google (à activer)
    # "social_core.backends.microsoft.MicrosoftOAuth2",  # Microsoft (à activer)
]

# Social Auth Settings (à configurer plus tard)
# SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_OAUTH2_KEY', '')
# SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_OAUTH2_SECRET', '')

# SOCIAL_AUTH_MICROSOFT_OAUTH2_KEY = os.environ.get('MICROSOFT_OAUTH2_KEY', '')
# SOCIAL_AUTH_MICROSOFT_OAUTH2_SECRET = os.environ.get('MICROSOFT_OAUTH2_SECRET', '')

# SOCIAL_AUTH_LOGIN_REDIRECT_URL = 'core:dashboard'
# SOCIAL_AUTH_NEW_USER_REDIRECT_URL = 'core:dashboard'




# REST Framework Configuration
# AltiusOne/settings.py
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",  # Ajouter ceci !
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",  # Si vous utilisez les tokens
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

CORS_ALLOW_CREDENTIALS = True

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]