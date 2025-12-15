# core/services/document_service.py
"""
Service de lecture et de traitement des documents.
Permet de lire, afficher et générer des aperçus pour PDF, images, etc.
"""
import io
import os
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, BinaryIO, Union
from PIL import Image

from django.core.files.base import ContentFile
from django.http import HttpResponse, FileResponse
from django.conf import settings


class DocumentService:
    """
    Service centralisé pour la lecture et le traitement des documents.
    """

    # Types MIME supportés
    SUPPORTED_IMAGES = {
        'image/jpeg': 'JPEG',
        'image/png': 'PNG',
        'image/gif': 'GIF',
        'image/webp': 'WEBP',
        'image/bmp': 'BMP',
        'image/tiff': 'TIFF',
    }

    SUPPORTED_DOCUMENTS = {
        'application/pdf': 'PDF',
        'application/msword': 'DOC',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
        'application/vnd.ms-excel': 'XLS',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
        'text/plain': 'TXT',
        'text/csv': 'CSV',
    }

    # Tailles des miniatures
    THUMBNAIL_SIZES = {
        'small': (100, 100),
        'medium': (200, 200),
        'large': (400, 400),
    }

    @classmethod
    def get_mime_type(cls, file_path: str) -> str:
        """Détecte le type MIME d'un fichier."""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

    @classmethod
    def is_image(cls, file_path: str) -> bool:
        """Vérifie si le fichier est une image supportée."""
        mime_type = cls.get_mime_type(file_path)
        return mime_type in cls.SUPPORTED_IMAGES

    @classmethod
    def is_pdf(cls, file_path: str) -> bool:
        """Vérifie si le fichier est un PDF."""
        mime_type = cls.get_mime_type(file_path)
        return mime_type == 'application/pdf'

    @classmethod
    def is_document(cls, file_path: str) -> bool:
        """Vérifie si le fichier est un document supporté."""
        mime_type = cls.get_mime_type(file_path)
        return mime_type in cls.SUPPORTED_DOCUMENTS

    # ========================================================================
    # LECTURE DE FICHIERS
    # ========================================================================

    @classmethod
    def read_file(cls, file_path: str) -> bytes:
        """Lit un fichier et retourne son contenu en bytes."""
        with open(file_path, 'rb') as f:
            return f.read()

    @classmethod
    def read_file_stream(cls, file_path: str) -> BinaryIO:
        """Retourne un flux de lecture pour un fichier."""
        return open(file_path, 'rb')

    @classmethod
    def get_file_response(
        cls,
        file_path: str,
        filename: Optional[str] = None,
        as_attachment: bool = False
    ) -> FileResponse:
        """
        Génère une FileResponse pour servir un fichier.

        Args:
            file_path: Chemin vers le fichier
            filename: Nom du fichier à afficher (optionnel)
            as_attachment: Si True, force le téléchargement

        Returns:
            FileResponse configurée
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")

        mime_type = cls.get_mime_type(file_path)
        filename = filename or os.path.basename(file_path)

        response = FileResponse(
            open(file_path, 'rb'),
            content_type=mime_type
        )

        if as_attachment:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'inline; filename="{filename}"'

        return response

    # ========================================================================
    # TRAITEMENT D'IMAGES
    # ========================================================================

    @classmethod
    def read_image(cls, file_path: str) -> Image.Image:
        """Lit une image et retourne un objet PIL Image."""
        return Image.open(file_path)

    @classmethod
    def get_image_dimensions(cls, file_path: str) -> Tuple[int, int]:
        """Retourne les dimensions (largeur, hauteur) d'une image."""
        with Image.open(file_path) as img:
            return img.size

    @classmethod
    def generate_thumbnail(
        cls,
        file_path: str,
        size: str = 'medium',
        output_format: str = 'JPEG'
    ) -> bytes:
        """
        Génère une miniature d'une image.

        Args:
            file_path: Chemin vers l'image source
            size: 'small', 'medium', ou 'large'
            output_format: Format de sortie ('JPEG', 'PNG', etc.)

        Returns:
            bytes: Contenu de la miniature
        """
        if size not in cls.THUMBNAIL_SIZES:
            size = 'medium'

        max_size = cls.THUMBNAIL_SIZES[size]

        with Image.open(file_path) as img:
            # Convertir en RGB si nécessaire (pour JPEG)
            if output_format == 'JPEG' and img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Créer la miniature en conservant les proportions
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Sauvegarder dans un buffer
            buffer = io.BytesIO()
            img.save(buffer, format=output_format, quality=85)
            buffer.seek(0)

            return buffer.getvalue()

    @classmethod
    def get_thumbnail_response(
        cls,
        file_path: str,
        size: str = 'medium'
    ) -> HttpResponse:
        """
        Génère une HttpResponse avec la miniature d'une image.

        Args:
            file_path: Chemin vers l'image source
            size: 'small', 'medium', ou 'large'

        Returns:
            HttpResponse avec la miniature
        """
        thumbnail_data = cls.generate_thumbnail(file_path, size)

        response = HttpResponse(thumbnail_data, content_type='image/jpeg')
        response['Content-Disposition'] = 'inline'
        response['Cache-Control'] = 'max-age=86400'  # Cache 24h

        return response

    @classmethod
    def resize_image(
        cls,
        file_path: str,
        max_width: int,
        max_height: int,
        output_format: str = 'JPEG',
        quality: int = 85
    ) -> bytes:
        """
        Redimensionne une image en conservant les proportions.

        Args:
            file_path: Chemin vers l'image source
            max_width: Largeur maximale
            max_height: Hauteur maximale
            output_format: Format de sortie
            quality: Qualité (1-100)

        Returns:
            bytes: Image redimensionnée
        """
        with Image.open(file_path) as img:
            if output_format == 'JPEG' and img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format=output_format, quality=quality)
            buffer.seek(0)

            return buffer.getvalue()

    # ========================================================================
    # TRAITEMENT DE PDF
    # ========================================================================

    @classmethod
    def get_pdf_page_count(cls, file_path: str) -> int:
        """
        Retourne le nombre de pages d'un PDF.

        Requires: PyPDF2
        """
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            return len(reader.pages)
        except ImportError:
            return 0
        except Exception:
            return 0

    @classmethod
    def extract_pdf_text(cls, file_path: str, page_number: Optional[int] = None) -> str:
        """
        Extrait le texte d'un PDF.

        Args:
            file_path: Chemin vers le PDF
            page_number: Numéro de page (optionnel, toutes les pages si non spécifié)

        Returns:
            str: Texte extrait

        Requires: PyPDF2
        """
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)

            if page_number is not None:
                if 0 <= page_number < len(reader.pages):
                    return reader.pages[page_number].extract_text() or ''
                return ''

            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return '\n\n'.join(text_parts)

        except ImportError:
            return ''
        except Exception:
            return ''

    @classmethod
    def generate_pdf_thumbnail(
        cls,
        file_path: str,
        page_number: int = 0,
        size: str = 'medium'
    ) -> Optional[bytes]:
        """
        Génère une miniature de la première page d'un PDF.

        Args:
            file_path: Chemin vers le PDF
            page_number: Numéro de page (défaut: 0)
            size: Taille de la miniature

        Returns:
            bytes: Image miniature ou None si échec

        Requires: pdf2image (optionnel)
        """
        try:
            from pdf2image import convert_from_path

            max_size = cls.THUMBNAIL_SIZES.get(size, cls.THUMBNAIL_SIZES['medium'])

            # Convertir la page en image
            images = convert_from_path(
                file_path,
                first_page=page_number + 1,
                last_page=page_number + 1,
                size=max_size
            )

            if images:
                buffer = io.BytesIO()
                images[0].save(buffer, format='JPEG', quality=85)
                buffer.seek(0)
                return buffer.getvalue()

            return None

        except ImportError:
            # pdf2image non installé, retourner None
            return None
        except Exception:
            return None

    # ========================================================================
    # APERÇU DE DOCUMENTS
    # ========================================================================

    @classmethod
    def get_document_preview_data(cls, file_path: str) -> dict:
        """
        Génère des métadonnées d'aperçu pour un document.

        Args:
            file_path: Chemin vers le document

        Returns:
            dict avec les métadonnées (type, nom, taille, dimensions, etc.)
        """
        if not os.path.exists(file_path):
            return {'error': 'Fichier non trouvé'}

        stat = os.stat(file_path)
        mime_type = cls.get_mime_type(file_path)

        data = {
            'filename': os.path.basename(file_path),
            'mime_type': mime_type,
            'size': stat.st_size,
            'size_human': cls._format_file_size(stat.st_size),
            'is_image': cls.is_image(file_path),
            'is_pdf': cls.is_pdf(file_path),
            'can_preview': cls.is_image(file_path) or cls.is_pdf(file_path),
        }

        # Ajouter les dimensions pour les images
        if data['is_image']:
            try:
                width, height = cls.get_image_dimensions(file_path)
                data['width'] = width
                data['height'] = height
            except Exception:
                pass

        # Ajouter le nombre de pages pour les PDF
        if data['is_pdf']:
            data['page_count'] = cls.get_pdf_page_count(file_path)

        return data

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """Formate une taille en bytes en format lisible."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    # ========================================================================
    # OCR (Optionnel)
    # ========================================================================

    @classmethod
    def extract_text_ocr(cls, file_path: str, lang: str = 'fra') -> str:
        """
        Extrait le texte d'une image via OCR.

        Args:
            file_path: Chemin vers l'image
            lang: Code de langue pour Tesseract (défaut: français)

        Returns:
            str: Texte extrait

        Requires: pytesseract, tesseract-ocr
        """
        try:
            import pytesseract
            from PIL import Image

            with Image.open(file_path) as img:
                text = pytesseract.image_to_string(img, lang=lang)
                return text.strip()

        except ImportError:
            return ''
        except Exception:
            return ''

    @classmethod
    def extract_text_from_pdf_ocr(cls, file_path: str, lang: str = 'fra') -> str:
        """
        Extrait le texte d'un PDF scanné via OCR.

        Args:
            file_path: Chemin vers le PDF
            lang: Code de langue pour Tesseract

        Returns:
            str: Texte extrait

        Requires: pytesseract, pdf2image
        """
        try:
            import pytesseract
            from pdf2image import convert_from_path

            images = convert_from_path(file_path)
            text_parts = []

            for img in images:
                text = pytesseract.image_to_string(img, lang=lang)
                if text.strip():
                    text_parts.append(text.strip())

            return '\n\n'.join(text_parts)

        except ImportError:
            return ''
        except Exception:
            return ''
