# core/pdf.py
"""
Utilitaires PDF globaux pour le projet Altiusone.

- PDFViewSetMixin: Ajoute preview_pdf et download_pdf à tout ViewSet DRF
- serve_pdf: Vue utilitaire pour servir/générer un PDF (preview ou download)
- serve_file: Vue utilitaire pour servir un fichier uploadé quelconque
- save_pdf_overwrite: Sauvegarde un PDF en supprimant l'ancien fichier
"""
import logging

from django.core.files.base import ContentFile
from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


class PDFViewSetMixin:
    """
    Mixin DRF ajoutant les actions preview_pdf et download_pdf à un ViewSet.

    Attributs configurables:
        pdf_field_name (str): Nom du champ FileField sur le modèle (défaut: 'fichier_pdf')

    Usage:
        class MonViewSet(PDFViewSetMixin, viewsets.ModelViewSet):
            pdf_field_name = 'fichier_pdf'
    """

    pdf_field_name = 'fichier_pdf'

    def _get_pdf_field(self, obj):
        """Retourne le champ fichier PDF de l'instance."""
        return getattr(obj, self.pdf_field_name, None)

    @action(detail=True, methods=['get'], url_path='preview-pdf')
    def preview_pdf(self, request, pk=None):
        """Aperçu inline du PDF dans le navigateur."""
        obj = self.get_object()
        field = self._get_pdf_field(obj)

        if not field:
            return Response(
                {"error": "Aucun PDF disponible"},
                status=status.HTTP_404_NOT_FOUND
            )

        response = FileResponse(
            field.open('rb'),
            content_type='application/pdf',
        )
        filename = field.name.split('/')[-1]
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Cache-Control'] = 'private, max-age=3600'
        return response

    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        """Téléchargement du PDF en pièce jointe."""
        obj = self.get_object()
        field = self._get_pdf_field(obj)

        if not field:
            return Response(
                {"error": "Aucun PDF disponible"},
                status=status.HTTP_404_NOT_FOUND
            )

        response = FileResponse(
            field.open('rb'),
            content_type='application/pdf',
        )
        filename = field.name.split('/')[-1]
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


def serve_pdf(request, instance, field_name, filename, redirect_url, generate=True, inline=False):
    """
    Utilitaire global : génère (optionnel) et sert un PDF via FileResponse streaming.

    Args:
        request: HttpRequest Django
        instance: Instance du modèle avec generer_pdf()
        field_name: Nom du champ FileField ('fichier_pdf', 'fichier_declaration')
        filename: Nom du fichier pour Content-Disposition
        redirect_url: URL de redirection en cas d'erreur (str ou tuple (url_name, pk))
        generate: Si True, appelle instance.generer_pdf() avant de servir
        inline: Si True, Content-Disposition: inline (preview), sinon attachment (download)
    """
    from django.contrib import messages
    from django.shortcuts import redirect as do_redirect
    from django.utils.translation import gettext_lazy as _

    try:
        if generate:
            instance.generer_pdf()

        field = getattr(instance, field_name)
        if field:
            response = FileResponse(field.open("rb"), content_type="application/pdf")
            disposition = "inline" if inline else "attachment"
            response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
            if inline:
                response["X-Frame-Options"] = "SAMEORIGIN"
                response["Cache-Control"] = "private, max-age=3600"
            return response

        messages.error(request, _("Aucun PDF disponible"))
    except Exception as e:
        messages.error(request, _("Erreur lors de la génération du PDF: %(error)s") % {'error': str(e)})

    if isinstance(redirect_url, tuple):
        return do_redirect(redirect_url[0], pk=redirect_url[1])
    return do_redirect(redirect_url)


def serve_file(request, instance, field_name, filename, redirect_url, content_type=None):
    """
    Utilitaire global : sert un fichier uploadé (sans génération).

    Utile pour les FileFields qui sont des uploads manuels (fiscalité, annexes).

    Args:
        request: HttpRequest Django
        instance: Instance du modèle
        field_name: Nom du champ FileField
        filename: Nom du fichier pour Content-Disposition
        redirect_url: URL de redirection en cas d'erreur (str ou tuple)
        content_type: Type MIME (auto-détecté si None)
    """
    from django.contrib import messages
    from django.shortcuts import redirect as do_redirect
    from django.utils.translation import gettext_lazy as _
    import mimetypes

    field = getattr(instance, field_name, None)
    if field and field.name:
        if content_type is None:
            content_type, _ = mimetypes.guess_type(field.name)
            content_type = content_type or "application/octet-stream"
        response = FileResponse(field.open("rb"), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    messages.error(request, _("Aucun fichier disponible"))
    if isinstance(redirect_url, tuple):
        return do_redirect(redirect_url[0], pk=redirect_url[1])
    return do_redirect(redirect_url)


def save_pdf_overwrite(instance, field_name, pdf_bytes, filename):
    """
    Supprime l'ancien fichier avant de sauvegarder le nouveau PDF.

    Évite l'accumulation de fichiers orphelins sur le storage (S3/local)
    sans avoir à modifier file_overwrite sur les storage classes.

    Args:
        instance: Instance du modèle Django
        field_name: Nom du champ FileField (ex: 'fichier_pdf')
        pdf_bytes: Contenu du PDF en bytes
        filename: Nom du fichier à sauvegarder

    Returns:
        Le champ FileField après sauvegarde
    """
    field = getattr(instance, field_name)

    # Supprimer l'ancien fichier s'il existe
    if field and field.name:
        try:
            if field.storage.exists(field.name):
                field.storage.delete(field.name)
        except Exception:
            logger.warning(
                "Impossible de supprimer l'ancien fichier %s pour %s",
                field.name, instance,
            )

    field.save(filename, ContentFile(pdf_bytes), save=True)
    return getattr(instance, field_name)
