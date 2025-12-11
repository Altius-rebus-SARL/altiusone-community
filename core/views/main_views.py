# core/views/main_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.db.models import Q, Count, Sum, Avg, F, Max, Min
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

from core.models import (
    Client,
    Mandat,
    Contact,
    ExerciceComptable,
    User,
    Tache,
    Notification,
)
from core.forms import (
    ClientForm,
    MandatForm,
    ContactForm,
    TacheForm,
    AdresseForm,
    SignUpForm, 
    ExerciceComptableForm,
)
from core.filters import ClientFilter, MandatFilter, TacheFilter

from comptabilite.models import EcritureComptable, Compte
from facturation.models import Facture
from tva.models import DeclarationTVA
from documents.models import Document


class DashboardView(LoginRequiredMixin, ListView):
    """Tableau de bord principal"""

    template_name = "core/dashboard.html"
    context_object_name = "mandats"

    def get_queryset(self):
        user = self.request.user
        if user.role in ["ADMIN", "MANAGER"]:
            return Mandat.objects.filter(statut="ACTIF")
        return Mandat.objects.filter(
            Q(responsable=user) | Q(equipe=user), statut="ACTIF"  # ← Vérifiez ici
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Statistiques générales
        context["stats"] = {
            "clients_actifs": Client.objects.filter(statut="ACTIF").count(),
            "mandats_actifs": self.get_queryset().count(),
            "taches_en_cours": Tache.objects.filter(
                assigne_a=user, statut__in=["A_FAIRE", "EN_COURS"]
            ).count(),
            "notifications_non_lues": Notification.objects.filter(
                destinataire=user, lue=False
            ).count(),
        }

        # Tâches urgentes
        context["taches_urgentes"] = (
            Tache.objects.filter(
                assigne_a=user,
                statut__in=["A_FAIRE", "EN_COURS"],
                priorite__in=["HAUTE", "URGENTE"],
            )
            .select_related("mandat", "cree_par")
            .order_by("date_echeance")[:5]
        )

        # Notifications récentes
        context["notifications"] = Notification.objects.filter(
            destinataire=user
        ).order_by("-created_at")[:10]

        # Activité récente par mandat
        mandats = self.get_queryset()[:10]
        context["activite_mandats"] = []

        for mandat in mandats:
            context["activite_mandats"].append(
                {
                    "mandat": mandat,
                    "taches_count": Tache.objects.filter(mandat=mandat).count(),
                    "taches_terminees": Tache.objects.filter(
                        mandat=mandat, statut="TERMINEE"
                    ).count(),
                }
            )

        return context


# ============ CLIENTS ============


class ClientListView(LoginRequiredMixin, ListView):
    """Liste des clients avec filtres avancés"""

    model = Client
    template_name = "core/client_list.html"
    context_object_name = "clients"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            Client.objects.select_related(
                "adresse_siege", "responsable", "contact_principal"
            )
            .prefetch_related("mandats")
            .annotate(
                nb_mandats=Count("mandats"),
                nb_mandats_actifs=Count("mandats", filter=Q(mandats__statut="ACTIF")),
            )
        )

        # Appliquer les filtres
        self.filterset = ClientFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "actifs": queryset.filter(statut="ACTIF").count(),
            "prospects": queryset.filter(statut="PROSPECT").count(),
            "par_forme_juridique": queryset.values("forme_juridique")
            .annotate(count=Count("id"))
            .order_by("-count"),
        }

        return context


class ClientDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un client avec toutes ses informations"""

    model = Client
    template_name = "core/client_detail.html"
    context_object_name = "client"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "adresse_siege",
                "adresse_correspondance",
                "responsable",
                "contact_principal",
            )
            .prefetch_related("contacts", "mandats__responsable", "mandats__exercices")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object

        # Mandats
        context["mandats"] = client.mandats.all().order_by("-date_debut")

        # Contacts
        context["contacts"] = client.contacts.all()

        # Documents récents
        from documents.models import Document

        context["documents_recents"] = Document.objects.filter(
            mandat__client=client
        ).order_by("-created_at")[:10]

        # Factures récentes
        from facturation.models import Facture

        context["factures_recentes"] = Facture.objects.filter(client=client).order_by(
            "-date_emission"
        )[:10]

        # Statistiques financières
        factures = Facture.objects.filter(client=client)
        context["stats_financieres"] = {
            "ca_total": factures.aggregate(Sum("montant_ttc"))["montant_ttc__sum"] or 0,
            "ca_annee_courante": factures.filter(
                date_emission__year=datetime.now().year
            ).aggregate(Sum("montant_ttc"))["montant_ttc__sum"]
            or 0,
            "impaye": factures.filter(
                statut__in=["EMISE", "ENVOYEE", "RELANCEE", "EN_RETARD"]
            ).aggregate(Sum("montant_restant"))["montant_restant__sum"]
            or 0,
        }

        return context


class ClientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Création d'un nouveau client"""

    model = Client
    form_class = ClientForm
    template_name = "core/client_form.html"
    permission_required = "core.add_client"
    success_url = reverse_lazy("core:client-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Client créé avec succès"))
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modification d'un client"""

    model = Client
    form_class = ClientForm
    template_name = "core/client_form.html"
    permission_required = "core.change_client"

    def get_success_url(self):
        return reverse_lazy("core:client-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Client modifié avec succès"))
        return super().form_valid(form)

class MandatUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modification d'un mandat"""

    model = Mandat
    form_class = MandatForm
    template_name = "core/mandat_form.html"
    permission_required = "core.change_mandat"

    def get_success_url(self):
        return reverse_lazy("core:mandat-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Mandat modifié avec succès"))
        return super().form_valid(form)
    
# ============ MANDATS ============


class MandatListView(LoginRequiredMixin, ListView):
    """Liste des mandats"""

    model = Mandat
    template_name = "core/mandat_list.html"
    context_object_name = "mandats"
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user

        queryset = (
            Mandat.objects.select_related("client", "responsable")
            .prefetch_related("equipe")
            .annotate(
                nb_taches=Count("taches"),
                nb_taches_en_cours=Count(
                    "taches", filter=Q(taches__statut__in=["A_FAIRE", "EN_COURS"])
                ),
            )
        )

        # # Filtrer selon le rôle
        # if user.role not in ["ADMIN", "MANAGER"]:
        #     queryset = queryset.filter(Q(responsable=user) | Q(equipe=user)).distinct()

        # Appliquer filtres
        self.filterset = MandatFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("-date_debut")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "actifs": queryset.filter(statut="ACTIF").count(),
            "par_type": queryset.values("type_mandat").annotate(count=Count("id")),
        }

        return context


class MandatDetailView(LoginRequiredMixin, DetailView):
    """Détail complet d'un mandat"""

    model = Mandat
    template_name = "core/mandat_detail.html"
    context_object_name = "mandat"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("client", "responsable")
            .prefetch_related("equipe", "exercices")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mandat = self.object

        # Exercices comptables
        context["exercices"] = mandat.exercices.all().order_by("-annee")

        # Tâches
        context["taches"] = (
            Tache.objects.filter(mandat=mandat)
            .select_related("assigne_a")
            .order_by("-date_echeance")[:20]
        )

        # Documents
        from documents.models import Document

        context["documents"] = Document.objects.filter(mandat=mandat).order_by(
            "-created_at"
        )[:10]

        # Statistiques selon le type de mandat
        if mandat.type_mandat in ["COMPTA", "GLOBAL"]:
            from comptabilite.models import EcritureComptable, PieceComptable

            exercice_actuel = mandat.exercices.filter(statut="OUVERT").first()
            if exercice_actuel:
                context["stats_compta"] = {
                    "nb_ecritures": EcritureComptable.objects.filter(
                        mandat=mandat, exercice=exercice_actuel
                    ).count(),
                    "nb_pieces": PieceComptable.objects.filter(mandat=mandat).count(),
                    "pieces_non_equilibrees": PieceComptable.objects.filter(
                        mandat=mandat, equilibree=False
                    ).count(),
                }

        if mandat.type_mandat in ["TVA", "GLOBAL"]:
            from tva.models import DeclarationTVA

            context["declarations_tva"] = DeclarationTVA.objects.filter(
                mandat=mandat
            ).order_by("-annee", "-trimestre")[:5]

        if mandat.type_mandat in ["SALAIRES", "GLOBAL"]:
            from salaires.models import Employe, FicheSalaire

            context["stats_salaires"] = {
                "nb_employes": Employe.objects.filter(
                    mandat=mandat, statut="ACTIF"
                ).count(),
                "masse_salariale_mois": FicheSalaire.objects.filter(
                    employe__mandat=mandat,
                    periode__month=datetime.now().month,
                    periode__year=datetime.now().year,
                ).aggregate(Sum("salaire_brut_total"))["salaire_brut_total__sum"]
                or 0,
            }

        # Facturation
        from facturation.models import Facture

        factures = Facture.objects.filter(mandat=mandat)
        context["stats_facturation"] = {
            "ca_annee": factures.filter(
                date_emission__year=datetime.now().year
            ).aggregate(Sum("montant_ttc"))["montant_ttc__sum"]
            or 0,
            "impaye": factures.filter(
                statut__in=["EMISE", "ENVOYEE", "RELANCEE", "EN_RETARD"]
            ).aggregate(Sum("montant_restant"))["montant_restant__sum"]
            or 0,
        }

        return context


class MandatCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Création d'un nouveau mandat"""

    model = Mandat
    form_class = MandatForm
    template_name = "core/mandat_form.html"
    permission_required = "core.add_mandat"

    def get_success_url(self):
        return reverse_lazy("core:mandat-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Mandat créé avec succès"))
        return super().form_valid(form)


# ============ TÂCHES ============


class TacheListView(LoginRequiredMixin, ListView):
    """Liste des tâches"""

    model = Tache
    template_name = "core/tache_list.html"
    context_object_name = "taches"
    paginate_by = 50

    def get_queryset(self):
        queryset = Tache.objects.select_related(
            "assigne_a", "cree_par", "mandat__client"
        )

        # Filtrer par utilisateur si pas admin
        user = self.request.user
        if user.role not in ["ADMIN", "MANAGER"]:
            queryset = queryset.filter(Q(assigne_a=user) | Q(cree_par=user))

        # Appliquer filtres
        self.filterset = TacheFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by("date_echeance", "-priorite")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        # Statistiques
        user = self.request.user
        queryset = Tache.objects.filter(assigne_a=user)

        context["stats"] = {
            "a_faire": queryset.filter(statut="A_FAIRE").count(),
            "en_cours": queryset.filter(statut="EN_COURS").count(),
            "en_retard": queryset.filter(
                statut__in=["A_FAIRE", "EN_COURS"],
                date_echeance__lt=datetime.now().date(),
            ).count(),
            "terminees_semaine": queryset.filter(
                statut="TERMINEE", date_fin__gte=datetime.now() - timedelta(days=7)
            ).count(),
        }

        return context


class TacheDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une tâche"""

    model = Tache
    template_name = "core/tache_detail.html"
    context_object_name = "tache"


class TacheCreateView(LoginRequiredMixin, CreateView):
    """Création d'une tâche"""

    model = Tache
    form_class = TacheForm
    template_name = "core/tache_form.html"
    success_url = reverse_lazy("core:tache-list")

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Tâche créée avec succès"))
        return super().form_valid(form)


class TacheUpdateView(LoginRequiredMixin, UpdateView):
    """Modification d'une tâche"""

    model = Tache
    form_class = TacheForm
    template_name = "core/tache_form.html"
    success_url = reverse_lazy("core:tache-list")

    def form_valid(self, form):
        messages.success(self.request, _("Tâche modifiée avec succès"))
        return super().form_valid(form)


# ============ API AJAX ============


@login_required
def tache_changer_statut(request, pk):
    """Change le statut d'une tâche (AJAX)"""
    if request.method == "POST":
        tache = get_object_or_404(Tache, pk=pk)
        nouveau_statut = request.POST.get("statut")

        if nouveau_statut in dict(Tache.STATUT_CHOICES):
            tache.statut = nouveau_statut

            if nouveau_statut == "EN_COURS" and not tache.date_debut:
                tache.date_debut = datetime.now()
            elif nouveau_statut == "TERMINEE":
                tache.date_fin = datetime.now()

            tache.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": _("Statut mis à jour"),
                    "statut": tache.get_statut_display(),
                }
            )

    return JsonResponse({"success": False}, status=400)


@login_required
def notification_marquer_lue(request, pk):
    """Marque une notification comme lue (AJAX)"""
    if request.method == "POST":
        notif = get_object_or_404(Notification, pk=pk, destinataire=request.user)
        notif.lue = True
        notif.date_lecture = datetime.now()
        notif.save()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)


