# documents/ai_service.py
"""
Service AI unifie pour AltiusOne.

Combine traitement local et API AltiusOne AI:
- OCR: Tesseract local (images, PDF scannes, multilingue FR/DE/EN/IT)
- Embeddings: API AltiusOne AI (vecteurs 768D, nomic-embed-text)
- Extraction structuree: API AltiusOne AI (qwen2.5:3b)
- Chat IA: API AltiusOne AI (qwen2.5:3b, streaming SSE)
- Resume et Q&A sur documents

Configuration via .env:
- AI_API_KEY: Cle API AltiusOne
- AI_API_URL: URL de l'API (https://ai.altiusone.ch)

Endpoints API utilises:
- POST /embeddings - Generation d'embeddings 768D
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

# Import des schemas personnalises
from documents.schemas import (
    DOCUMENT_TYPE_SCHEMAS,
    get_schema_for_document_type,
    get_available_document_types,
)

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

    # Mapping types de documents vers categories
    TYPE_TO_CATEGORY = {
        # Comptabilite
        'FACTURE': 'Comptabilite',
        'FACTURE_ACHAT': 'Comptabilite',
        'FACTURE_VENTE': 'Comptabilite',
        'DEVIS': 'Commercial',
        'OFFRE': 'Commercial',
        'BON_COMMANDE': 'Commercial',
        'BON_LIVRAISON': 'Logistique',

        # Banque
        'RELEVE_BANQUE': 'Banque',
        'EXTRAIT_BANCAIRE': 'Banque',

        # Contrats
        'CONTRAT': 'Juridique',
        'CONTRAT_TRAVAIL': 'RH',
        'CONTRAT_BAIL': 'Juridique',

        # RH / Salaires
        'FICHE_SALAIRE': 'RH',
        'CERTIFICAT_SALAIRE': 'RH',

        # Fiscal
        'DECLARATION_TVA': 'Fiscal',

        # Administratif
        'ATTESTATION': 'Administratif',
        'CORRESPONDANCE': 'Correspondance',
        'COURRIER': 'Correspondance',
        'EMAIL': 'Correspondance',

        # Divers
        'AUTRE': 'Divers',
    }

    def __init__(self):
        self.api_url = getattr(settings, 'AI_API_URL', 'https://ai.altiusone.ch').rstrip('/')
        self.api_key = getattr(settings, 'AI_API_KEY', '')
        self.timeout = 300  # Timeout augmente pour operations longues (300s = 5min)
        self.timeout_short = 60  # Timeout court pour operations rapides (embeddings, health)

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
            status_code = e.response.status_code
            # Cloudflare-specific errors (return HTML, not JSON)
            cloudflare_errors = {
                520: "Le service IA a retourne une erreur inattendue",
                521: "Le service IA est arrete",
                522: "Le service IA est injoignable (connexion impossible)",
                523: "Le service IA est injoignable (origine introuvable)",
                524: "Le service IA met trop de temps a repondre",
            }
            if status_code in cloudflare_errors:
                error_msg = cloudflare_errors[status_code]
                logger.error(f"Cloudflare {status_code}: {error_msg} ({url})")
                raise AIServiceError(error_msg)

            error_msg = f"Erreur HTTP {status_code}"
            try:
                # Detect HTML responses (Cloudflare, nginx, etc.)
                content_type = e.response.headers.get('content-type', '')
                if 'text/html' in content_type or e.response.text[:15].strip().startswith(('<', '<!',)):
                    error_msg = f"Le service IA a retourne une erreur (HTTP {status_code})"
                else:
                    error_detail = e.response.json().get('detail', e.response.text)
                    error_msg = f"{error_msg}: {error_detail}"
            except Exception:
                error_msg = f"Le service IA a retourne une erreur (HTTP {status_code})"
            logger.error(error_msg)
            raise AIServiceError(error_msg)

        except Exception as e:
            logger.error(f"Erreur inattendue API: {e}")
            raise AIServiceError(f"Erreur inattendue: {str(e)}")

    # =========================================================================
    # OCR - EXTRACTION DE TEXTE
    # =========================================================================

    # Mapping langue -> code Tesseract
    TESSERACT_LANGS = {
        'fr': 'fra', 'de': 'deu', 'it': 'ita', 'en': 'eng',
        'auto': 'fra+deu+eng+ita',
    }

    def ocr(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_url: Optional[str] = None,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        language: str = 'auto'
    ) -> OCRResult:
        """
        Extrait le texte d'un document (image, PDF ou DOCX).

        Utilise Tesseract OCR localement (rapide, CPU).
        DOCX: extraction directe du texte (pas d'OCR).
        PDF: extraction du texte embarque, puis OCR sur les pages images.
        Images: OCR Tesseract.

        Args:
            file_path: Chemin vers le fichier local
            file_content: Contenu du fichier en bytes
            file_url: URL du fichier (telecharge puis traite)
            filename: Nom du fichier (pour determiner le mime_type)
            mime_type: Type MIME du fichier (prioritaire sur la detection)
            language: Langue du document (auto, fr, de, en, it)

        Returns:
            OCRResult avec le texte extrait et metadonnees
        """
        import time as _time
        start = _time.time()

        try:
            if file_path:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                if not filename:
                    filename = file_path.split('/')[-1]

            if file_url and not file_content:
                import requests as _req
                resp = _req.get(file_url, timeout=30)
                resp.raise_for_status()
                file_content = resp.content
                if not filename:
                    filename = file_url.split('/')[-1].split('?')[0] or 'document'

            if not file_content:
                raise AIServiceError("Aucune source de fichier fournie")

            import mimetypes
            if not filename:
                filename = 'document'
            if not mime_type:
                mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            # DOCX — extraction directe
            if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or filename.lower().endswith('.docx'):
                return self._extract_text_from_docx(file_content, filename)

            # PDF — texte embarque + OCR fallback sur pages images
            if 'pdf' in mime_type.lower() or filename.lower().endswith('.pdf'):
                return self._ocr_pdf(file_content, language, start)

            # Images — OCR Tesseract
            return self._ocr_image(file_content, language, start)

        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Erreur OCR: {e}")
            raise AIServiceError(f"Erreur lors de l'extraction OCR: {str(e)}")

    def _ocr_image(self, image_bytes: bytes, language: str, start_time: float) -> OCRResult:
        """OCR d'une image avec Tesseract."""
        import time as _time
        import pytesseract
        from PIL import Image
        import io

        lang = self.TESSERACT_LANGS.get(language, 'fra+deu+eng+ita')
        img = Image.open(io.BytesIO(image_bytes))

        text = pytesseract.image_to_string(img, lang=lang)
        processing_ms = (_time.time() - start_time) * 1000

        detected_lang = language if language != 'auto' else 'fr'

        return OCRResult(
            text=text.strip(),
            confidence=90.0,
            pages=1,
            language=detected_lang,
            processing_time=processing_ms
        )

    def _ocr_pdf(self, pdf_bytes: bytes, language: str, start_time: float) -> OCRResult:
        """OCR d'un PDF: texte embarque d'abord, puis OCR sur pages images."""
        import time as _time
        import io

        # 1. Essayer d'extraire le texte embarque (PDF textuel)
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)
            text_parts = []

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())

            # Si on a du texte pour la majorite des pages, c'est un PDF textuel
            if len(text_parts) >= num_pages * 0.5 and any(len(t) > 20 for t in text_parts):
                processing_ms = (_time.time() - start_time) * 1000
                return OCRResult(
                    text='\n\n'.join(text_parts),
                    confidence=95.0,
                    pages=num_pages,
                    language=language if language != 'auto' else 'fr',
                    processing_time=processing_ms
                )
        except Exception as e:
            logger.warning(f"Extraction texte PDF echouee, fallback OCR: {e}")
            num_pages = 0

        # 2. PDF image — convertir en images et OCR chaque page
        import pytesseract
        from pdf2image import convert_from_bytes

        lang = self.TESSERACT_LANGS.get(language, 'fra+deu+eng+ita')
        images = convert_from_bytes(pdf_bytes, dpi=300)
        num_pages = len(images)
        text_parts = []

        for img in images:
            page_text = pytesseract.image_to_string(img, lang=lang)
            if page_text and page_text.strip():
                text_parts.append(page_text.strip())

        processing_ms = (_time.time() - start_time) * 1000

        return OCRResult(
            text='\n\n'.join(text_parts),
            confidence=85.0,
            pages=num_pages,
            language=language if language != 'auto' else 'fr',
            processing_time=processing_ms
        )

    def _extract_text_from_docx(self, file_content: bytes, filename: str) -> OCRResult:
        """
        Extrait le texte d'un fichier DOCX localement (sans OCR).

        Args:
            file_content: Contenu du fichier DOCX en bytes
            filename: Nom du fichier

        Returns:
            OCRResult avec le texte extrait
        """
        import io
        try:
            from docx import Document as DocxDocument
        except ImportError:
            raise AIServiceError("python-docx non installe. Installez-le avec: pip install python-docx")

        try:
            # Charger le document DOCX depuis les bytes
            doc = DocxDocument(io.BytesIO(file_content))

            # Extraire le texte de tous les paragraphes
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)

            # Extraire aussi le texte des tableaux
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        paragraphs.append(' | '.join(row_text))

            text = '\n'.join(paragraphs)

            return OCRResult(
                text=text,
                confidence=100.0,  # Extraction directe, pas d'OCR
                pages=1,
                language='fr',
                processing_time=0.0
            )

        except Exception as e:
            logger.error(f"Erreur extraction DOCX {filename}: {e}")
            raise AIServiceError(f"Erreur lors de l'extraction du texte DOCX: {str(e)}")

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
        # Types de documents disponibles (depuis schemas.py)
        types_disponibles = get_available_document_types()

        system_prompt = f"""Tu es un assistant specialise dans la classification de documents professionnels (comptabilite, facturation, RH, projets).

Types de documents disponibles:
- FACTURE_ACHAT, FACTURE_VENTE: Factures fournisseurs ou clients
- CONTRAT_TRAVAIL: Contrats de travail (CDI, CDD, apprentissage)
- CONTRAT_BAIL: Contrats de location (habitation, commercial)
- CONTRAT: Autres contrats (prestation, vente, etc.)
- FICHE_SALAIRE: Fiches/bulletins de paie mensuels
- CERTIFICAT_SALAIRE: Certificats de salaire annuels
- RELEVE_BANQUE, EXTRAIT_BANCAIRE: Releves de compte bancaire
- DECLARATION_TVA: Declarations TVA trimestrielles/annuelles
- DEVIS, OFFRE: Devis et offres commerciales
- ATTESTATION: Attestations diverses (domicile, travail, etc.)
- CORRESPONDANCE, COURRIER: Lettres et correspondance

Analyse le document et determine son type.
Reponds UNIQUEMENT en JSON valide:
{{"type_document": "TYPE_EXACT", "confidence": 0.95, "tags": ["tag1", "tag2"], "raison": "breve explication"}}"""

        user_prompt = f"""Classifie ce document suisse:
Nom fichier: {filename or 'inconnu'}

Contenu:
{text[:4000]}"""

        try:
            chat_response = self.chat(message=user_prompt, system=system_prompt)
            response_text = chat_response.get('response', '') if isinstance(chat_response, dict) else str(chat_response)

            # Parser la reponse JSON
            import json
            try:
                # Essayer de trouver le JSON dans la reponse
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(response_text[json_start:json_end])
                else:
                    result = json.loads(response_text)
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
        custom_schema: Optional[Dict] = None,
        source_language: str = 'auto',
        output_language: str = 'fr'
    ) -> ExtractionResult:
        """
        Extrait les metadonnees structurees d'un document.

        Utilise les schemas personnalises definis dans documents/schemas.py
        pour extraire des informations structurees (adresses, montants,
        numeros TVA, AVS, noms, etc.)

        Args:
            text: Texte du document
            type_document: Type de document (FACTURE_ACHAT, CONTRAT_TRAVAIL, etc.)
            custom_schema: Schema personnalise (prioritaire sur le schema predefini)
            source_language: Langue du document source (auto, fr, de, it, en)
            output_language: Langue de sortie pour les extractions (fr par defaut)

        Returns:
            ExtractionResult avec les donnees extraites
        """
        # Utiliser le schema personnalise ou celui defini pour le type de document
        schema = custom_schema or get_schema_for_document_type(type_document)

        try:
            response = self._make_request(
                'POST',
                '/extract',
                json_data={
                    'text': text[:15000],  # Augmente la limite pour documents longs
                    'schema': schema,
                    'source_language': source_language,
                    'output_language': output_language,
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
        message: str = "",
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        messages_override: Optional[List[Dict[str, str]]] = None,
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
            max_tokens: Limite de tokens pour la reponse (reduit le temps de reponse)
            tools: Definitions d'outils pour le function calling
            messages_override: Si fourni, utilise ces messages directement (ignore message/system/history)

        Returns:
            Dict avec 'response', 'tokens_prompt', 'tokens_completion', et optionnel 'tool_calls'
        """
        if messages_override:
            messages = messages_override
        else:
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
            request_data = {
                'messages': messages,
                'temperature': temperature
            }
            if max_tokens:
                request_data['max_tokens'] = max_tokens
            if tools:
                request_data['tools'] = tools

            response = self._make_request(
                'POST',
                '/chat',
                json_data=request_data
            )

            # Extraire le contenu de la reponse - supporter differents formats
            response_text = response.get('message',
                            response.get('content',
                            response.get('response', '')))

            result = {
                'response': response_text,
                'tokens_prompt': response.get('tokens_prompt', response.get('usage', {}).get('prompt_tokens', 0)),
                'tokens_completion': response.get('tokens_completion', response.get('usage', {}).get('completion_tokens', 0)),
            }

            # Propager les tool_calls si presents
            tool_calls = response.get('tool_calls')
            if tool_calls:
                result['tool_calls'] = tool_calls

            return result

        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Erreur chat IA: {e}")
            raise AIServiceError(f"Erreur lors de la requete chat: {str(e)}")

    def chat_stream(
        self,
        message: str = "",
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[List[dict]] = None,
        messages_override: Optional[List[Dict[str, str]]] = None,
    ):
        """
        Stream chat response token by token via SSE.

        Same signature as chat() but yields dicts from the SSE stream.
        Falls back gracefully if the server returns a non-streaming JSON response.

        Yields:
            Dict with 'token', 'done', 'tool_calls', and optionally 'model', 'tokens_used', 'processing_time_ms'
        """
        if not self.enabled:
            raise AIServiceError("Service AI non configure. Verifiez AI_API_KEY et AI_API_URL dans .env")

        if messages_override:
            messages = messages_override
        else:
            # Support des deux noms de parametre
            system = system or system_prompt

            if context:
                message = f"Contexte:\n{context}\n\nQuestion: {message}"

            # Construire les messages pour l'API
            messages = []
            if system:
                messages.append({'role': 'system', 'content': system})

            if history:
                for msg in history[:-1] if history else []:
                    role = msg.get('role', '').lower()
                    content = msg.get('content', '')
                    if role in ['user', 'assistant'] and content:
                        messages.append({'role': role, 'content': content})

            messages.append({'role': 'user', 'content': message})

        url = f"{self.api_url}/chat"

        request_body = {
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': True,
        }
        if tools:
            request_body['tools'] = tools

        try:
            import json as _json
            response = requests.post(
                url,
                json=request_body,
                headers=self._get_headers(),
                stream=True,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                cloudflare_errors = {
                    520: "Le service IA a retourne une erreur inattendue",
                    521: "Le service IA est arrete",
                    522: "Le service IA est injoignable (connexion impossible)",
                    523: "Le service IA est injoignable (origine introuvable)",
                    524: "Le service IA met trop de temps a repondre",
                }
                if response.status_code in cloudflare_errors:
                    raise AIServiceError(cloudflare_errors[response.status_code])
                raise AIServiceError(f"Erreur HTTP {response.status_code}")

            # Check if response is SSE or plain JSON
            content_type = response.headers.get('content-type', '')
            is_sse = 'text/event-stream' in content_type

            if is_sse:
                # True SSE streaming - yield token by token
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith('data: '):
                        line = line[6:]
                    try:
                        event = _json.loads(line)
                        yield event
                        if event.get('done'):
                            return
                    except _json.JSONDecodeError:
                        continue
            else:
                # Non-streaming fallback: server returned plain JSON
                data = response.json()

                # Check for tool_calls
                tool_calls = data.get('tool_calls')
                if tool_calls:
                    yield {
                        'type': 'tool_calls',
                        'tool_calls': tool_calls,
                    }
                    return

                response_text = data.get('message',
                                data.get('content',
                                data.get('response', '')))

                # Yield the full response as a single token
                if response_text:
                    yield {'type': 'token', 'token': response_text}

                # Yield done event
                yield {
                    'type': 'done',
                    'done': True,
                    'model': data.get('model', ''),
                    'tokens_used': data.get('tokens_used', 0),
                    'processing_time_ms': data.get('processing_time_ms', 0),
                }

        except AIServiceError:
            raise
        except requests.exceptions.Timeout:
            raise AIServiceError(f"L'API n'a pas repondu dans les {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise AIServiceError(f"Impossible de se connecter a {self.api_url}")
        except Exception as e:
            logger.error(f"Erreur chat stream: {e}")
            raise AIServiceError(f"Erreur lors du streaming chat: {str(e)}")

    # =========================================================================
    # RESUME ET Q&A SUR DOCUMENTS
    # =========================================================================

    def summarize_document(
        self,
        text: str,
        max_length: str = 'medium',
        language: str = 'fr'
    ) -> Dict[str, Any]:
        """
        Genere un resume d'un document (utile pour documents longs).

        Args:
            text: Texte complet du document
            max_length: Longueur du resume ('short', 'medium', 'long')
            language: Langue du resume (fr, de, en, it)

        Returns:
            Dict avec 'summary', 'key_points', 'entities'
        """
        length_instructions = {
            'short': '3-5 phrases maximum',
            'medium': '1-2 paragraphes',
            'long': '3-4 paragraphes detailles'
        }

        system_prompt = f"""Tu es un assistant specialise dans l'analyse de documents professionnels suisses.
Genere un resume clair et structure en {language.upper()}.
Longueur attendue: {length_instructions.get(max_length, '1-2 paragraphes')}

Format de reponse JSON:
{{
    "summary": "Resume du document...",
    "key_points": ["Point cle 1", "Point cle 2", ...],
    "entities": {{
        "personnes": ["Nom 1", "Nom 2"],
        "organisations": ["Entreprise 1"],
        "montants": ["CHF 1'000.00"],
        "dates": ["15.01.2024"]
    }},
    "type_document_suggere": "FACTURE_ACHAT"
}}"""

        # Limiter le texte pour eviter les timeouts (4000 chars max)
        text_truncated = text[:4000] if len(text) > 4000 else text

        user_prompt = f"""Resume ce document:

{text_truncated}"""

        try:
            chat_response = self.chat(message=user_prompt, system=system_prompt, temperature=0.3, max_tokens=1000)
            response_text = chat_response.get('response', '') if isinstance(chat_response, dict) else str(chat_response)

            # Parser la reponse JSON
            import json
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(response_text[json_start:json_end])
                else:
                    result = {'summary': response_text, 'key_points': [], 'entities': {}}
            except json.JSONDecodeError:
                result = {'summary': response_text, 'key_points': [], 'entities': {}}

            return result

        except Exception as e:
            logger.error(f"Erreur resume document: {e}")
            return {'summary': '', 'key_points': [], 'entities': {}, 'error': str(e)}

    def ask_document(
        self,
        text: str,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        language: str = 'fr'
    ) -> Dict[str, Any]:
        """
        Pose une question sur un document specifique (Q&A contextuel).

        Permet aux utilisateurs de poser des questions sur le contenu
        d'un document et d'obtenir des reponses precises basees sur le texte.

        Args:
            text: Texte du document (OCR)
            question: Question de l'utilisateur
            history: Historique de conversation pour le suivi
            language: Langue de reponse

        Returns:
            Dict avec 'answer', 'confidence', 'sources'
        """
        system_prompt = f"""Tu es un assistant expert pour analyser des documents professionnels suisses.
Tu reponds aux questions en te basant UNIQUEMENT sur le contenu du document fourni.
Si l'information n'est pas dans le document, dis-le clairement.
Reponds en {language.upper()} de maniere precise et professionnelle.

Format de reponse JSON:
{{
    "answer": "Reponse detaillee...",
    "confidence": 0.95,
    "sources": ["Extrait pertinent 1 du document...", "Extrait pertinent 2..."],
    "found_in_document": true
}}"""

        # Limiter le texte pour eviter les timeouts (4000 chars max)
        text_truncated = text[:4000] if len(text) > 4000 else text

        user_prompt = f"""Document:
---
{text_truncated}
---

Question: {question}"""

        try:
            chat_response = self.chat(
                message=user_prompt,
                system=system_prompt,
                history=history,
                temperature=0.2,
                max_tokens=800  # Limiter pour eviter les timeouts
            )
            response_text = chat_response.get('response', '') if isinstance(chat_response, dict) else str(chat_response)

            # Parser la reponse JSON
            import json
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(response_text[json_start:json_end])
                else:
                    result = {'answer': response_text, 'confidence': 0.5, 'sources': [], 'found_in_document': True}
            except json.JSONDecodeError:
                result = {'answer': response_text, 'confidence': 0.5, 'sources': [], 'found_in_document': True}

            return result

        except Exception as e:
            logger.error(f"Erreur Q&A document: {e}")
            return {'answer': '', 'confidence': 0, 'sources': [], 'error': str(e)}

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
            ocr_result = self.ocr(
                file_path=file_path,
                file_content=file_content,
                filename=filename,
                mime_type=mime_type
            )
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
