# facturation/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from core.permissions import BusinessPermissionMixin, permission_required_business
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q, Count, Sum, Avg, F, Max, Min, Prefetch
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.forms import inlineformset_factory
from .models import (
    Prestation, TimeTracking, Facture, LigneFacture, Paiement, Relance,
    ZoneGeographique, TarifMandat,
)
from .forms import (
    PrestationForm,
    TimeTrackingForm,
    FactureForm,
    LigneFactureForm,
    PaiementForm,
    LigneFactureFormSet,
    RelanceForm,
    TarifMandatForm,
    ZoneGeographiqueForm,
)
from .filters import FactureFilter, TimeTrackingFilter, PaiementFilter
from core.models import Mandat, Client
from tva.utils import get_taux_tva_defaut


def _get_tva_context(mandat=None):
    """Retourne les variables TVA pour les templates facturation."""
    from tva.models import RegimeFiscal, TauxTVA
    ctx = {'taux_tva_defaut': get_taux_tva_defaut(mandat)}
    try:
        if mandat and hasattr(mandat, 'config_tva') and mandat.config_tva and mandat.config_tva.regime:
            regime = mandat.config_tva.regime
        else:
            regime = RegimeFiscal.objects.filter(code='CH').first()
        if regime:
            ctx['taux_tva_normal'] = regime.taux_normal
            from datetime import date
            today = date.today()
            reduit = TauxTVA.objects.filter(
                regime=regime, type_taux='REDUIT',
                date_debut__lte=today,
            ).filter(
                Q(date_fin__isnull=True) | Q(date_fin__gte=today)
            ).first()
            if reduit:
                ctx['taux_tva_reduit'] = reduit.taux
            special = TauxTVA.objects.filter(
                regime=regime, type_taux='SPECIAL',
                date_debut__lte=today,
            ).filter(
                Q(date_fin__isnull=True) | Q(date_fin__gte=today)
            ).first()
            if special:
                ctx['taux_tva_special'] = special.taux
    except Exception:
        pass
    return ctx


# ============ PRESTATIONS ============


class PrestationListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des prestations"""

    model = Prestation
    business_permission = 'facturation.view_prestations'
    template_name = "facturation/prestation_list.html"
    context_object_name = "prestations"
    paginate_by = 50

    def get_queryset(self):
        queryset = Prestation.objects.annotate(nb_lignes_facture=Count("lignefacture"))

        # Filtrer par type
        type_prestation = self.request.GET.get("type")
        if type_prestation:
            queryset = queryset.filter(type_prestation=type_prestation)

        # Filtrer par actif
        actif = self.request.GET.get("actif")
        if actif:
            queryset = queryset.filter(actif=actif == "true")

        return queryset.order_by("code")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["stats"] = {
            "total": self.get_queryset().count(),
            "actives": self.get_queryset().filter(actif=True).count(),
            "par_type": self.get_queryset()
            .values("type_prestation")
            .annotate(count=Count("id")),
        }

        return context


class PrestationDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une prestation"""

    model = Prestation
    business_permission = 'facturation.view_prestations'
    template_name = "facturation/prestation_detail.html"
    context_object_name = "prestation"


class PrestationCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une prestation"""

    model = Prestation
    form_class = PrestationForm
    template_name = "facturation/prestation_form.html"
    business_permission = 'facturation.view_prestations'
    success_url = reverse_lazy("facturation:prestation-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_tva_context())
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Prestation créée avec succès"))
        return super().form_valid(form)

class PrestationUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une prestation"""

    model = Prestation
    form_class = PrestationForm
    template_name = "facturation/prestation_form.html"
    business_permission = 'facturation.view_prestations'
    success_url = reverse_lazy("facturation:prestation-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_tva_context())
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Prestation modifiée avec succès"))
        return super().form_valid(form)

# ============ TIME TRACKING ============


class TimeTrackingListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste du suivi du temps"""

    model = TimeTracking
    business_permission = 'facturation.view_timetracking'
    template_name = "facturation/timetracking_list.html"
    context_object_name = "temps"
    paginate_by = 50

    def get_queryset(self):
        queryset = TimeTracking.objects.select_related(
            "mandat__client", "utilisateur", "prestation", "facture"
        )

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager() and user.has_perm("facturation.view_all_timetracking"):
            queryset = queryset.filter(
                Q(utilisateur=user)
                | Q(mandat__responsable=user)
                | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = TimeTrackingFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-date_travail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        user = self.request.user
        is_manager = user.is_manager()
        context["is_manager"] = is_manager

        # Statistiques
        queryset = self.get_queryset()

        stats = {
            "total_heures": queryset.aggregate(total=Sum("duree_minutes"))["total"]
            or 0,
            "total_heures_display": (
                queryset.aggregate(total=Sum("duree_minutes"))["total"] or 0
            )
            / 60,
            "non_facture": queryset.filter(
                facturable=True, facture__isnull=True
            ).count(),
        }

        # Stats financières uniquement pour manager
        if is_manager:
            stats["montant_non_facture"] = queryset.filter(
                facturable=True, facture__isnull=True
            ).aggregate(Sum("montant_ht"))["montant_ht__sum"] or 0

        context["stats"] = stats

        # Temps par utilisateur (si admin/manager)
        if is_manager:
            context["temps_par_utilisateur"] = (
                queryset.values(
                    "utilisateur__username",
                    "utilisateur__first_name",
                    "utilisateur__last_name",
                )
                .annotate(
                    total_minutes=Sum("duree_minutes"), total_montant=Sum("montant_ht")
                )
                .order_by("-total_minutes")
            )

        return context


class TimeTrackingCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Saisie de temps"""

    model = TimeTracking
    business_permission = 'facturation.view_timetracking'
    form_class = TimeTrackingForm
    template_name = "facturation/timetracking_form.html"
    success_url = reverse_lazy("facturation:timetracking-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["utilisateur"] = self.request.user
        initial["date_travail"] = datetime.now().date()
        initial["facturable"] = True
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_manager"] = self.request.user.is_manager()
        # Zones pour le JS (Leaflet)
        zones = ZoneGeographique.objects.filter(is_active=True).values(
            "id", "nom", "couleur"
        )
        context["zones_json"] = json.dumps(list(zones), default=str)
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        # Forcer utilisateur pour non-managers
        if not self.request.user.is_manager():
            form.instance.utilisateur = self.request.user

        # Calcul automatique du montant si taux horaire défini
        if form.instance.taux_horaire and form.instance.duree_minutes:
            heures = Decimal(form.instance.duree_minutes) / Decimal("60")
            form.instance.montant_ht = (heures * form.instance.taux_horaire).quantize(
                Decimal("0.01")
            )

        messages.success(self.request, _("Temps enregistré avec succès"))
        return super().form_valid(form)


# ============ FACTURES ============


class FactureListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des factures"""

    model = Facture
    business_permission = 'facturation.view_factures'
    template_name = "facturation/facture_list.html"
    context_object_name = "factures"
    paginate_by = 50

    def get_queryset(self):
        queryset = Facture.objects.select_related(
            "mandat__client", "client", "creee_par"
        ).prefetch_related("lignes")

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager() and not user.has_perm("facturation.view_all_factures"):
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        self.filterset = FactureFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-date_emission")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()

        context["stats"] = {
            "total": queryset.count(),
            "brouillon": queryset.filter(statut="BROUILLON").count(),
            "emises": queryset.filter(statut="EMISE").count(),
            "en_retard": queryset.filter(statut="EN_RETARD").count(),
            "payees": queryset.filter(statut="PAYEE").count(),
            "ca_total": queryset.aggregate(Sum("montant_ttc"))["montant_ttc__sum"] or 0,
            "ca_annee": queryset.filter(
                date_emission__year=datetime.now().year
            ).aggregate(Sum("montant_ttc"))["montant_ttc__sum"]
            or 0,
            "impaye_total": queryset.exclude(statut="PAYEE").aggregate(
                Sum("montant_restant")
            )["montant_restant__sum"]
            or 0,
        }

        # Évolution CA par mois (6 derniers mois)
        evolution_ca = []
        for i in range(5, -1, -1):
            date = datetime.now() - timedelta(days=30 * i)
            ca_mois = (
                queryset.filter(
                    date_emission__year=date.year, date_emission__month=date.month
                ).aggregate(Sum("montant_ttc"))["montant_ttc__sum"]
                or 0
            )

            evolution_ca.append({"mois": date.strftime("%Y-%m"), "ca": float(ca_mois)})

        context["evolution_ca"] = json.dumps(evolution_ca)

        return context


class FactureDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une facture"""

    model = Facture
    business_permission = 'facturation.view_factures'
    template_name = "facturation/facture_detail.html"
    context_object_name = "facture"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "mandat__client",
                "client",
                "creee_par",
                "validee_par",
                "facture_origine",
            )
            .prefetch_related(
                "lignes__prestation", "lignes__temps_factures", "paiements", "relances"
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        facture = self.object

        # Paiements
        context["paiements"] = facture.paiements.all().order_by("-date_paiement")

        # Relances
        context["relances"] = facture.relances.all().order_by("-date_relance")

        # Temps facturés
        temps_factures = TimeTracking.objects.none()
        for ligne in facture.lignes.all():
            temps_factures = temps_factures | ligne.temps_factures.all()
        context["temps_factures"] = temps_factures

        # Avoirs liés
        context["avoirs"] = Facture.objects.filter(
            facture_origine=facture, type_facture="AVOIR"
        )

        return context


class FactureCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une facture avec lignes"""

    model = Facture
    form_class = FactureForm
    template_name = "facturation/facture_form.html"
    business_permission = 'facturation.add_facture'

    def get_initial(self):
        initial = super().get_initial()

        # Préremplir avec le mandat si fourni
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            mandat = get_object_or_404(Mandat, pk=mandat_id)
            initial["mandat"] = mandat
            initial["client"] = mandat.client

        initial["date_emission"] = datetime.now().date()
        initial["delai_paiement_jours"] = 30

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = LigneFactureFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = LigneFactureFormSet(instance=self.object)

        # Prestations pour l'autocomplete
        context["prestations"] = Prestation.objects.filter(actif=True).values(
            "id", "libelle", "prix_unitaire_ht", "unite", "taux_tva_defaut"
        )

        # TVA context
        mandat = None
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            mandat = Mandat.objects.filter(pk=mandat_id).first()
        context.update(_get_tva_context(mandat))

        return context

    def get_success_url(self):
        return reverse_lazy("facturation:facture-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            form.instance.creee_par = self.request.user
            self.object = form.save()

            formset.instance = self.object
            formset.save()

            # Recalculer les totaux
            self.object.calculer_totaux()

            messages.success(self.request, _("Facture créée avec succès"))
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class FactureUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une facture"""

    model = Facture
    form_class = FactureForm
    template_name = "facturation/facture_form.html"
    business_permission = 'facturation.add_facture'

    def get_queryset(self):
        # Ne peut modifier que les factures en brouillon
        return super().get_queryset().filter(statut="BROUILLON")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["formset"] = LigneFactureFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["formset"] = LigneFactureFormSet(instance=self.object)

        # Prestations pour l'autocomplete
        context["prestations"] = Prestation.objects.filter(actif=True).values(
            "id", "libelle", "prix_unitaire_ht", "unite", "taux_tva_defaut"
        )

        # TVA context
        mandat = self.object.mandat if self.object else None
        context.update(_get_tva_context(mandat))

        return context

    def get_success_url(self):
        return reverse_lazy("facturation:facture-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context["formset"]

        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

            # Recalculer les totaux
            self.object.calculer_totaux()

            messages.success(self.request, _("Facture modifiée avec succès"))
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


# facturation/views.py - Ajouter ces vues


@login_required
def ligne_facture_form_row(request):
    """Retourne une nouvelle ligne de formulaire vide"""
    index = int(request.GET.get("index", 0))

    # Créer un formset vide avec un seul formulaire
    
    FormSet = inlineformset_factory(
        Facture, LigneFacture, form=LigneFactureForm, extra=1, can_delete=True
    )
    formset = FormSet()
    form = formset.forms[0]

    # Remplacer le prefix
    form.prefix = form.prefix.replace("0", str(index))

    prestations = Prestation.objects.filter(actif=True).values(
        "id", "libelle", "prix_unitaire_ht", "unite", "taux_tva_defaut"
    )

    ctx = {
        "ligne_form": form,
        "index": index,
        "prestations": prestations,
    }
    ctx.update(_get_tva_context())

    return render(
        request,
        "facturation/partials/ligne_facture_row.html",
        ctx,
    )


@login_required
@require_http_methods(["DELETE"])
def ligne_facture_delete_row(request, index):
    """Marque une ligne pour suppression"""
    return HttpResponse(status=200)


@login_required
@require_http_methods(["POST"])
def facture_valider(request, pk):
    """Valide une facture"""
    facture = get_object_or_404(Facture, pk=pk, statut="BROUILLON")

    try:
        facture.valider(request.user)
        messages.success(request, _("Facture validée avec succès"))
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("facturation:facture-detail", pk=pk)


@login_required
def facture_generer_pdf(request, pk):
    """
    Génère le PDF d'une facture.

    Paramètres GET:
        - qr_bill: Si "1" ou "true", génère avec QR-Bill suisse
    """
    from core.pdf import serve_pdf

    facture = get_object_or_404(Facture, pk=pk)

    # Option QR-Bill
    qr_bill_param = request.GET.get('qr_bill', '').lower()
    avec_qr_bill = qr_bill_param in ('1', 'true', 'yes', 'oui')

    try:
        facture.generer_pdf(avec_qr_bill=avec_qr_bill)
    except Exception as e:
        messages.error(request, _("Erreur lors de la génération: %(error)s") % {'error': str(e)})
        return redirect("facturation:facture-detail", pk=pk)

    suffix = "_qr" if avec_qr_bill else ""
    filename = f"facture_{facture.numero_facture}{suffix}.pdf"
    return serve_pdf(
        request, facture, 'fichier_pdf', filename,
        ("facturation:facture-detail", pk),
        generate=False,
    )


@login_required
def facture_preview_pdf(request, pk):
    """Aperçu inline du PDF d'une facture dans le navigateur."""
    from core.pdf import serve_pdf

    facture = get_object_or_404(Facture, pk=pk)
    return serve_pdf(
        request, facture, 'fichier_pdf',
        f"facture_{facture.numero_facture}.pdf",
        ("facturation:facture-detail", pk),
        generate=True, inline=True,
    )


@login_required
def facture_envoyer_email(request, pk):
    """Envoie la facture par email au client"""
    from django.core.mail import EmailMessage
    from django.template.loader import render_to_string
    from django.conf import settings

    facture = get_object_or_404(Facture, pk=pk)

    # Vérifier qu'on a une adresse email
    destinataire = facture.client.email
    if not destinataire:
        # Essayer de récupérer l'email du contact principal
        contact_principal = facture.client.contacts.filter(principal=True).first()
        if contact_principal:
            destinataire = contact_principal.email

    if not destinataire:
        messages.error(request, _("Aucune adresse email trouvée pour ce client"))
        return redirect("facturation:facture-detail", pk=pk)

    # Générer le PDF si pas encore fait
    if not facture.fichier_pdf:
        try:
            facture.generer_pdf()
        except Exception as e:
            messages.error(request, _("Erreur lors de la génération du PDF: %(error)s") % {'error': str(e)})
            return redirect("facturation:facture-detail", pk=pk)

    # Préparer le contenu de l'email
    context = {
        'facture': facture,
        'client': facture.client,
        'mandat': facture.mandat,
    }

    # Sujet de l'email
    if facture.type_facture == 'AVOIR':
        sujet = f"Avoir N° {facture.numero_facture}"
    else:
        sujet = f"Facture N° {facture.numero_facture}"

    # Corps de l'email (HTML)
    try:
        corps_html = render_to_string('facturation/email/facture_email.html', context)
    except Exception:
        # Template par défaut si le template n'existe pas
        corps_html = f"""
        <html>
        <body>
        <p>Bonjour,</p>
        <p>Veuillez trouver ci-joint la facture N° {facture.numero_facture}
        d'un montant de CHF {facture.montant_ttc:,.2f}.</p>
        <p>Date d'échéance : {facture.date_echeance.strftime('%d.%m.%Y')}</p>
        <p>Nous vous remercions de votre confiance.</p>
        <p>Cordialement,<br>
        {facture.mandat.client.raison_sociale}</p>
        </body>
        </html>
        """

    # Corps texte simple
    corps_texte = f"""
Bonjour,

Veuillez trouver ci-joint la facture N° {facture.numero_facture}
d'un montant de CHF {facture.montant_ttc:,.2f}.

Date d'échéance : {facture.date_echeance.strftime('%d.%m.%Y')}

Nous vous remercions de votre confiance.

Cordialement,
{facture.mandat.client.raison_sociale}
"""

    try:
        # Créer l'email
        email = EmailMessage(
            subject=sujet,
            body=corps_texte,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinataire],
            reply_to=[facture.mandat.client.email] if facture.mandat.client.email else None,
        )

        # Ajouter le contenu HTML
        email.content_subtype = 'html'
        email.body = corps_html

        # Attacher le PDF
        if facture.fichier_pdf:
            email.attach_file(facture.fichier_pdf.path)

        # Envoyer
        email.send(fail_silently=False)

        # Mettre à jour le statut
        facture.statut = "ENVOYEE"
        facture.save()

        messages.success(request, _("Facture envoyée par email à %(email)s") % {'email': destinataire})

    except Exception as e:
        messages.error(request, _("Erreur lors de l'envoi de l'email: %(error)s") % {'error': str(e)})

    return redirect("facturation:facture-detail", pk=pk)


# ============ LIGNES DE FACTURE ============


@login_required
def ligne_facture_create(request, facture_pk):
    """Ajoute une ligne à une facture"""
    facture = get_object_or_404(Facture, pk=facture_pk, statut="BROUILLON")

    if request.method == "POST":
        form = LigneFactureForm(request.POST)
        if form.is_valid():
            ligne = form.save(commit=False)
            ligne.facture = facture

            # Ordre
            dernier_ordre = facture.lignes.aggregate(Max("ordre"))["ordre__max"] or 0
            ligne.ordre = dernier_ordre + 1

            ligne.save()

            # Recalculer la facture
            facture.calculer_totaux()

            messages.success(request, _("Ligne ajoutée avec succès"))
            return redirect("facturation:facture-detail", pk=facture.pk)
    else:
        form = LigneFactureForm()

    return render(
        request, "facturation/ligne_form.html", {"form": form, "facture": facture}
    )


@login_required
def ligne_facture_delete(request, pk):
    """Supprime une ligne de facture"""
    ligne = get_object_or_404(LigneFacture, pk=pk)
    facture = ligne.facture

    if facture.statut != "BROUILLON":
        messages.error(
            request, _("Impossible de supprimer une ligne d'une facture validée")
        )
        return redirect("facturation:facture-detail", pk=facture.pk)

    ligne.delete()
    facture.calculer_totaux()

    messages.success(request, _("Ligne supprimée avec succès"))
    return redirect("facturation:facture-detail", pk=facture.pk)


# ============ PAIEMENTS ============


# facturation/views.py


class PaiementListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des paiements"""

    model = Paiement
    business_permission = 'facturation.view_paiements'
    template_name = "facturation/paiement_list.html"
    context_object_name = "paiements"
    paginate_by = 50

    def get_queryset(self):
        # Queryset de base
        queryset = Paiement.objects.select_related(
            "facture__client", "facture__mandat", "valide_par"
        ).filter(is_active=True)

        # Appliquer les filtres SEULEMENT s'il y a des paramètres
        if self.request.GET:
            self.filterset = PaiementFilter(self.request.GET, queryset=queryset)
            return self.filterset.qs.order_by("-date_paiement")
        else:
            # Pas de filtres = tout afficher
            self.filterset = PaiementFilter(queryset=queryset)  # Filterset vide
            return queryset.order_by("-date_paiement")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.object_list  # Utiliser object_list au lieu de get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "valides": queryset.filter(valide=True).count(),
            "montant_total": queryset.filter(valide=True).aggregate(Sum("montant"))[
                "montant__sum"
            ]
            or 0,
            "montant_mois": queryset.filter(
                valide=True,
                date_paiement__year=datetime.now().year,
                date_paiement__month=datetime.now().month,
            ).aggregate(Sum("montant"))["montant__sum"]
            or 0,
        }

        return context


@login_required
def paiement_create(request, facture_pk):
    """Enregistre un paiement pour une facture"""
    facture = get_object_or_404(Facture, pk=facture_pk)

    if request.method == "POST":
        form = PaiementForm(request.POST)
        if form.is_valid():
            try:
                paiement = facture.enregistrer_paiement(
                    montant=form.cleaned_data["montant"],
                    date_paiement=form.cleaned_data["date_paiement"],
                    mode_paiement=form.cleaned_data["mode_paiement"],
                    reference=form.cleaned_data.get("reference", ""),
                    user=request.user,
                )
                messages.success(request, _("Paiement enregistré avec succès"))
                return redirect("facturation:facture-detail", pk=facture.pk)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = PaiementForm(
            initial={
                "montant": facture.montant_restant,
                "date_paiement": datetime.now().date(),
            }
        )

    return render(
        request, "facturation/paiement_form.html", {"form": form, "facture": facture}
    )


@login_required
@require_http_methods(["POST"])
def paiement_valider(request, pk):
    """Valide un paiement"""
    paiement = get_object_or_404(Paiement, pk=pk, valide=False)

    paiement.valide = True
    paiement.valide_par = request.user
    paiement.date_validation = datetime.now()
    paiement.save()

    messages.success(request, _("Paiement validé avec succès"))
    return redirect("facturation:facture-detail", pk=paiement.facture.pk)


# ============ RELANCES ============


@login_required
def relance_create(request, facture_pk):
    """Crée une relance pour une facture"""
    facture = get_object_or_404(Facture, pk=facture_pk)

    try:
        relance = facture.creer_relance(user=request.user)
        messages.success(request, _("Relance créée avec succès"))
        return redirect("facturation:facture-detail", pk=facture.pk)
    except Exception as e:
        messages.error(request, str(e))
        return redirect("facturation:facture-detail", pk=facture.pk)


# ============ TAUX HORAIRE API ============


@login_required
def get_taux_horaire(request):
    """Endpoint HTMX/JSON : retourne le taux horaire selon la cascade TarifMandat → Prestation → Mandat"""
    mandat_id = request.GET.get("mandat")
    prestation_id = request.GET.get("prestation")

    taux = None
    source = None

    if mandat_id and prestation_id:
        # 1. TarifMandat spécifique
        tarif = TarifMandat.objects.filter(
            mandat_id=mandat_id, prestation_id=prestation_id, is_active=True,
        ).first()
        if tarif and tarif.est_valide():
            taux = float(tarif.taux_horaire)
            source = "tarif_mandat"

    if taux is None and prestation_id:
        # 2. Taux de la prestation
        try:
            prestation = Prestation.objects.get(pk=prestation_id)
            if prestation.taux_horaire:
                taux = float(prestation.taux_horaire)
                source = "prestation"
        except Prestation.DoesNotExist:
            pass

    if taux is None and mandat_id:
        # 3. Taux du mandat
        try:
            mandat = Mandat.objects.get(pk=mandat_id)
            if mandat.taux_horaire:
                taux = float(mandat.taux_horaire)
                source = "mandat"
        except Mandat.DoesNotExist:
            pass

    # Budget info du mandat
    budget_info = None
    if mandat_id:
        try:
            mandat_obj = Mandat.objects.get(pk=mandat_id)
            budget_info = {
                "budget_prevu": float(mandat_obj.budget_prevu) if mandat_obj.budget_prevu else 0,
                "budget_reel": float(mandat_obj.budget_reel) if mandat_obj.budget_reel else 0,
            }
            if budget_info["budget_prevu"] > 0:
                budget_info["pourcent"] = round(
                    budget_info["budget_reel"] / budget_info["budget_prevu"] * 100, 1
                )
            else:
                budget_info["pourcent"] = 0
        except Mandat.DoesNotExist:
            pass

    return JsonResponse({"taux_horaire": taux, "source": source, "budget_info": budget_info})


@login_required
def get_positions(request):
    """API JSON : positions d'un mandat pour cascade Select2"""
    mandat_id = request.GET.get("mandat")
    if not mandat_id:
        return JsonResponse([], safe=False)

    from projets.models import Position
    positions = Position.objects.filter(
        mandat_id=mandat_id, is_active=True
    ).order_by("ordre", "numero")

    data = [
        {
            "id": str(p.id),
            "text": f"{p.numero} - {p.titre}",
            "budget_prevu": float(p.budget_prevu),
            "budget_reel": float(p.budget_reel),
        }
        for p in positions
    ]
    return JsonResponse(data, safe=False)


@login_required
def get_operations(request):
    """API JSON : opérations d'une position pour cascade Select2"""
    position_id = request.GET.get("position")
    if not position_id:
        return JsonResponse([], safe=False)

    from projets.models import Operation
    operations = Operation.objects.filter(
        position_id=position_id, is_active=True
    ).order_by("ordre", "numero")

    data = [
        {
            "id": str(o.id),
            "text": f"{o.numero} - {o.titre}",
            "cout_reel": float(o.cout_reel),
            "statut": o.statut,
        }
        for o in operations
    ]
    return JsonResponse(data, safe=False)


# ============ TARIFS MANDAT ============


class TarifMandatListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des tarifs mandat"""

    model = TarifMandat
    business_permission = 'facturation.view_prestations'
    template_name = "facturation/tarif_list.html"
    context_object_name = "tarifs"
    paginate_by = 50

    def get_queryset(self):
        return TarifMandat.objects.select_related(
            "mandat__client", "prestation"
        ).filter(is_active=True).order_by("mandat", "prestation")


class TarifMandatCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un tarif mandat"""

    model = TarifMandat
    form_class = TarifMandatForm
    template_name = "facturation/tarif_form.html"
    business_permission = 'facturation.view_prestations'
    success_url = reverse_lazy("facturation:tarif-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Tarif créé avec succès"))
        return super().form_valid(form)


class TarifMandatUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un tarif mandat"""

    model = TarifMandat
    form_class = TarifMandatForm
    template_name = "facturation/tarif_form.html"
    business_permission = 'facturation.view_prestations'
    success_url = reverse_lazy("facturation:tarif-list")

    def form_valid(self, form):
        messages.success(self.request, _("Tarif modifié avec succès"))
        return super().form_valid(form)


# ============ ZONES GEOGRAPHIQUES ============


class ZoneGeographiqueListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des zones géographiques"""

    model = ZoneGeographique
    business_permission = 'facturation.view_prestations'
    template_name = "facturation/zone_list.html"
    context_object_name = "zones"
    paginate_by = 50

    def get_queryset(self):
        return ZoneGeographique.objects.filter(is_active=True).order_by("nom")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # GeoJSON pour la carte
        zones = ZoneGeographique.objects.filter(is_active=True)
        features = []
        for zone in zones:
            features.append({
                "type": "Feature",
                "properties": {
                    "id": str(zone.id),
                    "nom": zone.nom,
                    "couleur": zone.couleur,
                },
                "geometry": json.loads(zone.geometrie.geojson),
            })
        context["zones_geojson"] = json.dumps({
            "type": "FeatureCollection",
            "features": features,
        })
        return context


class ZoneGeographiqueCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'une zone géographique"""

    model = ZoneGeographique
    form_class = ZoneGeographiqueForm
    template_name = "facturation/zone_form.html"
    business_permission = 'facturation.view_prestations'
    success_url = reverse_lazy("facturation:zone-list")

    def form_valid(self, form):
        # La géométrie est passée en GeoJSON via un champ hidden dans le template
        geojson = self.request.POST.get("geometrie_geojson")
        if geojson:
            from django.contrib.gis.geos import GEOSGeometry
            form.instance.geometrie = GEOSGeometry(geojson, srid=4326)

        form.instance.created_by = self.request.user
        messages.success(self.request, _("Zone créée avec succès"))
        return super().form_valid(form)


class ZoneGeographiqueUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'une zone géographique"""

    model = ZoneGeographique
    form_class = ZoneGeographiqueForm
    template_name = "facturation/zone_form.html"
    business_permission = 'facturation.view_prestations'
    success_url = reverse_lazy("facturation:zone-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.geometrie:
            context["geometrie_geojson"] = self.object.geometrie.geojson
        return context

    def form_valid(self, form):
        geojson = self.request.POST.get("geometrie_geojson")
        if geojson:
            from django.contrib.gis.geos import GEOSGeometry
            form.instance.geometrie = GEOSGeometry(geojson, srid=4326)

        messages.success(self.request, _("Zone modifiée avec succès"))
        return super().form_valid(form)


# ==============================================================================
# DOCUMENT STUDIO - FACTURES
# ==============================================================================

@login_required
@permission_required_business('facturation.view_factures')
def facture_studio(request, pk):
    """Vue Studio PDF pour personnaliser une facture."""
    facture = get_object_or_404(Facture, pk=pk)

    from core.models import ModeleDocumentPDF
    modele = ModeleDocumentPDF.get_effectif('FACTURE', facture.mandat)
    config = modele.to_style_config() if modele else {}

    # Convertir les HexColor en strings pour le template
    config_json = {
        'couleur_primaire': modele.couleur_primaire if modele else '#088178',
        'couleur_accent': modele.couleur_accent if modele else '#2c3e50',
        'couleur_texte': modele.couleur_texte if modele else '#333333',
        'police': modele.police if modele else 'Helvetica',
        'marge_haut': modele.marge_haut if modele else 20,
        'marge_bas': modele.marge_bas if modele else 25,
        'marge_gauche': modele.marge_gauche if modele else 20,
        'marge_droite': modele.marge_droite if modele else 15,
        'textes': modele.textes if modele else {},
        'blocs_visibles': modele.blocs_visibles if modele else {},
    }

    blocs_config = [
        ('logo', _('Logo')),
        ('introduction', _('Introduction')),
        ('conclusion', _('Conclusion')),
        ('conditions', _('Conditions de paiement')),
        ('qr_bill', _('QR-Bill suisse')),
        ('remise', _('Remise')),
        ('tva', _('TVA')),
    ]

    return render(request, "facturation/facture_studio.html", {
        'facture': facture,
        'config': config_json,
        'config_json': json.dumps(config_json),
        'blocs_config': blocs_config,
        'preview_url': reverse_lazy('facturation:facture-studio-preview'),
        'save_url': reverse_lazy('core:modele-pdf-save'),
        'type_document': 'FACTURE',
        'config_extra_template': 'facturation/_studio_config_extra.html',
    })


@login_required
@require_http_methods(["POST"])
@permission_required_business('facturation.view_factures')
def facture_studio_preview(request):
    """API de preview PDF pour le Studio facture."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalide'}, status=400)

    facture = get_object_or_404(Facture, pk=data.get('instance_id'))

    from facturation.services.pdf_facture import FacturePDF
    service = FacturePDF(
        facture,
        style_config=data,
        avec_qr_bill=data.get('blocs_visibles', {}).get('qr_bill', False),
    )
    pdf_bytes = service.generer()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="preview.pdf"'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response