@login_required
def get_stats_dashboard(request):
    """Retourne les statistiques pour le dashboard (AJAX)"""
    user = request.user

    data = {
        "taches": {
            "a_faire": Tache.objects.filter(assigne_a=user, statut="A_FAIRE").count(),
            "en_cours": Tache.objects.filter(assigne_a=user, statut="EN_COURS").count(),
        },
        "notifications": Notification.objects.filter(
            destinataire=user, lue=False
        ).count(),
    }

    return JsonResponse(data)




# ============================================================================
# RECHERCHE GLOBALE
# ============================================================================


class GlobalSearchView(LoginRequiredMixin, TemplateView):
    """
    Recherche globale dans tous les modules
    """

    template_name = "core/search_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()

        context["query"] = query
        context["results"] = {}

        if not query or len(query) < 2:
            context["error"] = _(
                "Veuillez entrer au moins 2 caractères pour la recherche"
            )
            return context

        # Recherche dans les clients
        clients = Client.objects.filter(
            Q(nom__icontains=query)
            | Q(code_client__icontains=query)
            | Q(email__icontains=query)
            | Q(telephone__icontains=query)
        ).select_related()[:10]
        context["results"]["clients"] = clients

        # Recherche dans les mandats
        mandats = Mandat.objects.filter(
            Q(numero__icontains=query)
            | Q(client__nom__icontains=query)
            | Q(description__icontains=query)
        ).select_related("client")[:10]
        context["results"]["mandats"] = mandats

        # Recherche dans les factures
        if self.request.user.has_perm("facturation.view_facture"):
            factures = Facture.objects.filter(
                Q(numero__icontains=query) | Q(client__nom__icontains=query)
            ).select_related("client")[:10]
            context["results"]["factures"] = factures

        # Recherche dans les documents
        if self.request.user.has_perm("documents.view_document"):
            documents = Document.objects.filter(
                Q(nom__icontains=query) | Q(description__icontains=query)
            ).select_related("mandat")[:10]
            context["results"]["documents"] = documents

        # Compter le total de résultats
        context["total_results"] = sum(
            len(results) for results in context["results"].values()
        )

        return context


# ============================================================================
# NOTIFICATIONS
# ============================================================================


class NotificationListView(LoginRequiredMixin, ListView):
    """Liste des notifications de l'utilisateur"""

    model = Notification
    template_name = "core/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            destinataire=self.request.user  # ← Vérifiez ici
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["stats"] = {
            "total": Notification.objects.filter(destinataire=user).count(),  # ← Et ici
            "non_lues": Notification.objects.filter(
                destinataire=user, lue=False
            ).count(),  # ← Et ici
            "importantes": Notification.objects.filter(
                destinataire=user,  # ← Et ici
                type_notification__in=["ERROR", "WARNING"],
            ).count(),
        }
        return context

    
