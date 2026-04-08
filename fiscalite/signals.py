# fiscalite/signals.py
"""
Auto-filing GED pour les documents fiscaux uploadés.

Quand un fichier est uploadé sur DeclarationFiscale, AnnexeFiscale
ou ReclamationFiscale, il est automatiquement classé dans la GED
sous le dossier Fiscalité du mandat.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _file_fiscalite_document(instance, field_name, description):
    """Classe un fichier fiscal dans la GED si le champ est rempli."""
    field = getattr(instance, field_name, None)
    if not field or not field.name:
        return

    mandat = getattr(instance, 'mandat', None)
    if not mandat:
        return

    try:
        field.open('rb')
        file_bytes = field.read()
        field.close()

        if not file_bytes:
            return

        import os
        import hashlib
        from core.pdf import auto_file_to_ged
        from documents.models import Document

        filename = os.path.basename(field.name)
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        if Document.objects.filter(mandat=mandat, hash_fichier=file_hash).exists():
            return

        auto_file_to_ged(
            mandat=mandat,
            file_bytes=file_bytes,
            filename=filename,
            dossier_nom='Fiscalité',
            description=description,
        )
    except Exception:
        logger.warning(
            "Auto-filing GED echoue pour %s.%s (%s)",
            instance.__class__.__name__, field_name, instance,
        )


@receiver(post_save, sender='fiscalite.DeclarationFiscale')
def auto_file_declaration_fiscale(sender, instance, **kwargs):
    _file_fiscalite_document(
        instance, 'fichier_declaration',
        f"Declaration fiscale {instance.annee_fiscale} - fichier depose",
    )
    _file_fiscalite_document(
        instance, 'fichier_taxation',
        f"Declaration fiscale {instance.annee_fiscale} - avis de taxation",
    )


@receiver(post_save, sender='fiscalite.AnnexeFiscale')
def auto_file_annexe_fiscale(sender, instance, **kwargs):
    _file_fiscalite_document(
        instance, 'fichier',
        f"Annexe fiscale - {instance}",
    )


@receiver(post_save, sender='fiscalite.ReclamationFiscale')
def auto_file_reclamation_fiscale(sender, instance, **kwargs):
    _file_fiscalite_document(
        instance, 'fichier_reclamation',
        "Reclamation fiscale - fichier de reclamation",
    )
    _file_fiscalite_document(
        instance, 'fichier_decision',
        "Reclamation fiscale - decision",
    )
