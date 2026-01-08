# documents/ai_service.py
"""
Service AI unifie utilisant l'API AltiusOne AI.

Ce service centralise toutes les operations AI:
- OCR (extraction de texte depuis images/PDFs)
- Embeddings (vecteurs 768D pour recherche semantique)
- Extraction structuree (factures, contrats, etc.)
- Chat IA (assistant conversationnel)

Configuration via .env:
- AI_API_KEY: Cle API AltiusOne
- AI_API_URL: URL de l'API (https://ai.altiusone.ch)

Endpoints API (sans prefixe /api/):
- POST /embeddings - Generation d'embeddings 768D
- POST /ocr - OCR sur images/PDF (base64 ou URL)
- POST /ocr/file - OCR sur fichier uploade
- POST /chat - Chat avec le LLM
- POST /extract - Extraction structuree
- GET /health - Health check
"""
import logging
import hashlib
import base64
import requests
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Resultat d'extraction OCR."""
    text: str
    confidence: float = 0.0
    pages: int = 1
    language: str = 'fr'
    processing_time: float = 0.0


@dataclass
class ClassificationResult:
    """Resultat de classification de document."""
    type_document: str
    confidence: float
    categories: List[str]
    tags: List[str]


@dataclass
class ExtractionResult:
    """Resultat d'extraction de metadonnees."""
    data: Dict[str, Any]
    confidence: float = 0.0


class AIServiceError(Exception):
    """Exception pour les erreurs du service AI."""
    pass


