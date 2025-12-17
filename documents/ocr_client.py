# documents/ocr_client.py
"""
Client pour le service OCR externe.

L'OCR est géré par un service Django séparé avec PGVector.
Ce client permet d'envoyer des documents et de récupérer les résultats.
"""
import logging
import requests
from typing import Optional, Dict, Any, List
from django.conf import settings

logger = logging.getLogger(__name__)


class OCRServiceError(Exception):
    """Exception pour les erreurs du service OCR."""
    pass


class OCRClient:
    """
    Client pour communiquer avec le service OCR externe.

    Le service OCR est une application Django séparée qui gère:
    - Extraction de texte (OCR)
    - Classification de documents via LLM
    - Extraction de métadonnées structurées
    - Embeddings vectoriels (PGVector) pour la recherche sémantique
    """

    def __init__(self):
        self.base_url = getattr(settings, 'OCR_SERVICE_URL', 'http://ocr-service:8000')
        self.api_key = getattr(settings, 'OCR_SERVICE_API_KEY', '')
        self.timeout = getattr(settings, 'OCR_SERVICE_TIMEOUT', 60)
        self.enabled = getattr(settings, 'OCR_SERVICE_ENABLED', False)

    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers pour les requêtes API."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Effectue une requête vers le service OCR.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Endpoint de l'API (ex: /api/ocr/extract)
            data: Données JSON à envoyer
            files: Fichiers à uploader
            timeout: Timeout personnalisé

        Returns:
            Réponse JSON du service

        Raises:
            OCRServiceError: Si la requête échoue
        """
        if not self.enabled:
            raise OCRServiceError("Service OCR non activé")

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        timeout = timeout or self.timeout

        try:
            headers = self._get_headers()

            if files:
                # Multipart pour upload de fichiers
                headers.pop('Content-Type', None)
                response = requests.request(
                    method,
                    url,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=timeout
                )
            else:
                response = requests.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                    timeout=timeout
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Timeout OCR service: {url}")
            raise OCRServiceError(f"Le service OCR n'a pas répondu dans les {timeout}s")

        except requests.exceptions.ConnectionError:
            logger.error(f"Connexion impossible au service OCR: {url}")
            raise OCRServiceError("Impossible de se connecter au service OCR")

        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP OCR service: {e.response.status_code} - {e.response.text}")
            raise OCRServiceError(f"Erreur service OCR: {e.response.status_code}")

        except Exception as e:
            logger.error(f"Erreur inattendue OCR service: {e}")
            raise OCRServiceError(f"Erreur inattendue: {str(e)}")

    def health_check(self) -> bool:
        """
        Vérifie si le service OCR est disponible.

        Returns:
            True si le service répond, False sinon
        """
        try:
            result = self._make_request('GET', '/api/health/', timeout=5)
            return result.get('status') == 'ok'
        except OCRServiceError:
            return False

    def extraire_texte(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extrait le texte d'un document via OCR.

        Args:
            file_content: Contenu du fichier en bytes
            filename: Nom du fichier
            mime_type: Type MIME du fichier
            options: Options OCR (langue, dpi, etc.)

        Returns:
            dict avec:
            - text: Texte extrait
            - confidence: Score de confiance (0-100)
            - pages: Nombre de pages traitées
            - language: Langue détectée
        """
        files = {
            'file': (filename, file_content, mime_type)
        }
        data = options or {}

        result = self._make_request('POST', '/api/ocr/extract/', data=data, files=files)

        return {
            'text': result.get('text', ''),
            'confidence': result.get('confidence', 0),
            'pages': result.get('pages', 1),
            'language': result.get('language', 'fr'),
            'processing_time': result.get('processing_time', 0)
        }

    def classifier_document(
        self,
        text: str,
        filename: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Classifie un document via LLM.

        Args:
            text: Texte du document (extrait par OCR)
            filename: Nom du fichier (indice pour classification)
            metadata: Métadonnées additionnelles

        Returns:
            dict avec:
            - type_document: Type prédit (FACTURE_ACHAT, RELEVE_BANQUE, etc.)
            - confidence: Score de confiance (0-1)
            - categories: Liste de catégories possibles
            - tags: Tags suggérés
        """
        data = {
            'text': text,
            'filename': filename,
            'metadata': metadata or {}
        }

        result = self._make_request('POST', '/api/ocr/classify/', data=data)

        return {
            'type_document': result.get('type_document', 'AUTRE'),
            'confidence': result.get('confidence', 0),
            'categories': result.get('categories', []),
            'tags': result.get('tags', [])
        }

    def extraire_metadonnees(
        self,
        text: str,
        type_document: str,
        template: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extrait les métadonnées structurées d'un document.

        Args:
            text: Texte du document
            type_document: Type de document (pour adapter l'extraction)
            template: Template d'extraction personnalisé

        Returns:
            dict avec les métadonnées extraites selon le type:
            - Pour factures: montant_ht, montant_tva, montant_ttc, numero_facture,
                            date_facture, fournisseur, iban, etc.
            - Pour relevés bancaires: solde, mouvements, etc.
            - Pour contrats: parties, date_debut, date_fin, etc.
        """
        data = {
            'text': text,
            'type_document': type_document,
            'template': template
        }

        result = self._make_request('POST', '/api/ocr/extract-metadata/', data=data)

        return result.get('metadata', {})

    def generer_embedding(self, text: str, document_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Génère un embedding vectoriel pour la recherche sémantique.

        Args:
            text: Texte à vectoriser
            document_id: ID du document (pour stockage dans PGVector)

        Returns:
            dict avec:
            - embedding: Vecteur (liste de floats)
            - dimensions: Nombre de dimensions
            - model: Modèle utilisé
        """
        data = {
            'text': text,
            'document_id': document_id
        }

        result = self._make_request('POST', '/api/ocr/embed/', data=data)

        return {
            'embedding': result.get('embedding', []),
            'dimensions': result.get('dimensions', 0),
            'model': result.get('model', '')
        }

    def recherche_semantique(
        self,
        query: str,
        mandat_id: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique dans les documents.

        Args:
            query: Requête de recherche
            mandat_id: Filtrer par mandat
            limit: Nombre max de résultats
            threshold: Seuil de similarité (0-1)

        Returns:
            Liste de documents correspondants avec score de similarité
        """
        data = {
            'query': query,
            'mandat_id': mandat_id,
            'limit': limit,
            'threshold': threshold
        }

        result = self._make_request('POST', '/api/ocr/search/', data=data)

        return result.get('results', [])

    def traiter_document_complet(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        mandat_id: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Traitement complet d'un document:
        1. Extraction OCR
        2. Classification
        3. Extraction métadonnées
        4. Génération embedding

        Args:
            file_content: Contenu du fichier
            filename: Nom du fichier
            mime_type: Type MIME
            mandat_id: ID du mandat
            options: Options de traitement

        Returns:
            dict avec tous les résultats du traitement
        """
        files = {
            'file': (filename, file_content, mime_type)
        }
        data = {
            'mandat_id': mandat_id,
            'options': options or {}
        }

        # Timeout plus long pour traitement complet
        result = self._make_request(
            'POST',
            '/api/ocr/process/',
            data=data,
            files=files,
            timeout=120
        )

        return {
            'ocr': {
                'text': result.get('text', ''),
                'confidence': result.get('ocr_confidence', 0),
                'pages': result.get('pages', 1)
            },
            'classification': {
                'type_document': result.get('type_document', 'AUTRE'),
                'confidence': result.get('classification_confidence', 0),
                'tags': result.get('tags', [])
            },
            'metadata': result.get('metadata', {}),
            'embedding_stored': result.get('embedding_stored', False),
            'processing_time': result.get('processing_time', 0)
        }


# Instance singleton
ocr_client = OCRClient()


def traiter_document_async(document_id: str) -> None:
    """
    Tâche Celery pour traiter un document de manière asynchrone.

    Args:
        document_id: ID du document à traiter
    """
    from documents.models import Document, TraitementDocument
    from documents.storage import storage_service
    from django.utils import timezone

    try:
        document = Document.objects.get(id=document_id)

        # Créer un enregistrement de traitement
        traitement = TraitementDocument.objects.create(
            document=document,
            type_traitement='OCR',
            statut='EN_COURS',
            moteur='Service OCR externe'
        )

        # Télécharger le fichier
        content = storage_service.telecharger_fichier(document.path_storage)
        if content is None:
            traitement.statut = 'ERREUR'
            traitement.erreur = "Impossible de télécharger le fichier"
            traitement.save()
            return

        # Traitement complet
        result = ocr_client.traiter_document_complet(
            file_content=content,
            filename=document.nom_fichier,
            mime_type=document.mime_type,
            mandat_id=str(document.mandat_id)
        )

        # Mettre à jour le document
        document.ocr_text = result['ocr']['text']
        document.ocr_confidence = result['ocr']['confidence']
        document.prediction_type = result['classification']['type_document']
        document.prediction_confidence = result['classification']['confidence']
        document.tags_auto = result['classification']['tags']
        document.metadata_extraite = result['metadata']
        document.statut_traitement = 'OCR_TERMINE'
        document.save()

        # Mettre à jour le traitement
        traitement.statut = 'TERMINE'
        traitement.date_fin = timezone.now()
        traitement.resultat = result
        traitement.duree_secondes = int(result.get('processing_time', 0))
        traitement.save()

        logger.info(f"Document {document_id} traité avec succès")

    except Document.DoesNotExist:
        logger.error(f"Document {document_id} non trouvé")

    except OCRServiceError as e:
        logger.error(f"Erreur OCR pour document {document_id}: {e}")
        if 'traitement' in locals():
            traitement.statut = 'ERREUR'
            traitement.erreur = str(e)
            traitement.date_fin = timezone.now()
            traitement.save()

        document.statut_traitement = 'ERREUR'
        document.save()

    except Exception as e:
        logger.error(f"Erreur inattendue traitement document {document_id}: {e}")