@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Marquer toutes les notifications comme lues"""
    Notification.objects.filter(
        destinataire=request.user,  # ← Vérifiez ici
        lue=False,
    ).update(lue=True, date_lecture=timezone.now())

    messages.success(request, _("Toutes les notifications ont été marquées comme lues"))
    return redirect("core:notifications-list")


@login_required
@require_http_methods(["POST"])
def notification_mark_read(request, pk):
    """
    Marquer une notification spécifique comme lue
    """
    notification = get_object_or_404(Notification, pk=pk, utilisateur=request.user)

    notification.lue = True
    notification.date_lecture = datetime.now()
    notification.save()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True})

    return redirect("core:notifications-list")


# ============================================================================
# PROFIL UTILISATEUR
# ============================================================================


class ProfileView(LoginRequiredMixin, TemplateView):
    """
    Page de profil utilisateur
    """

    template_name = "core/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Statistiques de l'utilisateur
        context["stats"] = {
            "taches_total": Tache.objects.filter(assigne_a=user).count(),
            "taches_en_cours": Tache.objects.filter(
                assigne_a=user, statut="EN_COURS"
            ).count(),
            "taches_completees": Tache.objects.filter(
                assigne_a=user, statut="TERMINEE"
            ).count(),
            "mandats_responsable": Mandat.objects.filter(responsable=user).count(),
            "mandats_equipe": Mandat.objects.filter(
                equipe=user
            ).count(),  # ← CORRECTION ICI: 'equipe' au lieu de 'equipe_members'
        }

        # Tâches récentes de l'utilisateur
        context["taches_recentes"] = Tache.objects.filter(assigne_a=user).order_by(
            "-created_at"
        )[:5]

        # Mandats actifs de l'utilisateur
        context["mandats_actifs"] = Mandat.objects.filter(
            responsable=user, statut="ACTIF"
        ).order_by("-date_debut")[:5]

        # Notifications non lues
        context["notifications_non_lues"] = Notification.objects.filter(
            destinataire=user,
            lue=False,
        ).count()

        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    Modification du profil utilisateur
    """

    template_name = "core/profile_edit.html"
    fields = ["first_name", "last_name", "email"]
    success_url = reverse_lazy("core:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _("Profil mis à jour avec succès"))
        return super().form_valid(form)



# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================


class CustomLoginView(LoginView):
    """Vue de connexion personnalisée"""

    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        # Rediriger vers 'next' si présent, sinon vers le dashboard
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse_lazy("core:dashboard")


class SignUpView(CreateView):
    """Vue d'inscription"""

    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("core:dashboard")

    def form_valid(self, form):
        """Connecter automatiquement l'utilisateur après inscription"""
        response = super().form_valid(form)
        # Connecter l'utilisateur automatiquement
        auth_login(self.request, self.object)
        messages.success(
            self.request,
            _("Bienvenue sur AltiusOne ! Votre compte a été créé avec succès."),
        )
        return response

    def dispatch(self, request, *args, **kwargs):
        """Rediriger les utilisateurs déjà connectés"""
        if request.user.is_authenticated:
            return redirect("core:dashboard")
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    """Vue de demande de réinitialisation de mot de passe"""

    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("core:password-reset-done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """Vue de confirmation d'envoi d'email"""

    template_name = "registration/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Vue de réinitialisation du mot de passe"""

    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("core:password-reset-complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """Vue de confirmation de réinitialisation"""

    template_name = "registration/password_reset_complete.html"


@login_required
def logout_view(request):
    """
    Vue de déconnexion personnalisée
    """
    auth_logout(request)
    messages.success(request, _("Vous avez été déconnecté avec succès"))
    return redirect("core:login")
# ============================================================================
# PARAMÈTRES
# ============================================================================


class SettingsView(LoginRequiredMixin, TemplateView):
    """
    Page des paramètres utilisateur
    """

    template_name = "core/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Préférences utilisateur
        context["user"] = user
        context["preferences"] = {
            "langue": getattr(user, "langue", "fr"),
            "theme": getattr(user, "theme", "light"),
            "notifications_email": getattr(user, "notifications_email", True),
            "notifications_push": getattr(user, "notifications_push", False),
        }

        # Paramètres de sécurité
        context["security"] = {
            "last_login": user.last_login,
            "date_joined": user.date_joined,
            "two_factor_enabled": False,  # À implémenter si nécessaire
        }

        return context


# Ajoutez ceci dans core/views.py si ce n'est pas déjà présent


@login_required
@require_http_methods(["POST"])
def update_user_preferences(request):
    """
    Mise à jour des préférences utilisateur via AJAX ou POST
    """
    user = request.user

    # Récupérer les paramètres
    langue = request.POST.get("langue")
    theme = request.POST.get("theme")
    notifications_email = request.POST.get("notifications_email") == "on"
    notifications_push = request.POST.get("notifications_push") == "on"

    # Mettre à jour les préférences dans le modèle User
    # Si vous avez un champ preferences (JSONField) dans votre modèle User
    if not user.preferences:
        user.preferences = {}

    if langue:
        user.preferences["langue"] = langue
    if theme:
        user.preferences["theme"] = theme

    user.preferences["notifications_email"] = notifications_email
    user.preferences["notifications_push"] = notifications_push

    user.save()

    messages.success(request, _("Préférences mises à jour avec succès"))

    # Si c'est une requête AJAX
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True})

    # Sinon rediriger vers la page des paramètres
    return redirect("core:settings")


@login_required
@require_http_methods(["POST"])
def update_user_preferences(request):
    """
    Mise à jour des préférences utilisateur via AJAX
    """
    user = request.user

    # Récupérer les paramètres
    langue = request.POST.get("langue")
    theme = request.POST.get("theme")
    notifications_email = request.POST.get("notifications_email") == "true"

    # Mettre à jour (vous devrez adapter selon votre modèle User)
    if langue:
        user.langue = langue
    if theme:
        user.theme = theme

    user.save()

    messages.success(request, _("Préférences mises à jour avec succès"))

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True})

    return redirect("core:settings")


# ============================================================================
# PAGES STATIQUES
# ============================================================================


class AboutView(LoginRequiredMixin, TemplateView):
    """
    Page À propos de l'application
    """

    template_name = "core/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["app_info"] = {
            "name": "AltiusOne",
            "version": "1.0.0",
            "description": _("Gestion fiduciaire complète pour la Suisse"),
            "company": "AltiusOne SA",
            "year": datetime.now().year,
        }

        # Statistiques globales (si admin)
        if self.request.user.is_staff:
            context["global_stats"] = {
                "clients": Client.objects.count(),
                "mandats": Mandat.objects.count(),
                "users": self.request.user.__class__.objects.count(),
            }

        return context


class SupportView(LoginRequiredMixin, TemplateView):
    """
    Page de support / aide
    """

    template_name = "core/support.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # FAQ communes
        context["faq"] = [
            {
                "question": _("Comment créer un nouveau client ?"),
                "answer": _(
                    "Allez dans le menu 'Clients' puis cliquez sur 'Nouveau client'."
                ),
            },
            {
                "question": _("Comment générer une facture ?"),
                "answer": _(
                    "Accédez au module Facturation, sélectionnez le mandat concerné, puis cliquez sur 'Nouvelle facture'."
                ),
            },
            {
                "question": _("Comment soumettre une déclaration TVA ?"),
                "answer": _(
                    "Allez dans TVA > Déclarations, sélectionnez la période, puis cliquez sur 'Soumettre'."
                ),
            },
        ]

        # Informations de contact
        context["contact"] = {
            "email": "support@altiusone.ch",
            "phone": "+41 XX XXX XX XX",
            "hours": _("Lundi - Vendredi : 9h00 - 18h00"),
        }

        return context


@login_required
@require_http_methods(["POST"])
def submit_support_request(request):
    """
    Soumettre une demande de support
    """
    subject = request.POST.get("subject")
    message = request.POST.get("message")

    # Ici, vous pourriez envoyer un email ou créer un ticket
    # Pour l'instant, on crée juste une notification
    Notification.objects.create(
        utilisateur=request.user,
        titre=f"Support: {subject}",
        message=f"Votre demande a été enregistrée: {message}",
        niveau="INFO",
        type_notification="SYSTEME",
    )

    messages.success(
        request,
        _("Votre demande de support a été envoyée. Nous vous contacterons sous 24h."),
    )

    return redirect("core:support")


# ============================================================================
# CHANGEMENT DE LANGUE
# ============================================================================


@login_required
def set_language(request):
    """
    Changer la langue de l'interface
    """
    from django.utils import translation

    language = request.GET.get("language", "fr")

    # Valider la langue
    available_languages = ["fr", "de", "it", "en"]
    if language not in available_languages:
        language = "fr"

    # Activer la langue
    translation.activate(language)
    request.session[translation.LANGUAGE_SESSION_KEY] = language

    # Sauvegarder dans le profil utilisateur (si le champ existe)
    user = request.user
    if hasattr(user, "langue"):
        user.langue = language
        user.save(update_fields=["langue"])

    # Rediriger vers la page précédente
    next_url = request.META.get("HTTP_REFERER", "/")

    return redirect(next_url)


# ============================================================================
# API AJAX POUR LE DASHBOARD
# ============================================================================


@login_required
@require_http_methods(["GET"])
def get_dashboard_stats(request):
    """
    Retourner les statistiques du dashboard en JSON (pour actualisation AJAX)
    """
    user = request.user

    stats = {
        "clients_actifs": Client.objects.filter(statut="ACTIF").count(),
        "mandats_actifs": Mandat.objects.filter(statut="ACTIF").count(),
        "taches_en_cours": Tache.objects.filter(
            statut__in=["A_FAIRE", "EN_COURS"]
        ).count(),
        "notifications_non_lues": Notification.objects.filter(
            utilisateur=user, lue=False
        ).count(),
    }

    return JsonResponse(stats)

# ============================================================================
# EXERCICES COMPTABLES
# ============================================================================


class ExerciceListView(LoginRequiredMixin, ListView):
    """Liste des exercices comptables"""

    model = ExerciceComptable
    template_name = "core/exercice_list.html"
    context_object_name = "exercices"
    paginate_by = 25

    def get_queryset(self):
        queryset = ExerciceComptable.objects.select_related(
            "mandat", "mandat__client"
        ).order_by("-annee", "-date_debut")

        # Filtrer par mandat si spécifié
        mandat_id = self.request.GET.get("mandat")
        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        # Filtrer par statut
        statut = self.request.GET.get("statut")
        if statut:
            queryset = queryset.filter(statut=statut)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Statistiques
        queryset = self.get_queryset()
        context["stats"] = {
            "total": queryset.count(),
            "ouverts": queryset.filter(statut="OUVERT").count(),
            "clotures_provisoire": queryset.filter(statut="CLOTURE_PROVISOIRE").count(),
            "clotures_definitif": queryset.filter(statut="CLOTURE_DEFINITIVE").count(),
        }

        # Mandats pour le filtre
        context["mandats"] = Mandat.objects.filter(statut="ACTIF").order_by(
            "client__raison_sociale"
        )

        return context


class ExerciceDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un exercice comptable"""

    model = ExerciceComptable
    template_name = "core/exercice_detail.html"
    context_object_name = "exercice"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("mandat", "mandat__client", "cloture_par")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exercice = self.object

        # Statistiques comptables si le module existe
        try:
            from comptabilite.models import EcritureComptable, PieceComptable

            context["stats_compta"] = {
                "nb_ecritures": EcritureComptable.objects.filter(
                    exercice=exercice
                ).count(),
                "nb_pieces": PieceComptable.objects.filter(
                    mandat=exercice.mandat,
                    date_piece__range=[
                        exercice.date_debut,
                        exercice.date_fin,
                    ],  # ← CORRECTION ICI: date_piece au lieu de date
                ).count(),
            }
        except ImportError:
            pass

        # Déclarations TVA si le module existe
        try:
            from tva.models import DeclarationTVA

            context["declarations_tva"] = DeclarationTVA.objects.filter(
                mandat=exercice.mandat, annee=exercice.annee
            ).order_by("-trimestre")
        except ImportError:
            pass

        return context


class ExerciceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Création d'un nouvel exercice comptable"""

    model = ExerciceComptable
    form_class = ExerciceComptableForm
    template_name = "core/exercice_form.html"
    permission_required = "core.add_exercicecomptable"

    def get_success_url(self):
        return reverse_lazy("core:exercice-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Exercice comptable créé avec succès"))
        return super().form_valid(form)


class ExerciceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modification d'un exercice comptable"""

    model = ExerciceComptable
    form_class = ExerciceComptableForm
    template_name = "core/exercice_form.html"
    permission_required = "core.change_exercicecomptable"

    def get_success_url(self):
        return reverse_lazy("core:exercice-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Exercice comptable modifié avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def exercice_cloturer(request, pk):
    """
    Clôturer un exercice comptable
    """
    exercice = get_object_or_404(ExerciceComptable, pk=pk)

    # Vérifier les permissions
    if not request.user.has_perm("core.change_exercicecomptable"):
        messages.error(
            request, _("Vous n'avez pas la permission de clôturer cet exercice")
        )
        return redirect("core:exercice-detail", pk=pk)

    # Vérifier que l'exercice n'est pas déjà clôturé définitivement
    if exercice.statut == "CLOTURE_DEFINITIVE":
        messages.warning(request, _("Cet exercice est déjà clôturé définitivement"))
        return redirect("core:exercice-detail", pk=pk)

    # Type de clôture
    type_cloture = request.POST.get("type_cloture", "provisoire")

    if type_cloture == "definitif":
        exercice.statut = "CLOTURE_DEFINITIVE"
        msg = _("Exercice clôturé définitivement")
    else:
        exercice.statut = "CLOTURE_PROVISOIRE"
        msg = _("Exercice clôturé provisoirement")

    exercice.date_cloture = timezone.now()
    exercice.cloture_par = request.user
    exercice.save()

    # Créer une notification
    Notification.objects.create(
        destinataire=exercice.mandat.responsable,
        titre=f"Clôture exercice {exercice.annee}",
        message=f"L'exercice {exercice.annee} du mandat {exercice.mandat.numero} a été clôturé",
        type_notification="INFO",
        mandat=exercice.mandat,
    )

    messages.success(request, msg)
    return redirect("core:exercice-detail", pk=pk)
# ============================================================================
# FIN DES VUES ADDITIONNELLES
# ============================================================================