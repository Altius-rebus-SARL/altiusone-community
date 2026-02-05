# AltiusOne/settings.py
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import os
from pathlib import Path
# from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,django').split(',')

# CSRF trusted origins (required for Django 4+)
# Format: https://domain.com (must include protocol)
CSRF_TRUSTED_ORIGINS = [
    f"https://{host.strip()}" for host in os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')
    if host.strip() and host.strip() not in ('localhost', '127.0.0.1')
]
# Always include localhost for development
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend(['http://localhost:8000', 'http://localhost:8012', 'http://127.0.0.1:8000'])


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
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "widget_tweaks",
    "drf_spectacular",
    'corsheaders',
    'django_countries',
    'import_export',
    # OAuth2/OIDC Provider pour Docs
    'oauth2_provider',
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
    "mailing",
    "editeur",
    "modelforms",
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
        "NAME": os.environ.get("POSTGRES_DB", "altiusone"),
        "USER": os.environ.get("POSTGRES_USER", "altiusone"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", os.environ.get("DB_HOST", "altiusone_postgres")),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
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
# Note: La configuration SMTP principale est gérée via le modèle ConfigurationEmail
# Ces valeurs sont utilisées comme fallback si aucune configuration n'existe en base
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@altiusone.ch")

# Support email pour l'application
ALTIUSONE_SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@altiusone.ch")

# ============================================================================
# FERNET ENCRYPTION (pour chiffrer les mots de passe SMTP en base de données)
# ============================================================================
# Générer une clé: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEYS = [
    os.environ.get('FERNET_KEY', 'your-32-url-safe-base64-encoded-key-here'),
]

# ============================================================================
# INVITATION SETTINGS
# ============================================================================
# Durée de validité des invitations (en jours)
INVITATION_EXPIRY_DAYS = int(os.environ.get('INVITATION_EXPIRY_DAYS', 7))
# Limite par défaut d'utilisateurs qu'un responsable client peut inviter par mandat
INVITATION_DEFAULT_LIMIT_PER_MANDAT = int(os.environ.get('INVITATION_DEFAULT_LIMIT', 5))

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Zurich'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery Beat - Taches planifiees
CELERY_BEAT_SCHEDULE = {
    # Traiter les documents en attente toutes les 5 minutes
    'traiter-documents-en-attente': {
        'task': 'documents.tasks.traiter_documents_en_attente',
        'schedule': 300.0,  # 5 minutes
    },
    # Indexer les documents sans embedding toutes les heures
    'indexer-documents-sans-embedding': {
        'task': 'documents.tasks.indexer_documents_sans_embedding',
        'schedule': 3600.0,  # 1 heure
    },
    # Verifier le service AI toutes les 15 minutes
    'verifier-service-ai': {
        'task': 'documents.tasks.verifier_service_ai',
        'schedule': 900.0,  # 15 minutes
    },
}



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
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}


# ============================================================================
# API DOCUMENTATION (drf-spectacular)
# ============================================================================

# Construire les serveurs dynamiquement depuis ALLOWED_HOSTS
_spectacular_servers = []
for host in ALLOWED_HOSTS:
    if host.strip() and host.strip() not in ('localhost', '127.0.0.1', '*'):
        _spectacular_servers.append({
            'url': f'https://{host.strip()}',
            'description': host.strip()
        })

# Ajouter localhost en dev
if DEBUG:
    _spectacular_servers.append({
        'url': 'http://localhost:8000',
        'description': 'Development'
    })

SPECTACULAR_SETTINGS = {
    'TITLE': 'AltiusOne API',
    'DESCRIPTION': 'API de gestion fiduciaire complète pour la Suisse',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {'email': 'contact@altiusone.ch'},
    'LICENSE': {'name': 'Proprietary'},
    'SERVERS': _spectacular_servers,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': False,
    },
    'SECURITY': [
        {'BearerAuth': []},
    ],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
}