class AltiusAIService:
    """
    Service unifie pour toutes les operations AI via le SDK AltiusOne.

    Utilise l'API AltiusOne AI pour:
    - OCR intelligent
    - Generation d'embeddings 768D
    - Extraction de donnees structurees
    - Chat IA contextuel
    """

    # Schemas d'extraction predefinies
    EXTRACTION_SCHEMAS = {
        'FACTURE_ACHAT': {
            'numero_facture': 'string',
            'date_facture': 'string',
            'date_echeance': 'string',
            'fournisseur': {
                'nom': 'string',
                'adresse': 'string',
                'numero_tva': 'string',
                'iban': 'string'
            },
            'montant_ht': 'number',
            'montant_tva': 'number',
            'taux_tva': 'number',
            'montant_ttc': 'number',
            'devise': 'string',
            'reference_client': 'string'
        },
        'FACTURE_VENTE': {
            'numero_facture': 'string',
            'date_facture': 'string',
            'date_echeance': 'string',
            'client': {
                'nom': 'string',
                'adresse': 'string',
                'numero_tva': 'string'
            },
            'montant_ht': 'number',
            'montant_tva': 'number',
            'taux_tva': 'number',
            'montant_ttc': 'number',
            'devise': 'string'
        },
        'RELEVE_BANQUE': {
            'banque': 'string',
            'numero_compte': 'string',
            'iban': 'string',
            'periode_debut': 'string',
            'periode_fin': 'string',
            'solde_initial': 'number',
            'solde_final': 'number',
            'devise': 'string',
            'nombre_operations': 'number'
        },
        'CONTRAT': {
            'type_contrat': 'string',
            'parties': [{'nom': 'string', 'role': 'string'}],
            'date_signature': 'string',
            'date_debut': 'string',
            'date_fin': 'string',
            'montant': 'number',
            'devise': 'string',
            'objet': 'string'
        },
        'FICHE_SALAIRE': {
            'employe': {
                'nom': 'string',
                'prenom': 'string',
                'numero_avs': 'string'
            },
            'employeur': 'string',
            'periode': 'string',
            'salaire_brut': 'number',
            'deductions': 'number',
            'salaire_net': 'number',
            'devise': 'string'
        },
        'DEVIS': {
            'numero_devis': 'string',
            'date_devis': 'string',
            'validite': 'string',
            'client': {
                'nom': 'string',
                'adresse': 'string'
            },
            'montant_ht': 'number',
            'montant_tva': 'number',
            'montant_ttc': 'number',
            'devise': 'string'
        }
    }

    # Mapping types de documents vers categories
    TYPE_TO_CATEGORY = {
        'FACTURE_ACHAT': 'Comptabilite',
        'FACTURE_VENTE': 'Comptabilite',
        'RELEVE_BANQUE': 'Banque',
        'CONTRAT': 'Juridique',
        'FICHE_SALAIRE': 'RH',
        'CERTIFICAT_SALAIRE': 'RH',
        'DECLARATION_TVA': 'Fiscal',
        'DEVIS': 'Commercial',
        'BON_COMMANDE': 'Commercial',
        'BON_LIVRAISON': 'Logistique',
        'ATTESTATION': 'Administratif',
        'COURRIER': 'Correspondance',
        'EMAIL': 'Correspondance',
        'AUTRE': 'Divers'
    }

    def __init__(self):
        self.api_url = getattr(settings, 'AI_API_URL', 'https://ai.altiusone.ch').rstrip('/')
        self.api_key = getattr(settings, 'AI_API_KEY', '')
        self.timeout = 120  # Timeout pour les requetes longues (OCR, etc.)

    @property
    def enabled(self) -> bool:
        """Verifie si le service AI est configure."""
        return bool(self.api_key and self.api_url)

    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers pour les requetes API."""
        return {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Effectue une requete vers l'API AltiusOne AI.

        Args:
            method: HTTP method (GET, POST)
            endpoint: Endpoint (ex: /embeddings, /ocr, /chat)
            json_data: Donnees JSON a envoyer
            files: Fichiers a uploader (multipart)
            timeout: Timeout personnalise

        Returns:
            Reponse JSON de l'API

        Raises:
            AIServiceError: Si la requete echoue
        """
        if not self.enabled:
            raise AIServiceError("Service AI non configure. Verifiez AI_API_KEY et AI_API_URL dans .env")

        url = f"{self.api_url}{endpoint}"
        timeout = timeout or self.timeout

        try:
            headers = self._get_headers()

            if files:
                # Multipart pour upload de fichiers - pas de Content-Type (requests le gere)
                headers.pop('Content-Type', None)
                response = requests.request(
                    method,
                    url,
                    data=json_data,
                    files=files,
                    headers=headers,
                    timeout=timeout
                )
            else:
                response = requests.request(
                    method,
                    url,
                    json=json_data,
                    headers=headers,
                    timeout=timeout
                )

            # Log pour debug
            if response.status_code != 200:
                logger.error(f"API Error {response.status_code}: {response.text[:500]}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Timeout API: {url}")
            raise AIServiceError(f"L'API n'a pas repondu dans les {timeout}s")

        except requests.exceptions.ConnectionError:
            logger.error(f"Connexion impossible: {url}")
            raise AIServiceError(f"Impossible de se connecter a {self.api_url}")

        except requests.exceptions.HTTPError as e:
            error_msg = f"Erreur HTTP {e.response.status_code}"
            try:
                error_detail = e.response.json().get('detail', e.response.text)
                error_msg = f"{error_msg}: {error_detail}"
            except Exception:
                error_msg = f"{error_msg}: {e.response.text[:200]}"
            logger.error(error_msg)
            raise AIServiceError(error_msg)

        except Exception as e:
            logger.error(f"Erreur inattendue API: {e}")
            raise AIServiceError(f"Erreur inattendue: {str(e)}")

    # =========================================================================
    # OCR - EXTRACTION DE TEXTE
    # =========================================================================

    def ocr(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_url: Optional[str] = None,
        language: str = 'auto'
    ) -> OCRResult:
        """
        Extrait le texte d'un document (image ou PDF).

        Args:
            file_path: Chemin vers le fichier local
            file_content: Contenu du fichier en bytes
            file_url: URL du fichier
            language: Langue du document (auto, fr, de, en, it)

        Returns:
            OCRResult avec le texte extrait et metadonnees
        """
        try:
            if file_path:
                # Lire le fichier et l'encoder en base64
                with open(file_path, 'rb') as f:
                    file_content = f.read()

            if file_content:
                # Methode 1: Upload multipart via /ocr/file
                import mimetypes
                filename = file_path.split('/')[-1] if file_path else 'document'
                mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

                files = {'file': (filename, file_content, mime_type)}
                params = {'language': language} if language != 'auto' else {}

                # Utiliser /ocr/file pour upload multipart
                response = self._make_request(
                    'POST',
                    '/ocr/file',
                    json_data=params,
                    files=files
                )

            elif file_url:
                # Methode 2: Envoyer URL via /ocr
                response = self._make_request(
                    'POST',
                    '/ocr',
                    json_data={
                        'image_url': file_url,
                        'language': language
                    }
                )
            else:
                raise AIServiceError("Aucune source de fichier fournie")

            return OCRResult(
                text=response.get('text', ''),
                confidence=response.get('confidence', 95.0),
                pages=response.get('pages', 1),
                language=response.get('detected_language', language if language != 'auto' else 'fr'),
                processing_time=response.get('processing_time', 0)
            )

        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Erreur OCR: {e}")
            raise AIServiceError(f"Erreur lors de l'extraction OCR: {str(e)}")

    # =========================================================================
    # EMBEDDINGS - VECTORISATION
    # =========================================================================

    def embed(self, text: str) -> List[float]:
        """
        Genere un embedding 768D pour un texte.

        Args:
            text: Texte a vectoriser

        Returns:
            Liste de 768 floats representant le vecteur
        """
        if not text or not text.strip():
            raise AIServiceError("Texte vide fourni pour l'embedding")

        # Tronquer si trop long (limite API)
        text = text[:30000]

        try:
            response = self._make_request(
                'POST',
                '/embeddings',
                json_data={'text': text}
            )

            embeddings = response.get('embeddings', [])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]

            # Fallback si format different
            if 'embedding' in response:
                return response['embedding']

            raise AIServiceError("Aucun embedding retourne par l'API")

        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Erreur generation embedding: {e}")
            raise AIServiceError(f"Erreur lors de la generation de l'embedding: {str(e)}")

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Genere des embeddings pour plusieurs textes.

        Args:
            texts: Liste de textes a vectoriser

        Returns:
            Liste d'embeddings (ou None pour les textes vides)
        """
        if not texts:
            return []

        results = []
        for text in texts:
            if text and text.strip():
                try:
                    embedding = self.embed(text)
                    results.append(embedding)
                except AIServiceError:
                    results.append(None)
            else:
                results.append(None)

        return results

    @property
    def embedding_dimensions(self) -> int:
        """Retourne le nombre de dimensions des embeddings (768)."""
        return 768

    # =========================================================================
    # CLASSIFICATION DE DOCUMENTS
    # =========================================================================

    def classify_document(
        self,
        text: str,
        filename: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classifie automatiquement un document en utilisant le Chat IA.

        Args:
            text: Texte du document (extrait par OCR)
            filename: Nom du fichier (optionnel, aide a la classification)

        Returns:
            ClassificationResult avec type, confiance et tags
        """
        # Construire le prompt de classification
        types_disponibles = list(self.EXTRACTION_SCHEMAS.keys()) + ['ATTESTATION', 'COURRIER', 'EMAIL', 'AUTRE']

        system_prompt = f"""Tu es un assistant specialise dans la classification de documents professionnels suisses.
Analyse le document et determine son type parmi: {', '.join(types_disponibles)}.
Reponds UNIQUEMENT en JSON avec le format:
{{"type_document": "TYPE", "confidence": 0.95, "tags": ["tag1", "tag2"], "raison": "explication"}}"""

        user_prompt = f"""Classifie ce document:
Nom fichier: {filename or 'inconnu'}
Contenu (extrait):
{text[:3000]}"""

        try:
            response = self.chat(message=user_prompt, system=system_prompt)

            # Parser la reponse JSON
            import json
            try:
                # Essayer de trouver le JSON dans la reponse
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(response[json_start:json_end])
                else:
                    result = json.loads(response)
            except json.JSONDecodeError:
                # Fallback si pas de JSON valide
                result = {
                    'type_document': 'AUTRE',
                    'confidence': 0.5,
                    'tags': []
                }

            type_doc = result.get('type_document', 'AUTRE')
            category = self.TYPE_TO_CATEGORY.get(type_doc, 'Divers')

            return ClassificationResult(
                type_document=type_doc,
                confidence=float(result.get('confidence', 0.5)),
                categories=[category],
                tags=result.get('tags', [])
            )

        except Exception as e:
            logger.error(f"Erreur classification document: {e}")
            return ClassificationResult(
                type_document='AUTRE',
                confidence=0.0,
                categories=['Divers'],
                tags=[]
            )

    # =========================================================================
    # EXTRACTION DE METADONNEES STRUCTUREES
    # =========================================================================

    def extract_metadata(
        self,
        text: str,
        type_document: str,
        custom_schema: Optional[Dict] = None
    ) -> ExtractionResult:
        """
        Extrait les metadonnees structurees d'un document.

        Args:
            text: Texte du document
            type_document: Type de document (pour choisir le schema)
            custom_schema: Schema personnalise (optionnel)

        Returns:
            ExtractionResult avec les donnees extraites
        """
        # Determiner le schema a utiliser
        schema = custom_schema or self.EXTRACTION_SCHEMAS.get(type_document, {})

        if not schema:
            # Schema generique pour documents inconnus
            schema = {
                'titre': 'string',
                'date': 'string',
                'expediteur': 'string',
                'destinataire': 'string',
                'sujet': 'string',
                'montant': 'number'
            }

        try:
            response = self._make_request(
                'POST',
                '/extract',
                json_data={
                    'text': text[:10000],  # Limiter la taille
                    'schema': schema
                }
            )

            # Extraire les donnees de la reponse
            data = response.get('data', response.get('extracted', response))
            if isinstance(data, dict) and 'data' not in response and 'extracted' not in response:
                # La reponse est directement les donnees
                pass

            return ExtractionResult(
                data=data if isinstance(data, dict) else {},
                confidence=response.get('confidence', 0.9)
            )

        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Erreur extraction metadonnees: {e}")
            return ExtractionResult(data={}, confidence=0.0)

    # =========================================================================
    # CHAT IA
    # =========================================================================

    def chat(
        self,
        message: str,
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Interroge l'assistant IA.

        Args:
            message: Question ou instruction
            system: Prompt systeme (alias de system_prompt)
            system_prompt: Prompt systeme (personnalite de l'assistant)
            context: Contexte additionnel (ex: contenu document)
            history: Historique de conversation [{role: 'user'|'assistant', content: '...'}]
            temperature: Temperature de generation (0.0-1.0)

        Returns:
            Dict avec 'response', 'tokens_prompt', 'tokens_completion'
        """
        # Support des deux noms de parametre
        system = system or system_prompt

        if context:
            message = f"Contexte:\n{context}\n\nQuestion: {message}"

        # Construire les messages pour l'API
        messages = []
        if system:
            messages.append({'role': 'system', 'content': system})

        # Ajouter l'historique de conversation (exclure le dernier message user)
        if history:
            for msg in history[:-1] if history else []:
                role = msg.get('role', '').lower()
                content = msg.get('content', '')
                if role in ['user', 'assistant'] and content:
                    messages.append({'role': role, 'content': content})

        messages.append({'role': 'user', 'content': message})

        try:
            response = self._make_request(
                'POST',
                '/chat',
                json_data={
                    'messages': messages,
                    'temperature': temperature
                }
            )

            # Extraire le contenu de la reponse - supporter differents formats
            response_text = response.get('message',
                            response.get('content',
                            response.get('response', '')))

            return {
                'response': response_text,
                'tokens_prompt': response.get('tokens_prompt', response.get('usage', {}).get('prompt_tokens', 0)),
                'tokens_completion': response.get('tokens_completion', response.get('usage', {}).get('completion_tokens', 0))
            }

        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Erreur chat IA: {e}")
            raise AIServiceError(f"Erreur lors de la requete chat: {str(e)}")

    # =========================================================================
    # TRAITEMENT COMPLET DE DOCUMENT
    # =========================================================================

    def process_document(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        generate_embedding: bool = True
    ) -> Dict[str, Any]:
        """
        Traitement complet d'un document:
        1. OCR (extraction texte)
        2. Classification
        3. Extraction metadonnees
        4. Generation embedding (optionnel)

        Args:
            file_path: Chemin vers le fichier
            file_content: Contenu en bytes
            filename: Nom du fichier
            mime_type: Type MIME
            generate_embedding: Generer l'embedding vectoriel

        Returns:
            Dict avec tous les resultats du traitement
        """
        result = {
            'ocr': None,
            'classification': None,
            'metadata': None,
            'embedding': None,
            'success': False,
            'errors': []
        }

        # 1. OCR
        try:
            ocr_result = self.ocr(file_path=file_path, file_content=file_content)
            result['ocr'] = {
                'text': ocr_result.text,
                'confidence': ocr_result.confidence,
                'pages': ocr_result.pages,
                'language': ocr_result.language
            }
        except AIServiceError as e:
            result['errors'].append(f"OCR: {str(e)}")
            return result

        text = ocr_result.text

        # 2. Classification
        try:
            classification = self.classify_document(text, filename)
            result['classification'] = {
                'type_document': classification.type_document,
                'confidence': classification.confidence,
                'categories': classification.categories,
                'tags': classification.tags
            }
        except Exception as e:
            result['errors'].append(f"Classification: {str(e)}")
            result['classification'] = {
                'type_document': 'AUTRE',
                'confidence': 0,
                'categories': ['Divers'],
                'tags': []
            }

        # 3. Extraction metadonnees
        try:
            type_doc = result['classification']['type_document']
            extraction = self.extract_metadata(text, type_doc)
            result['metadata'] = extraction.data
        except Exception as e:
            result['errors'].append(f"Extraction: {str(e)}")
            result['metadata'] = {}

        # 4. Embedding
        if generate_embedding:
            try:
                embedding = self.embed(text)
                result['embedding'] = embedding
            except Exception as e:
                result['errors'].append(f"Embedding: {str(e)}")

        result['success'] = len(result['errors']) == 0
        return result

    # =========================================================================
    # UTILITAIRES
    # =========================================================================

    def compute_text_hash(self, text: str) -> str:
        """Calcule le hash SHA-256 d'un texte."""
        return hashlib.sha256(text.encode()).hexdigest()

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcule la similarite cosinus entre deux embeddings.

        Returns:
            Score entre 0 et 1 (1 = identique)
        """
        import numpy as np

        a = np.array(embedding1)
        b = np.array(embedding2)

        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def health_check(self) -> Dict[str, Any]:
        """
        Verifie l'etat du service AI.

        Returns:
            Dict avec le statut et details
        """
        status = {
            'enabled': self.enabled,
            'api_url': self.api_url,
            'connected': False,
            'error': None
        }

        if not self.enabled:
            status['error'] = "Service non configure (AI_API_KEY manquant)"
            return status

        try:
            # 1. Verifier le health endpoint (pas d'auth requise)
            health_response = requests.get(
                f"{self.api_url}/health",
                timeout=10
            )
            if health_response.status_code == 200:
                health_data = health_response.json()
                status['api_status'] = health_data.get('status', 'unknown')
                status['api_version'] = health_data.get('version', 'unknown')

            # 2. Test avec un embedding pour verifier l'API key
            test_embedding = self.embed("test")
            status['connected'] = len(test_embedding) == 768
            status['embedding_dimensions'] = len(test_embedding)

        except AIServiceError as e:
            status['error'] = str(e)
        except Exception as e:
            status['error'] = f"Erreur connexion: {str(e)}"

        return status


# Instance singleton
ai_service = AltiusAIService()
