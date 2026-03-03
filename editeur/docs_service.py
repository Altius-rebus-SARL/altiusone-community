"""
Service d'intégration avec Docs (La Suite Numérique).

Gère la communication avec l'API Docs pour :
- Création/modification de documents
- Synchronisation des utilisateurs
- Gestion des sessions collaboratives
- Export de documents
"""

import logging
import requests
import hashlib
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()


@dataclass
class DocsDocument:
    """Représentation d'un document Docs."""
    id: str
    title: str
    content: Dict[str, Any]
    created_at: str
    updated_at: str
    owner_id: str
    collaborators: List[str]


@dataclass
class DocsUser:
    """Représentation d'un utilisateur Docs."""
    id: str
    email: str
    name: str


class DocsServiceError(Exception):
    """Erreur du service Docs."""
    pass


class DocsService:
    """
    Service pour interagir avec l'instance Docs auto-hébergée.

    Configuration requise dans settings.py:
    - DOCS_API_URL: URL de l'API Docs (ex: http://docs-api:8000)
    - DOCS_API_KEY: Clé API pour l'authentification admin
    - DOCS_FRONTEND_URL: URL du frontend (ex: http://docs:3000)
    """

    def __init__(self):
        self.api_url = getattr(settings, 'DOCS_API_URL', 'http://docs-api:8072')
        self.api_key = getattr(settings, 'DOCS_API_KEY', '')
        self.frontend_url = getattr(settings, 'DOCS_FRONTEND_URL', 'http://localhost:3000')
        self.timeout = 30

    def _get_headers(self, user_token: Optional[str] = None) -> Dict[str, str]:
        """Génère les headers pour les requêtes API."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        if user_token:
            headers['Authorization'] = f'Bearer {user_token}'
        elif self.api_key:
            headers['X-API-Key'] = self.api_key

        return headers

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        user_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Effectue une requête à l'API Docs."""
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers(user_token)

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Timeout lors de l'appel à Docs: {url}")
            raise DocsServiceError("Le service Docs ne répond pas")

        except requests.exceptions.ConnectionError:
            logger.error(f"Impossible de se connecter à Docs: {url}")
            raise DocsServiceError("Impossible de se connecter au service Docs")

        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP Docs: {e.response.status_code} - {e.response.text}")
            raise DocsServiceError(f"Erreur Docs: {e.response.status_code}")

        except Exception as e:
            logger.exception(f"Erreur inattendue Docs: {e}")
            raise DocsServiceError(f"Erreur inattendue: {str(e)}")

    # =========================================================================
    # Gestion des documents
    # =========================================================================

    def create_document(
        self,
        title: str,
        user: User,
        content: Optional[Dict] = None,
        template_id: Optional[str] = None
    ) -> DocsDocument:
        """
        Crée un nouveau document dans Docs.

        Args:
            title: Titre du document
            user: Utilisateur AltiusOne créateur
            content: Contenu initial (format BlockNote JSON)
            template_id: ID du template Docs à utiliser

        Returns:
            DocsDocument: Le document créé
        """
        # S'assurer que l'utilisateur existe dans Docs
        docs_user = self.sync_user(user)

        data = {
            'title': title,
            'owner_id': docs_user.id,
        }

        if content:
            data['content'] = content

        if template_id:
            data['template_id'] = template_id

        result = self._request('POST', '/api/v1/documents/', data)

        logger.info(f"Document créé dans Docs: {result.get('id')} - {title}")

        return DocsDocument(
            id=result['id'],
            title=result['title'],
            content=result.get('content', {}),
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            owner_id=result['owner_id'],
            collaborators=result.get('collaborators', [])
        )

    def get_document(self, docs_id: str, user_token: Optional[str] = None) -> DocsDocument:
        """Récupère un document depuis Docs."""
        result = self._request('GET', f'/api/v1/documents/{docs_id}/', user_token=user_token)

        return DocsDocument(
            id=result['id'],
            title=result['title'],
            content=result.get('content', {}),
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            owner_id=result['owner_id'],
            collaborators=result.get('collaborators', [])
        )

    def update_document(
        self,
        docs_id: str,
        title: Optional[str] = None,
        content: Optional[Dict] = None,
        user_token: Optional[str] = None
    ) -> DocsDocument:
        """Met à jour un document dans Docs."""
        data = {}
        if title:
            data['title'] = title
        if content:
            data['content'] = content

        result = self._request(
            'PATCH',
            f'/api/v1/documents/{docs_id}/',
            data,
            user_token=user_token
        )

        return DocsDocument(
            id=result['id'],
            title=result['title'],
            content=result.get('content', {}),
            created_at=result['created_at'],
            updated_at=result['updated_at'],
            owner_id=result['owner_id'],
            collaborators=result.get('collaborators', [])
        )

    def delete_document(self, docs_id: str) -> bool:
        """Supprime un document de Docs."""
        self._request('DELETE', f'/api/v1/documents/{docs_id}/')
        logger.info(f"Document supprimé de Docs: {docs_id}")
        return True

    # =========================================================================
    # Gestion des collaborateurs
    # =========================================================================

    def add_collaborator(
        self,
        docs_id: str,
        user: User,
        permission: str = 'edit'
    ) -> bool:
        """
        Ajoute un collaborateur à un document.

        Args:
            docs_id: ID du document Docs
            user: Utilisateur AltiusOne à ajouter
            permission: 'view', 'comment', 'edit', 'admin'
        """
        docs_user = self.sync_user(user)

        data = {
            'user_id': docs_user.id,
            'permission': permission
        }

        self._request('POST', f'/api/v1/documents/{docs_id}/collaborators/', data)
        logger.info(f"Collaborateur ajouté: {user.email} sur {docs_id}")
        return True

    def remove_collaborator(self, docs_id: str, user: User) -> bool:
        """Retire un collaborateur d'un document."""
        # Récupérer l'ID Docs de l'utilisateur
        docs_user_id = self._get_docs_user_id(user)
        if not docs_user_id:
            return False

        self._request('DELETE', f'/api/v1/documents/{docs_id}/collaborators/{docs_user_id}/')
        logger.info(f"Collaborateur retiré: {user.email} de {docs_id}")
        return True

    def list_collaborators(self, docs_id: str) -> List[Dict[str, Any]]:
        """Liste les collaborateurs d'un document."""
        result = self._request('GET', f'/api/v1/documents/{docs_id}/collaborators/')
        return result.get('collaborators', [])

    # =========================================================================
    # Synchronisation des utilisateurs
    # =========================================================================

    def sync_user(self, user: User) -> DocsUser:
        """
        Synchronise un utilisateur AltiusOne avec Docs.

        Crée l'utilisateur s'il n'existe pas, ou le met à jour.
        """
        # Identifiant unique basé sur l'email
        external_id = f"altiusone_{user.id}"

        data = {
            'external_id': external_id,
            'email': user.email,
            'name': user.get_full_name() or user.email,
            'language': getattr(user, 'langue', 'fr') or 'fr',
        }

        try:
            # Essayer de récupérer l'utilisateur existant
            result = self._request('GET', f'/api/v1/users/external/{external_id}/')
            docs_user_id = result['id']

            # Mettre à jour si nécessaire
            self._request('PATCH', f'/api/v1/users/{docs_user_id}/', data)

        except DocsServiceError:
            # L'utilisateur n'existe pas, le créer
            result = self._request('POST', '/api/v1/users/', data)
            docs_user_id = result['id']

        return DocsUser(
            id=docs_user_id,
            email=user.email,
            name=user.get_full_name() or user.email
        )

    def _get_docs_user_id(self, user: User) -> Optional[str]:
        """Récupère l'ID Docs d'un utilisateur AltiusOne."""
        external_id = f"altiusone_{user.id}"
        try:
            result = self._request('GET', f'/api/v1/users/external/{external_id}/')
            return result['id']
        except DocsServiceError:
            return None

    # =========================================================================
    # Export de documents
    # =========================================================================

    def export_document(
        self,
        docs_id: str,
        format: str = 'pdf',
        user_token: Optional[str] = None
    ) -> bytes:
        """
        Exporte un document dans le format spécifié.

        Args:
            docs_id: ID du document Docs
            format: 'pdf', 'docx', 'odt', 'html', 'md'
            user_token: Token JWT de l'utilisateur

        Returns:
            bytes: Contenu du fichier exporté
        """
        url = f"{self.api_url}/api/v1/documents/{docs_id}/export/"
        headers = self._get_headers(user_token)
        headers['Accept'] = 'application/octet-stream'

        try:
            response = requests.get(
                url,
                headers=headers,
                params={'format': format},
                timeout=60  # Export peut prendre du temps
            )
            response.raise_for_status()
            return response.content

        except Exception as e:
            logger.error(f"Erreur export Docs: {e}")
            raise DocsServiceError(f"Erreur lors de l'export: {str(e)}")

    # =========================================================================
    # Génération de tokens pour l'édition
    # =========================================================================

    def generate_edit_token(self, user: User, docs_id: str, expires_in: int = 3600) -> str:
        """
        Génère un token JWT pour l'édition d'un document.

        Ce token est utilisé pour authentifier l'utilisateur
        dans l'interface Docs (iframe).
        """
        # S'assurer que l'utilisateur existe dans Docs
        docs_user = self.sync_user(user)

        data = {
            'user_id': docs_user.id,
            'document_id': docs_id,
            'permissions': ['read', 'write'],
            'expires_in': expires_in
        }

        result = self._request('POST', '/api/v1/auth/document-token/', data)
        return result['token']

    def generate_readonly_token(self, docs_id: str, expires_in: int = 3600) -> str:
        """Génère un token en lecture seule pour un document."""
        data = {
            'document_id': docs_id,
            'permissions': ['read'],
            'expires_in': expires_in
        }

        result = self._request('POST', '/api/v1/auth/document-token/', data)
        return result['token']

    # =========================================================================
    # Santé du service
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """Vérifie l'état du service Docs."""
        try:
            result = self._request('GET', '/api/v1/health/')
            return {
                'status': 'healthy',
                'docs_version': result.get('version', 'unknown'),
                'api_url': self.api_url,
                'frontend_url': self.frontend_url
            }
        except DocsServiceError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'api_url': self.api_url
            }

    # =========================================================================
    # URLs pour l'interface
    # =========================================================================

    def get_editor_url(self, docs_id: str, token: Optional[str] = None) -> str:
        """
        Génère l'URL pour ouvrir l'éditeur Docs.

        Args:
            docs_id: ID du document
            token: Token d'accès (optionnel, sera ajouté si fourni)
        """
        url = f"{self.frontend_url}/docs/{docs_id}"
        if token:
            url += f"?token={token}"
        return url

    def get_embed_url(self, docs_id: str, token: str, readonly: bool = False) -> str:
        """
        Génère l'URL pour intégrer l'éditeur en iframe.

        Args:
            docs_id: ID du document
            token: Token d'accès
            readonly: Mode lecture seule
        """
        mode = 'view' if readonly else 'edit'
        return f"{self.frontend_url}/embed/{docs_id}?token={token}&mode={mode}"


# Instance singleton
docs_service = DocsService()
