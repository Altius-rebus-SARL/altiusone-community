# core/storage.py
"""
Custom storage backends for S3/MinIO.

AltiusOne utilise MinIO comme backend S3-compatible pour:
- Les fichiers uploadés (documents, images, etc.)
- Le partage avec Nextcloud via External Storage

Configuration:
    USE_S3=true et variables AWS_* pour activer MinIO

Usage:
    from core.storage import DocumentStorage, PublicMediaStorage

    class Document(models.Model):
        fichier = models.FileField(storage=DocumentStorage())
"""

from django.conf import settings

# Détecter le backend à utiliser
USE_S3 = getattr(settings, 'USE_S3', False)


if USE_S3:
    from storages.backends.s3boto3 import S3Boto3Storage

    class S3DocumentStorage(S3Boto3Storage):
        """
        Storage pour les documents (privés, URLs signées).
        Accessible dans Nextcloud via External Storage.
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'documents'
        default_acl = 'private'
        file_overwrite = False
        querystring_auth = True  # URLs signées obligatoires

        object_parameters = {
            'CacheControl': 'private, max-age=0, no-cache',
        }

    class S3PublicMediaStorage(S3Boto3Storage):
        """
        Storage pour les médias publics (images, logos).
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'media'
        default_acl = 'public-read'
        file_overwrite = False
        querystring_auth = False  # Pas besoin de signature

        object_parameters = {
            'CacheControl': 'public, max-age=86400',  # 1 jour
        }

    class S3ProfileImageStorage(S3Boto3Storage):
        """
        Storage pour les photos de profil utilisateurs.
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'profiles'
        default_acl = 'public-read'
        file_overwrite = False
        querystring_auth = False

        object_parameters = {
            'CacheControl': 'public, max-age=3600',  # 1 heure
        }

    class S3InvoiceStorage(S3Boto3Storage):
        """
        Storage pour les factures PDF (privées).
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'factures'
        default_acl = 'private'
        file_overwrite = False
        querystring_auth = True

        object_parameters = {
            'CacheControl': 'private, no-cache',
            'ContentDisposition': 'attachment',
        }

    class S3SalairesStorage(S3Boto3Storage):
        """
        Storage pour les fiches de salaire et certificats (privés).
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'salaires'
        default_acl = 'private'
        file_overwrite = False
        querystring_auth = True

        object_parameters = {
            'CacheControl': 'private, no-cache',
        }

    class S3FiscaliteStorage(S3Boto3Storage):
        """
        Storage pour les documents fiscaux (privés).
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'fiscalite'
        default_acl = 'private'
        file_overwrite = False
        querystring_auth = True

        object_parameters = {
            'CacheControl': 'private, no-cache',
        }

    class S3ExportStorage(S3Boto3Storage):
        """
        Storage pour les exports et rapports (privés, téléchargement).
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'exports'
        default_acl = 'private'
        file_overwrite = False
        querystring_auth = True

        object_parameters = {
            'CacheControl': 'private, no-cache',
            'ContentDisposition': 'attachment',
        }

    class S3TVAStorage(S3Boto3Storage):
        """
        Storage pour les déclarations TVA (privées).
        """
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'altiusone-media')
        location = 'tva'
        default_acl = 'private'
        file_overwrite = False
        querystring_auth = True

        object_parameters = {
            'CacheControl': 'private, no-cache',
        }

    # Alias pour usage dans les models
    DocumentStorage = S3DocumentStorage
    PublicMediaStorage = S3PublicMediaStorage
    ProfileImageStorage = S3ProfileImageStorage
    InvoiceStorage = S3InvoiceStorage
    SalairesStorage = S3SalairesStorage
    FiscaliteStorage = S3FiscaliteStorage
    ExportStorage = S3ExportStorage
    TVAStorage = S3TVAStorage

else:
    # Stockage local (développement ou si S3 non configuré)
    from django.core.files.storage import FileSystemStorage

    class LocalStorage(FileSystemStorage):
        """Stockage local pour le développement."""
        def __init__(self, location=None, base_url=None):
            location = location or getattr(settings, 'MEDIA_ROOT', '')
            base_url = base_url or getattr(settings, 'MEDIA_URL', '/media/')
            super().__init__(location=location, base_url=base_url)

    # Tous les storages utilisent le filesystem local
    DocumentStorage = LocalStorage
    PublicMediaStorage = LocalStorage
    ProfileImageStorage = LocalStorage
    InvoiceStorage = LocalStorage
    SalairesStorage = LocalStorage
    FiscaliteStorage = LocalStorage
    ExportStorage = LocalStorage
    TVAStorage = LocalStorage


def get_storage_backend(storage_type='document'):
    """
    Retourne le backend de stockage approprié.

    Args:
        storage_type: 'document', 'public', 'profile', 'invoice',
                      'salaires', 'fiscalite', 'export', 'tva'

    Returns:
        Instance du storage backend
    """
    storage_map = {
        'document': DocumentStorage,
        'public': PublicMediaStorage,
        'profile': ProfileImageStorage,
        'invoice': InvoiceStorage,
        'salaires': SalairesStorage,
        'fiscalite': FiscaliteStorage,
        'export': ExportStorage,
        'tva': TVAStorage,
    }

    storage_class = storage_map.get(storage_type, DocumentStorage)
    return storage_class()


def get_storage_info():
    """
    Retourne des informations sur la configuration de stockage actuelle.
    Utile pour le debug et les pages de statut.
    """
    if USE_S3:
        return {
            'backend': 'S3/MinIO',
            'bucket': getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'N/A'),
            'endpoint': getattr(settings, 'AWS_S3_ENDPOINT_URL', 'AWS Default'),
            'region': getattr(settings, 'AWS_S3_REGION_NAME', 'N/A'),
        }
    else:
        return {
            'backend': 'Local Filesystem',
            'media_root': getattr(settings, 'MEDIA_ROOT', 'N/A'),
            'media_url': getattr(settings, 'MEDIA_URL', 'N/A'),
        }