# ============================================================================
# JWT CONFIGURATION (Simple JWT)
# ============================================================================
SIMPLE_JWT = {
    # Token lifetimes
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,

    # Algorithm
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,

    # Token types
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",

    # Token claims
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    # Serializers
    "TOKEN_OBTAIN_SERIALIZER": "core.jwt_serializers.CustomTokenObtainPairSerializer",
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

# ============================================================================
# DJANGO 6 - CONTENT SECURITY POLICY (CSP)
# ============================================================================
# La CSP protège contre les attaques XSS en déclarant les sources de contenu fiables

# Activer le middleware CSP
# MIDDLEWARE += [
#     'django.middleware.security.ContentSecurityPolicyMiddleware',
# ]

# # Configuration CSP
# CONTENT_SECURITY_POLICY = {
#     # Directive par défaut
#     "default-src": ["'self'"],

#     # Scripts JavaScript
#     "script-src": [
#         "'self'",
#         "'unsafe-inline'",  # Nécessaire pour certains scripts inline (à réduire progressivement)
#         "https://unpkg.com",  # HTMX
#         "https://cdn.jsdelivr.net",  # CDN
#     ],

#     # Styles CSS
#     "style-src": [
#         "'self'",
#         "'unsafe-inline'",  # Nécessaire pour les styles inline Bootstrap
#         "https://fonts.googleapis.com",
#     ],

#     # Images
#     "img-src": [
#         "'self'",
#         "data:",  # Pour les images base64 (QR codes)
#         "blob:",  # Pour les previews d'images
#     ],

#     # Polices
#     "font-src": [
#         "'self'",
#         "https://fonts.gstatic.com",
#     ],

#     # Connexions (AJAX, WebSocket)
#     "connect-src": [
#         "'self'",
#     ],

#     # Frames
#     "frame-ancestors": ["'none'"],

#     # Formulaires
#     "form-action": ["'self'"],

#     # Base URI
#     "base-uri": ["'self'"],
# }

# Mode report-only en développement (pour tester sans bloquer)
CONTENT_SECURITY_POLICY_REPORT_ONLY = DEBUG

# URL de rapport des violations CSP (optionnel)
# CONTENT_SECURITY_POLICY_REPORT_URI = "/csp-report/"


# ============================================================================
# PERMISSIONS MÉTIER - Context Processor
# ============================================================================
# Ajouter le context processor pour les permissions dans les templates

TEMPLATES[0]['OPTIONS']['context_processors'].append(
    'core.permissions.permissions_context'
)


# ============================================================================
# S3/MINIO STORAGE CONFIGURATION
# ============================================================================
# MinIO est utilisé comme backend S3-compatible pour:
# - Les fichiers uploadés (documents, images, factures, etc.)
# - Le partage avec Nextcloud via External Storage
#
# Architecture:
# - Django écrit dans MinIO via django-storages (S3Boto3Storage)
# - Nextcloud accède aux mêmes fichiers via External Storage S3
# - Les médias Django sont ainsi disponibles dans Nextcloud

USE_S3 = os.environ.get('USE_S3', 'False').lower() in ('true', '1', 'yes')

if USE_S3:
    # Configuration AWS/S3 pour MinIO
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', os.environ.get('MINIO_ROOT_USER', 'minio'))
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', os.environ.get('MINIO_ROOT_PASSWORD', 'minio123'))
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', 'http://minio:9000')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')

    # Options S3
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None  # Géré par classe de storage
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'path'  # MinIO utilise le style path
    AWS_QUERYSTRING_AUTH = True  # URLs signées par défaut
    AWS_S3_URL_PROTOCOL = 'http:'  # https: en production

    # URL publique pour accès externe (navigateur)
    # En production, utiliser l'URL externe de MinIO
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', None)

    # Durée des URLs signées (1 heure)
    AWS_QUERYSTRING_EXPIRE = 3600

    # Configuration STORAGES Django 4.2+
    STORAGES = {
        "default": {
            "BACKEND": "core.storage.PublicMediaStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# ============================================================================
# CLOUD STORAGE CONFIGURATION (Google Cloud Storage)
# ============================================================================
# Alternative à MinIO pour les instances hébergées sur GCP.
# Le stockage GCS (~10GB) est géré par le portail principal.

GCS_ENABLED = os.environ.get('GCS_ENABLED', 'False').lower() in ('true', '1', 'yes')

if GCS_ENABLED:
    from google.oauth2 import service_account

    # Backend de stockage GCS
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": os.environ.get('GCS_BUCKET_NAME', ''),
                "project_id": os.environ.get('GCS_PROJECT_ID', ''),
                "default_acl": "projectPrivate",
                "querystring_auth": True,
                "expiration": 3600,  # URLs signées valides 1h
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    # Credentials: fichier JSON ou variable d'environnement
    gcs_credentials_file = os.environ.get('GCS_CREDENTIALS_FILE', '/opt/altiusone/gcs-credentials.json')
    gcs_credentials_json = os.environ.get('GCS_CREDENTIALS_JSON', '')

    if gcs_credentials_json:
        # Credentials depuis variable d'environnement (pour containers)
        import json
        credentials_info = json.loads(gcs_credentials_json)
        GS_CREDENTIALS = service_account.Credentials.from_service_account_info(credentials_info)
    elif os.path.exists(gcs_credentials_file):
        # Credentials depuis fichier
        GS_CREDENTIALS = service_account.Credentials.from_service_account_file(gcs_credentials_file)

    # Paramètres supplémentaires GCS
    GS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', '')
    GS_PROJECT_ID = os.environ.get('GCS_PROJECT_ID', '')
    GS_DEFAULT_ACL = 'projectPrivate'
    GS_QUERYSTRING_AUTH = True
    GS_FILE_OVERWRITE = False  # Ne pas écraser les fichiers existants
    GS_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB avant écriture temporaire

    # Préfixe pour organiser les fichiers par instance
    GS_LOCATION = os.environ.get('GCS_LOCATION', 'media/')
else:
    # Stockage local en développement
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }


# ============================================================================
# ALTIUSONE AI SDK
# ============================================================================
# Service AI unifie pour OCR, Embeddings, Classification et Extraction.
# Utilise le SDK AltiusOne AI (https://pypi.org/project/altiusone-ai/)
#
# Configuration:
# - AI_API_URL: URL de l'API (https://ai.altiusone.ch)
# - AI_API_KEY: Cle API pour l'authentification
#
# Fonctionnalites:
# - OCR: Extraction de texte depuis images/PDFs
# - Embeddings: Vecteurs 768D pour recherche semantique (compatible PGVector)
# - Classification: Detection automatique du type de document
# - Extraction: Extraction structuree de donnees (factures, contrats, etc.)
# - Chat: Assistant conversationnel IA

AI_API_URL = os.environ.get('AI_API_URL', 'https://ai.altiusone.ch')
AI_API_KEY = os.environ.get('AI_API_KEY', '')

# Recherche hybride - ponderation des scores
SEARCH_FULLTEXT_WEIGHT = float(os.environ.get('SEARCH_FULLTEXT_WEIGHT', '0.4'))
SEARCH_SEMANTIC_WEIGHT = float(os.environ.get('SEARCH_SEMANTIC_WEIGHT', '0.6'))
SEARCH_SEMANTIC_THRESHOLD = float(os.environ.get('SEARCH_SEMANTIC_THRESHOLD', '0.5'))

# ============================================================================
# LEGACY - SERVICE OCR EXTERNE (DEPRECIE)
# ============================================================================
# Ces parametres sont conserves pour compatibilite mais ne sont plus utilises.
# Tout le traitement AI passe maintenant par le SDK AltiusOne AI.

OCR_SERVICE_ENABLED = False  # Deprecie - utiliser AI_API_KEY
OCR_SERVICE_URL = os.environ.get('OCR_SERVICE_URL', '')
OCR_SERVICE_API_KEY = os.environ.get('OCR_SERVICE_API_KEY', '')
OCR_SERVICE_TIMEOUT = int(os.environ.get('OCR_SERVICE_TIMEOUT', '60'))

# LEGACY - Configuration embeddings (DEPRECIE)
# Le SDK AltiusOne AI genere des embeddings 768D directement
EMBEDDING_BACKEND = 'altiusone'  # Fixe - utilise toujours le SDK
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')  # Non utilise
LOCAL_EMBEDDING_MODEL = ''  # Non utilise



# ============================================================================
# PROXY / SSL CONFIGURATION
# ============================================================================
# Nécessaire quand Django est derrière un reverse proxy qui termine SSL

# Indique à Django de faire confiance au header X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Utiliser le header X-Forwarded-Host pour request.get_host()
USE_X_FORWARDED_HOST = True

# En production, forcer HTTPS
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# ============================================================================
# DJANGO IMPORT-EXPORT CONFIGURATION
# ============================================================================
IMPORT_EXPORT_USE_TRANSACTIONS = True  # Rollback si erreur
IMPORT_EXPORT_SKIP_ADMIN_LOG = True  # On utilise notre propre AuditLog
IMPORT_EXPORT_IMPORT_PERMISSION_CODE = 'import'
IMPORT_EXPORT_EXPORT_PERMISSION_CODE = 'export'

# Formats supportés pour l'import/export
IMPORT_EXPORT_FORMATS = [
    'import_export.formats.base_formats.CSV',
    'import_export.formats.base_formats.XLSX',
]

# Taille maximale des fichiers d'import (10MB)
IMPORT_EXPORT_MAX_FILE_SIZE = 10 * 1024 * 1024


# ============================================================================
# ÉDITEUR COLLABORATIF (Docs - La Suite Numérique)
# ============================================================================
# Intégration de Docs (projet Franco-Allemand) pour l'édition collaborative
# en temps réel. Auto-hébergé pour une souveraineté totale.
#
# Architecture:
# - docs-api: Backend Django REST Framework (port 8072)
# - docs-frontend: Frontend Next.js (port 3000)
# - docs-collaboration: Serveur HocusPocus pour WebSocket (port 4444)
#
# Documentation: https://github.com/suitenumerique/docs

# URL du backend Docs (API)
DOCS_API_URL = os.environ.get('DOCS_API_URL', 'http://docs-api:8072')

# URL du frontend Docs (pour les iframes et redirections)
DOCS_FRONTEND_URL = os.environ.get('DOCS_FRONTEND_URL', 'http://localhost:3000')

# Clé API pour l'authentification admin (communication serveur à serveur)
DOCS_API_KEY = os.environ.get('DOCS_API_KEY', '')

# URL du serveur de collaboration WebSocket (HocusPocus)
DOCS_COLLABORATION_URL = os.environ.get('DOCS_COLLABORATION_URL', 'ws://docs-collaboration:4444')

# Secret partagé pour les webhooks Docs -> AltiusOne
DOCS_WEBHOOK_SECRET = os.environ.get('DOCS_WEBHOOK_SECRET', '')

# Configuration du stockage Docs (utilise Minio/S3)
DOCS_S3_BUCKET = os.environ.get('DOCS_S3_BUCKET', 'altiusone-docs')
DOCS_S3_ENDPOINT = os.environ.get('DOCS_S3_ENDPOINT', 'http://minio:9000')
DOCS_S3_ACCESS_KEY = os.environ.get('DOCS_S3_ACCESS_KEY', 'minio')
DOCS_S3_SECRET_KEY = os.environ.get('DOCS_S3_SECRET_KEY', 'minio123')


# ============================================================================
# OAUTH2 / OIDC PROVIDER (pour Docs et autres clients)
# ============================================================================
# AltiusOne agit comme fournisseur d'identité OIDC pour les applications
# tierces comme Docs (La Suite Numérique).
#
# Endpoints OIDC:
# - Authorization: /o/authorize/
# - Token: /o/token/
# - UserInfo: /o/userinfo/
# - JWKS: /o/jwks/

OAUTH2_PROVIDER = {
    # Durée de vie des tokens
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600,  # 1 heure
    'REFRESH_TOKEN_EXPIRE_SECONDS': 86400 * 7,  # 7 jours
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 600,  # 10 minutes

    # Scopes OIDC supportés
    'SCOPES': {
        'openid': 'OpenID Connect',
        'email': 'Accès à l\'email',
        'profile': 'Accès au profil',
        'read': 'Lecture des données',
        'write': 'Écriture des données',
    },

    # Utiliser OIDC
    'OIDC_ENABLED': True,
    'OIDC_ISS_ENDPOINT': os.environ.get('OIDC_ISSUER', 'http://localhost:8012'),
    # Clé RSA pour signer les ID tokens OIDC - lue depuis fichier ou env
    'OIDC_RSA_PRIVATE_KEY': (
        open(BASE_DIR / 'oidc_rsa_key.pem').read()
        if (BASE_DIR / 'oidc_rsa_key.pem').exists()
        else os.environ.get('OIDC_RSA_PRIVATE_KEY', '')
    ),

    # Backend OAuth2 - OAuthLibCore pour supporter form-urlencoded (standard OAuth2)
    # Note: JSONOAuthLibCore ne fonctionne qu'avec JSON, mais mozilla-django-oidc
    # envoie des requêtes en application/x-www-form-urlencoded
    'OAUTH2_BACKEND_CLASS': 'oauth2_provider.oauth2_backends.OAuthLibCore',

    # Validateur OAuth2/OIDC personnalisé avec claims utilisateur
    # Inclut email, name, etc. dans les réponses userinfo et id_token
    'OAUTH2_VALIDATOR_CLASS': 'AltiusOne.oidc_claims.AltiusOneOAuth2Validator',

    # Autoriser PKCE pour les apps mobiles/SPA
    'PKCE_REQUIRED': False,

    # Désactiver le hachage des secrets clients (défaut True depuis django-oauth-toolkit v2.x)
    # Nécessaire car Docs (mozilla-django-oidc) envoie le secret en clair pour l'échange de tokens
    # et la comparaison échoue si le secret est haché en base
    'HASH_CLIENT_SECRET': False,
}

# URL de login pour OAuth2 - utilise le login de l'app core (pas l'admin)
# LOGIN_URL est déjà défini plus haut comme "core:login"