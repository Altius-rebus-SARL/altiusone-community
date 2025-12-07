# core/views/export_views.py
"""
Vues d'export centralisées utilisant StreamingHttpResponse.
Ces vues remplacent les anciennes vues utilisant HttpResponse pour les téléchargements.
"""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import StreamingHttpResponse, HttpResponse
from django.utils.translation import gettext as _
from django.views import View

from core.services import ExportService, QRBillService
from core.permissions import permission_required_business, has_business_permission


# ============================================================================
# EXPORT FACTURATION
# ============================================================================

@login_required
@permission_required_business('facturation.export_factures')
def facture_export_pdf(request, pk):
    """Génère et télécharge le PDF d'une facture avec QR-Bill intégré."""
    from facturation.models import Facture

    facture = get_object_or_404(Facture, pk=pk)

    try:
        # Générer le PDF via la méthode du modèle
        fichier = facture.generer_pdf()

        # Streaming response pour les gros fichiers
        def file_iterator():
            with fichier.open('rb') as f:
                while chunk := f.read(8192):
                    yield chunk

        response = StreamingHttpResponse(
            file_iterator(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="facture_{facture.numero_facture}.pdf"'
        return response

    except Exception as e:
        messages.error(request, f"Erreur lors de la génération PDF: {str(e)}")
        return redirect('facturation:facture-detail', pk=pk)


@login_required
@permission_required_business('facturation.generate_qrbill')
def facture_generate_qrbill(request, pk):
    """Génère uniquement le QR-Bill d'une facture."""
    from facturation.models import Facture

    facture = get_object_or_404(Facture, pk=pk)

    try:
        # Générer la référence QR si pas encore fait
        if not facture.qr_reference:
            facture.generer_qr_reference()

        # Générer le QR-Bill
        facture.generer_qr_bill()

        messages.success(request, _("QR-Bill généré avec succès"))
        return redirect('facturation:facture-detail', pk=pk)

    except Exception as e:
        messages.error(request, f"Erreur lors de la génération du QR-Bill: {str(e)}")
        return redirect('facturation:facture-detail', pk=pk)


@login_required
@permission_required_business('facturation.export_factures')
def factures_export_csv(request):
    """Exporte la liste des factures en CSV (streaming)."""
    from facturation.models import Facture
    from django.db.models import Q

    # Récupérer les factures selon les filtres
    queryset = Facture.objects.select_related('client', 'mandat')

    # Appliquer les filtres de la requête
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    statut = request.GET.get('statut')
    client_id = request.GET.get('client')

    if date_debut:
        queryset = queryset.filter(date_emission__gte=date_debut)
    if date_fin:
        queryset = queryset.filter(date_emission__lte=date_fin)
    if statut:
        queryset = queryset.filter(statut=statut)
    if client_id:
        queryset = queryset.filter(client_id=client_id)

    # Filtrer selon les permissions
    user = request.user
    if not user.is_superuser and user.role not in ['ADMIN', 'MANAGER']:
        if not has_business_permission(user, 'facturation.view_all_factures'):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

    queryset = queryset.order_by('-date_emission')

    # Définir les champs à exporter
    fields = [
        'numero_facture',
        'client__raison_sociale',
        'date_emission',
        'date_echeance',
        'montant_ht',
        'montant_tva',
        'montant_ttc',
        'montant_paye',
        'montant_restant',
        'statut',
    ]

    field_labels = {
        'numero_facture': 'N° Facture',
        'client__raison_sociale': 'Client',
        'date_emission': 'Date émission',
        'date_echeance': 'Date échéance',
        'montant_ht': 'Montant HT',
        'montant_tva': 'Montant TVA',
        'montant_ttc': 'Montant TTC',
        'montant_paye': 'Montant payé',
        'montant_restant': 'Montant restant',
        'statut': 'Statut',
    }

    return ExportService.generate_csv_from_queryset(
        queryset=queryset,
        fields=fields,
        field_labels=field_labels,
        filename=f"factures_export_{request.user.username}"
    )


@login_required
@permission_required_business('facturation.export_factures')
def factures_export_excel(request):
    """Exporte la liste des factures en Excel (streaming)."""
    from facturation.models import Facture
    from django.db.models import Q

    queryset = Facture.objects.select_related('client', 'mandat')

    # Mêmes filtres que CSV
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    statut = request.GET.get('statut')
    client_id = request.GET.get('client')

    if date_debut:
        queryset = queryset.filter(date_emission__gte=date_debut)
    if date_fin:
        queryset = queryset.filter(date_emission__lte=date_fin)
    if statut:
        queryset = queryset.filter(statut=statut)
    if client_id:
        queryset = queryset.filter(client_id=client_id)

    user = request.user
    if not user.is_superuser and user.role not in ['ADMIN', 'MANAGER']:
        if not has_business_permission(user, 'facturation.view_all_factures'):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

    queryset = queryset.order_by('-date_emission')

    fields = [
        'numero_facture',
        'client__raison_sociale',
        'date_emission',
        'date_echeance',
        'montant_ht',
        'montant_tva',
        'montant_ttc',
        'montant_paye',
        'montant_restant',
        'statut',
    ]

    field_labels = {
        'numero_facture': 'N° Facture',
        'client__raison_sociale': 'Client',
        'date_emission': 'Date émission',
        'date_echeance': 'Date échéance',
        'montant_ht': 'Montant HT',
        'montant_tva': 'Montant TVA',
        'montant_ttc': 'Montant TTC',
        'montant_paye': 'Montant payé',
        'montant_restant': 'Montant restant',
        'statut': 'Statut',
    }

    return ExportService.generate_excel_streaming(
        queryset=queryset,
        fields=fields,
        field_labels=field_labels,
        filename=f"factures_export_{request.user.username}",
        sheet_name='Factures'
    )


# ============================================================================
# EXPORT TVA
# ============================================================================

@login_required
@permission_required_business('tva.export_tva')
def declaration_tva_export_xml(request, pk):
    """Exporte une déclaration TVA au format XML AFC (streaming)."""
    from tva.models import DeclarationTVA

    declaration = get_object_or_404(DeclarationTVA, pk=pk)

    try:
        # Générer le XML via la méthode du modèle
        fichier = declaration.generer_xml()

        # Streaming response
        def file_iterator():
            with fichier.open('rb') as f:
                while chunk := f.read(8192):
                    yield chunk

        response = StreamingHttpResponse(
            file_iterator(),
            content_type='application/xml'
        )
        response['Content-Disposition'] = f'attachment; filename="TVA_{declaration.numero_declaration}.xml"'
        return response

    except Exception as e:
        messages.error(request, f"Erreur lors de la génération XML: {str(e)}")
        return redirect('tva:declaration-detail', pk=pk)


@login_required
@permission_required_business('tva.export_tva')
def declaration_tva_export_pdf(request, pk):
    """Exporte une déclaration TVA au format PDF (streaming)."""
    from tva.models import DeclarationTVA

    declaration = get_object_or_404(DeclarationTVA, pk=pk)

    try:
        fichier = declaration.generer_pdf()

        def file_iterator():
            with fichier.open('rb') as f:
                while chunk := f.read(8192):
                    yield chunk

        response = StreamingHttpResponse(
            file_iterator(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="TVA_{declaration.numero_declaration}.pdf"'
        return response

    except Exception as e:
        messages.error(request, f"Erreur lors de la génération PDF: {str(e)}")
        return redirect('tva:declaration-detail', pk=pk)


@login_required
@permission_required_business('tva.export_tva')
def declarations_tva_export_csv(request):
    """Exporte la liste des déclarations TVA en CSV."""
    from tva.models import DeclarationTVA
    from django.db.models import Q

    queryset = DeclarationTVA.objects.select_related('mandat__client')

    # Filtres
    annee = request.GET.get('annee')
    statut = request.GET.get('statut')
    mandat_id = request.GET.get('mandat')

    if annee:
        queryset = queryset.filter(annee=annee)
    if statut:
        queryset = queryset.filter(statut=statut)
    if mandat_id:
        queryset = queryset.filter(mandat_id=mandat_id)

    user = request.user
    if not user.is_superuser and user.role not in ['ADMIN', 'MANAGER']:
        if not has_business_permission(user, 'tva.view_all_declarations'):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

    queryset = queryset.order_by('-annee', '-trimestre')

    fields = [
        'numero_declaration',
        'mandat__client__raison_sociale',
        'annee',
        'trimestre',
        'semestre',
        'chiffre_affaires_total',
        'tva_due_total',
        'tva_prealable_total',
        'solde_tva',
        'statut',
    ]

    field_labels = {
        'numero_declaration': 'N° Déclaration',
        'mandat__client__raison_sociale': 'Client',
        'annee': 'Année',
        'trimestre': 'Trimestre',
        'semestre': 'Semestre',
        'chiffre_affaires_total': 'CA Total',
        'tva_due_total': 'TVA Due',
        'tva_prealable_total': 'TVA Préalable',
        'solde_tva': 'Solde TVA',
        'statut': 'Statut',
    }

    return ExportService.generate_csv_from_queryset(
        queryset=queryset,
        fields=fields,
        field_labels=field_labels,
        filename=f"declarations_tva_export"
    )


# ============================================================================
# EXPORT COMPTABILITÉ
# ============================================================================

@login_required
@permission_required_business('comptabilite.export_comptabilite')
def balance_export(request, format_type='pdf'):
    """Exporte la balance au format spécifié."""
    from comptabilite.models import Compte, EcritureComptable
    from django.db.models import Sum, Q
    from datetime import date

    # Récupérer les paramètres
    mandat_id = request.GET.get('mandat')
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')

    if not mandat_id:
        messages.error(request, _("Mandat requis pour l'export"))
        return redirect('comptabilite:balance')

    # Parser les dates
    try:
        date_debut = date.fromisoformat(date_debut_str) if date_debut_str else date(date.today().year, 1, 1)
        date_fin = date.fromisoformat(date_fin_str) if date_fin_str else date.today()
    except ValueError:
        date_debut = date(date.today().year, 1, 1)
        date_fin = date.today()

    # Récupérer les comptes avec leurs soldes
    # Note: Cette requête doit être adaptée à votre modèle exact
    comptes = Compte.objects.filter(
        ecritures__piece__mandat_id=mandat_id,
        ecritures__piece__date_piece__gte=date_debut,
        ecritures__piece__date_piece__lte=date_fin,
    ).annotate(
        debit=Sum('ecritures__montant_debit'),
        credit=Sum('ecritures__montant_credit'),
    ).order_by('numero')

    # Formatter les données
    comptes_data = [
        {
            'numero': c.numero,
            'libelle': c.libelle,
            'debit': c.debit or 0,
            'credit': c.credit or 0,
            'solde': (c.debit or 0) - (c.credit or 0),
        }
        for c in comptes
    ]

    return ExportService.export_balance(
        comptes=comptes_data,
        titre=f"Balance des comptes",
        date_debut=date_debut,
        date_fin=date_fin,
        format_type=format_type
    )


@login_required
@permission_required_business('comptabilite.export_comptabilite')
def grand_livre_export_csv(request):
    """Exporte le grand livre en CSV."""
    from comptabilite.models import EcritureComptable
    from django.db.models import Q

    mandat_id = request.GET.get('mandat')
    compte_id = request.GET.get('compte')

    if not mandat_id:
        messages.error(request, _("Mandat requis"))
        return redirect('comptabilite:grand-livre')

    queryset = EcritureComptable.objects.filter(
        piece__mandat_id=mandat_id
    ).select_related('compte', 'piece')

    if compte_id:
        queryset = queryset.filter(compte_id=compte_id)

    queryset = queryset.order_by('compte__numero', 'piece__date_piece')

    fields = [
        'compte__numero',
        'compte__libelle',
        'piece__date_piece',
        'piece__numero',
        'libelle',
        'montant_debit',
        'montant_credit',
    ]

    field_labels = {
        'compte__numero': 'N° Compte',
        'compte__libelle': 'Libellé compte',
        'piece__date_piece': 'Date',
        'piece__numero': 'N° Pièce',
        'libelle': 'Libellé',
        'montant_debit': 'Débit',
        'montant_credit': 'Crédit',
    }

    return ExportService.generate_csv_from_queryset(
        queryset=queryset,
        fields=fields,
        field_labels=field_labels,
        filename='grand_livre_export'
    )


# ============================================================================
# EXPORT SALAIRES
# ============================================================================

@login_required
@permission_required_business('salaires.export_salaires')
def fiches_salaire_export_csv(request):
    """Exporte les fiches de salaire en CSV."""
    from salaires.models import FicheSalaire
    from django.db.models import Q

    queryset = FicheSalaire.objects.select_related('employe', 'mandat')

    # Filtres
    annee = request.GET.get('annee')
    mois = request.GET.get('mois')
    mandat_id = request.GET.get('mandat')

    if annee:
        queryset = queryset.filter(annee=annee)
    if mois:
        queryset = queryset.filter(mois=mois)
    if mandat_id:
        queryset = queryset.filter(mandat_id=mandat_id)

    user = request.user
    if not user.is_superuser and user.role not in ['ADMIN', 'MANAGER']:
        if not has_business_permission(user, 'salaires.view_all_fiches'):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

    queryset = queryset.order_by('-annee', '-mois', 'employe__nom')

    fields = [
        'employe__nom',
        'employe__prenom',
        'annee',
        'mois',
        'salaire_brut',
        'cotisations_employe',
        'impot_source',
        'salaire_net',
        'statut',
    ]

    field_labels = {
        'employe__nom': 'Nom',
        'employe__prenom': 'Prénom',
        'annee': 'Année',
        'mois': 'Mois',
        'salaire_brut': 'Salaire brut',
        'cotisations_employe': 'Cotisations',
        'impot_source': 'Impôt source',
        'salaire_net': 'Salaire net',
        'statut': 'Statut',
    }

    return ExportService.generate_csv_from_queryset(
        queryset=queryset,
        fields=fields,
        field_labels=field_labels,
        filename='fiches_salaire_export'
    )


# ============================================================================
# EXPORT ANALYTICS
# ============================================================================

@login_required
@permission_required_business('analytics.export_donnees')
def rapport_telecharger(request, pk):
    """Télécharge un rapport généré (streaming)."""
    from analytics.models import Rapport

    rapport = get_object_or_404(Rapport, pk=pk)

    if not rapport.fichier:
        messages.error(request, _("Fichier non trouvé"))
        return redirect('analytics:rapport-detail', pk=pk)

    def file_iterator():
        with rapport.fichier.open('rb') as f:
            while chunk := f.read(8192):
                yield chunk

    content_type = ExportService.get_content_type(rapport.format_fichier.lower())

    response = StreamingHttpResponse(
        file_iterator(),
        content_type=content_type
    )
    response['Content-Disposition'] = f'attachment; filename="{rapport.nom}.{rapport.format_fichier.lower()}"'
    return response


@login_required
@permission_required_business('analytics.export_donnees')
def export_telecharger(request, pk):
    """Télécharge un export de données (streaming)."""
    from analytics.models import ExportDonnees
    from datetime import datetime

    export = get_object_or_404(ExportDonnees, pk=pk)

    # Vérifier expiration
    if export.date_expiration and export.date_expiration < datetime.now():
        messages.error(request, _("Ce lien d'export a expiré"))
        return redirect('analytics:export-list')

    if not export.fichier:
        messages.error(request, _("Fichier non trouvé"))
        return redirect('analytics:export-list')

    def file_iterator():
        with export.fichier.open('rb') as f:
            while chunk := f.read(8192):
                yield chunk

    content_type = ExportService.get_content_type(export.format_export.lower())

    response = StreamingHttpResponse(
        file_iterator(),
        content_type=content_type
    )
    response['Content-Disposition'] = f'attachment; filename="{export.nom}.{export.format_export.lower()}"'
    return response
