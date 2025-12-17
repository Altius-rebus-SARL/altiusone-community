# documents/storage.py
"""
Service de stockage GCS pour les documents.
Cette application est une instance du portail principal avec un quota de ~10GB.
"""
import logging
import hashlib
from datetime import datetime
from typing import Optional, BinaryIO, Dict, Any
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service de gestion du stockage documents.
    Supporte GCS en production et stockage local en développement.
    """

    # Quota par défaut: 10GB (géré par le portail principal)
    DEFAULT_QUOTA_BYTES = 10 * 1024 * 1024 * 1024  # 10GB

    # Extensions autorisées par catégorie
    ALLOWED_EXTENSIONS = {
        'documents': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp'],
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.tiff', '.bmp'],
        'archives': ['.zip', '.tar', '.gz', '.rar', '.7z'],
        'text': ['.txt', '.csv', '.xml', '.json', '.html'],
    }

    # Taille maximale par fichier (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def __init__(self):
        self.storage = default_storage
        self.is_gcs = getattr(settings, 'GCS_ENABLED', False)
        self.location = getattr(settings, 'GS_LOCATION', 'media/')

    def generer_path(self, mandat_id: str, filename: str, date: Optional[datetime] = None) -> str:
        """
        Génère un chemin de stockage structuré.
        Format: {location}/{mandat_id}/{année}/{mois}/{hash_8chars}/{filename}
        """
        if date is None:
            date = datetime.now()

        # Hash basé sur le nom et timestamp pour unicité
        hash_input = f"{filename}{date.isoformat()}"
        hash_prefix = hashlib.sha256(hash_input.encode()).hexdigest()[:8]

        path = f"{self.location}{mandat_id}/{date.year}/{date.month:02d}/{hash_prefix}/{filename}"
        return path

    def calculer_hash_fichier(self, file_content: bytes) -> str:
        """Calcule le hash SHA-256 d'un fichier."""
        return hashlib.sha256(file_content).hexdigest()

    def valider_fichier(self, filename: str, file_size: int, content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Valide un fichier avant upload.
        Returns: dict avec 'valid' (bool) et 'errors' (list) si invalide.
        """
        errors = []
        import os
        ext = os.path.splitext(filename)[1].lower()

        # Vérifier extension
        all_extensions = []
        for exts in self.ALLOWED_EXTENSIONS.values():
            all_extensions.extend(exts)

        if ext not in all_extensions:
            errors.append(f"Extension '{ext}' non autorisée. Extensions permises: {', '.join(sorted(set(all_extensions)))}")

        # Vérifier taille
        if file_size > self.MAX_FILE_SIZE:
            errors.append(f"Fichier trop volumineux ({file_size / 1024 / 1024:.1f}MB). Maximum: {self.MAX_FILE_SIZE / 1024 / 1024:.0f}MB")

        if file_size == 0:
            errors.append("Le fichier est vide")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def upload_fichier(
        self,
        file_obj: BinaryIO,
        filename: str,
        mandat_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Upload un fichier vers le stockage.

        Args:
            file_obj: Objet fichier à uploader
            filename: Nom du fichier
            mandat_id: ID du mandat (pour l'organisation)
            metadata: Métadonnées optionnelles

        Returns:
            dict avec 'success', 'path', 'hash', 'size', 'url'
        """
        try:
            # Lire le contenu
            content = file_obj.read()
            file_size = len(content)

            # Valider
            validation = self.valider_fichier(filename, file_size)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors']
                }

            # Générer le chemin et hash
            path = self.generer_path(mandat_id, filename)
            file_hash = self.calculer_hash_fichier(content)

            # Sauvegarder
            saved_path = self.storage.save(path, ContentFile(content))

            # Générer URL
            url = self.storage.url(saved_path)

            logger.info(f"Fichier uploadé: {saved_path} ({file_size} bytes)")

            return {
                'success': True,
                'path': saved_path,
                'hash': file_hash,
                'size': file_size,
                'url': url,
                'storage_backend': 'gcs' if self.is_gcs else 'local'
            }

        except Exception as e:
            logger.error(f"Erreur upload fichier {filename}: {e}")
            return {
                'success': False,
                'errors': [str(e)]
            }

    def telecharger_fichier(self, path: str) -> Optional[bytes]:
        """
        Télécharge un fichier depuis le stockage.

        Args:
            path: Chemin du fichier

        Returns:
            Contenu du fichier en bytes, ou None si erreur
        """
        try:
            if not self.storage.exists(path):
                logger.warning(f"Fichier non trouvé: {path}")
                return None

            with self.storage.open(path, 'rb') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Erreur téléchargement {path}: {e}")
            return None

    def supprimer_fichier(self, path: str) -> bool:
        """
        Supprime un fichier du stockage.

        Args:
            path: Chemin du fichier

        Returns:
            True si supprimé, False sinon
        """
        try:
            if self.storage.exists(path):
                self.storage.delete(path)
                logger.info(f"Fichier supprimé: {path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur suppression {path}: {e}")
            return False

    def generer_url_signee(self, path: str, expiration: int = 3600) -> Optional[str]:
        """
        Génère une URL signée pour un fichier.

        Args:
            path: Chemin du fichier
            expiration: Durée de validité en secondes (défaut: 1h)

        Returns:
            URL signée ou None si erreur
        """
        try:
            if not self.storage.exists(path):
                return None

            if self.is_gcs:
                # GCS gère automatiquement les URLs signées via querystring_auth
                return self.storage.url(path)
            else:
                # Stockage local - retourner URL directe
                return self.storage.url(path)

        except Exception as e:
            logger.error(f"Erreur génération URL signée {path}: {e}")
            return None

    def get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un fichier.

        Returns:
            dict avec 'size', 'modified', 'url' ou None
        """
        try:
            if not self.storage.exists(path):
                return None

            return {
                'path': path,
                'size': self.storage.size(path),
                'url': self.storage.url(path),
                'exists': True
            }
        except Exception as e:
            logger.error(f"Erreur info fichier {path}: {e}")
            return None

    def copier_fichier(self, source_path: str, dest_mandat_id: str, new_filename: Optional[str] = None) -> Optional[str]:
        """
        Copie un fichier vers un nouveau chemin.

        Args:
            source_path: Chemin source
            dest_mandat_id: ID du mandat destination
            new_filename: Nouveau nom (optionnel)

        Returns:
            Nouveau chemin ou None si erreur
        """
        try:
            content = self.telecharger_fichier(source_path)
            if content is None:
                return None

            import os
            filename = new_filename or os.path.basename(source_path)
            dest_path = self.generer_path(dest_mandat_id, filename)

            saved_path = self.storage.save(dest_path, ContentFile(content))
            logger.info(f"Fichier copié: {source_path} -> {saved_path}")
            return saved_path

        except Exception as e:
            logger.error(f"Erreur copie {source_path}: {e}")
            return None


# Instance singleton
storage_service = StorageService()
