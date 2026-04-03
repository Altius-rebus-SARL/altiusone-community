# core/views/studio_views.py
"""
Vues API pour le Document Studio (sauvegarde de modèles PDF).
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import ModeleDocumentPDF


def _resolve_mandat(type_document, config):
    """
    Retrouve le mandat associé au document via l'instance_id.
    Retourne le mandat ou None.
    """
    instance_id = config.get('instance_id')
    if not instance_id:
        return None

    if type_document in ('FACTURE', 'AVOIR', 'ACOMPTE'):
        from facturation.models import Facture
        try:
            return Facture.objects.get(pk=instance_id).mandat
        except Facture.DoesNotExist:
            return None
    elif type_document == 'FICHE_SALAIRE':
        from salaires.models import FicheSalaire
        try:
            return FicheSalaire.objects.get(pk=instance_id).employe.mandat
        except FicheSalaire.DoesNotExist:
            return None
    elif type_document == 'CERTIFICAT_SALAIRE':
        from salaires.models import CertificatSalaire
        try:
            return CertificatSalaire.objects.get(pk=instance_id).employe.mandat
        except CertificatSalaire.DoesNotExist:
            return None
    elif type_document == 'CERTIFICAT_TRAVAIL':
        from salaires.models import CertificatTravail
        try:
            return CertificatTravail.objects.get(pk=instance_id).employe.mandat
        except CertificatTravail.DoesNotExist:
            return None
    elif type_document == 'DECLARATION_COTISATIONS':
        from salaires.models import DeclarationCotisations
        try:
            return DeclarationCotisations.objects.get(pk=instance_id).mandat
        except DeclarationCotisations.DoesNotExist:
            return None
    return None


@login_required
@require_http_methods(["POST"])
def modele_pdf_save(request):
    """
    Sauvegarde (create ou update) un ModeleDocumentPDF depuis le Studio.

    Body JSON attendu :
    {
        "type_document": "FACTURE",
        "config": {
            "instance_id": "<uuid>",
            "couleur_primaire": "#02312e",
            "couleur_accent": "#2c3e50",
            "couleur_texte": "#333333",
            "police": "Helvetica",
            "marge_haut": 20,
            "marge_bas": 25,
            "marge_gauche": 20,
            "marge_droite": 15,
            "textes": { ... },
            "blocs_visibles": { ... }
        }
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    type_document = data.get('type_document')
    config = data.get('config', {})

    if not type_document:
        return JsonResponse({'error': 'type_document requis'}, status=400)

    valid_types = [c[0] for c in ModeleDocumentPDF.TypeDocument.choices]
    if type_document not in valid_types:
        return JsonResponse({'error': f'type_document invalide: {type_document}'}, status=400)

    mandat = _resolve_mandat(type_document, config)

    # Chercher un modèle existant pour ce type + mandat
    modele = ModeleDocumentPDF.objects.filter(
        type_document=type_document,
        mandat=mandat,
        est_defaut=True,
        is_active=True,
    ).first()

    if not modele:
        modele = ModeleDocumentPDF(
            type_document=type_document,
            mandat=mandat,
            est_defaut=True,
            created_by=request.user,
        )

    # Mise à jour des champs
    type_label = modele.get_type_document_display() if modele.pk else dict(ModeleDocumentPDF.TypeDocument.choices).get(type_document, type_document)
    mandat_label = str(mandat) if mandat else 'Système'
    modele.nom = f"{type_label} - {mandat_label}"
    modele.couleur_primaire = config.get('couleur_primaire', '#02312e')
    modele.couleur_accent = config.get('couleur_accent', '#2c3e50')
    modele.couleur_texte = config.get('couleur_texte', '#333333')
    modele.police = config.get('police', 'Helvetica')
    modele.marge_haut = config.get('marge_haut', 20)
    modele.marge_bas = config.get('marge_bas', 25)
    modele.marge_gauche = config.get('marge_gauche', 20)
    modele.marge_droite = config.get('marge_droite', 15)
    modele.textes = config.get('textes', {})
    modele.blocs_visibles = config.get('blocs_visibles', {})

    modele.save()

    return JsonResponse({
        'status': 'ok',
        'id': str(modele.pk),
        'nom': modele.nom,
    })
