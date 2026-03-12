# core/views/admin_views.py
"""
Vues d'administration pour la gestion des utilisateurs, rôles et invitations.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    FormView,
)
from django.contrib.auth import login as auth_login
from django.db.models import Q, Count
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from core.models import User, Role, Entreprise, Mandat, AccesMandat, Invitation, CollaborateurFiduciaire
from core.forms import (
    UserForm,
    UserCreateForm,
    RoleForm,
    EntrepriseForm,
    CompteBancaireFormSet,
    InvitationStaffForm,
    InvitationClientForm,
    AcceptInvitationForm,
    AccesMandatForm,
    ForcePasswordChangeForm,
    CollaborateurFiduciaireForm,
)
from core.services import InvitationService


class ManagerRequiredMixin(UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est manager ou superuser"""

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_manager()


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est admin ou superuser"""

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_admin()


# =============================================================================
# VUES UTILISATEURS
# =============================================================================

class UserListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des utilisateurs"""

    model = User
    template_name = "core/admin/user_list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        queryset = User.objects.select_related('role').annotate(
            nb_mandats=Count('acces_mandats', filter=Q(acces_mandats__is_active=True))
        )

        # Filtres
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        type_utilisateur = self.request.GET.get('type')
        if type_utilisateur:
            queryset = queryset.filter(type_utilisateur=type_utilisateur)

        role_id = self.request.GET.get('role')
        if role_id:
            queryset = queryset.filter(role_id=role_id)

        is_active = self.request.GET.get('active')
        if is_active == '1':
            queryset = queryset.filter(is_active=True)
        elif is_active == '0':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('-date_joined')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Statistiques
        queryset = User.objects.all()
        context['stats'] = {
            'total': queryset.count(),
            'staff': queryset.filter(type_utilisateur=User.TypeUtilisateur.STAFF).count(),
            'clients': queryset.filter(type_utilisateur=User.TypeUtilisateur.CLIENT).count(),
            'actifs': queryset.filter(is_active=True).count(),
        }

        # Rôles pour le filtre
        context['roles'] = Role.objects.filter(actif=True).order_by('nom')

        return context


class UserDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Détail d'un utilisateur"""

    model = User
    template_name = "core/admin/user_detail.html"
    context_object_name = "user_obj"

    def get_queryset(self):
        return User.objects.select_related('role', 'contact_lie')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object

        # Accès aux mandats
        context['acces_mandats'] = user.acces_mandats.filter(
            is_active=True
        ).select_related('mandat', 'mandat__client')

        # Invitations envoyées par cet utilisateur
        context['invitations_envoyees'] = Invitation.objects.filter(
            invite_par=user
        ).order_by('-created_at')[:10]

        return context


class UserCreateView(LoginRequiredMixin, ManagerRequiredMixin, CreateView):
    """Création d'un utilisateur"""

    model = User
    form_class = UserCreateForm
    template_name = "core/admin/user_form.html"
    success_url = reverse_lazy('core:admin-user-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Utilisateur créé avec succès"))
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, ManagerRequiredMixin, UpdateView):
    """Modification d'un utilisateur"""

    model = User
    form_class = UserForm
    template_name = "core/admin/user_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('core:admin-user-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Utilisateur modifié avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def user_toggle_active(request, pk):
    """Active/désactive un utilisateur"""
    if not (request.user.is_superuser or request.user.is_manager()):
        return HttpResponseForbidden()

    user = get_object_or_404(User, pk=pk)

    # Ne pas permettre de se désactiver soi-même
    if user == request.user:
        messages.error(request, _("Vous ne pouvez pas vous désactiver vous-même"))
        return redirect('core:admin-user-detail', pk=pk)

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])

    status = _("activé") if user.is_active else _("désactivé")
    messages.success(request, _("Utilisateur %(status)s") % {'status': status})

    return redirect('core:admin-user-detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def user_reset_password(request, pk):
    """Force le changement de mot de passe d'un utilisateur"""
    if not (request.user.is_superuser or request.user.is_manager()):
        return HttpResponseForbidden()

    user = get_object_or_404(User, pk=pk)
    user.doit_changer_mot_de_passe = True
    user.save(update_fields=['doit_changer_mot_de_passe'])

    messages.success(
        request,
        _("L'utilisateur devra changer son mot de passe à la prochaine connexion")
    )

    return redirect('core:admin-user-detail', pk=pk)


# =============================================================================
# VUES ROLES
# =============================================================================

class RoleListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Liste des rôles"""

    model = Role
    template_name = "core/admin/role_list.html"
    context_object_name = "roles"
    paginate_by = 25

    def get_queryset(self):
        return Role.objects.annotate(
            nb_utilisateurs=Count('utilisateurs')
        ).order_by('-niveau', 'nom')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total': Role.objects.count(),
            'actifs': Role.objects.filter(actif=True).count(),
        }
        return context


class RoleDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """Détail d'un rôle"""

    model = Role
    template_name = "core/admin/role_detail.html"
    context_object_name = "role"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.object

        # Utilisateurs avec ce rôle
        context['utilisateurs'] = User.objects.filter(role=role).order_by('username')[:20]

        # Permissions groupées par app
        permissions_by_app = {}
        for perm in role.permissions.select_related('content_type').all():
            app = perm.content_type.app_label
            if app not in permissions_by_app:
                permissions_by_app[app] = []
            permissions_by_app[app].append(perm)
        context['permissions_by_app'] = permissions_by_app

        return context


class RoleCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Création d'un rôle"""

    model = Role
    form_class = RoleForm
    template_name = "core/admin/role_form.html"
    success_url = reverse_lazy('core:admin-role-list')

    def form_valid(self, form):
        messages.success(self.request, _("Rôle créé avec succès"))
        return super().form_valid(form)


class RoleUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Modification d'un rôle"""

    model = Role
    form_class = RoleForm
    template_name = "core/admin/role_form.html"

    def get_success_url(self):
        return reverse('core:admin-role-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Rôle modifié avec succès"))
        return super().form_valid(form)


# =============================================================================
# VUES ENTREPRISES
# =============================================================================

class EntrepriseListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des entreprises"""

    model = Entreprise
    template_name = "core/entreprise_list.html"
    context_object_name = "entreprises"
    paginate_by = 25

    def get_queryset(self):
        return Entreprise.objects.annotate(
            nb_clients=Count('clients')
        ).order_by('-est_defaut', 'raison_sociale')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total': Entreprise.objects.count(),
            'actives': Entreprise.objects.filter(statut='ACTIVE').count(),
        }
        return context


class EntrepriseDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Détail d'une entreprise"""

    model = Entreprise
    template_name = "core/entreprise_detail.html"
    context_object_name = "entreprise"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entreprise = self.object
        context['clients'] = entreprise.clients.filter(
            is_active=True
        ).order_by('raison_sociale')[:20]
        context['comptes_bancaires'] = entreprise.comptes_bancaires.filter(
            actif=True
        ).order_by('-est_compte_principal', 'libelle')
        return context


class EntrepriseCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Création d'une entreprise"""

    model = Entreprise
    form_class = EntrepriseForm
    template_name = "core/entreprise_form.html"
    success_url = reverse_lazy('core:entreprise-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['comptes_formset'] = CompteBancaireFormSet(self.request.POST, prefix='comptes')
        else:
            context['comptes_formset'] = CompteBancaireFormSet(prefix='comptes')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        comptes_formset = context['comptes_formset']
        if comptes_formset.is_valid():
            self.object = form.save()
            comptes_formset.instance = self.object
            comptes_formset.save()
            messages.success(self.request, _("Entreprise créée avec succès"))
            return redirect(self.success_url)
        else:
            return self.form_invalid(form)


class EntrepriseUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Modification d'une entreprise"""

    model = Entreprise
    form_class = EntrepriseForm
    template_name = "core/entreprise_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['comptes_formset'] = CompteBancaireFormSet(
                self.request.POST, instance=self.object, prefix='comptes'
            )
        else:
            context['comptes_formset'] = CompteBancaireFormSet(
                instance=self.object, prefix='comptes'
            )
        return context

    def get_success_url(self):
        return reverse('core:entreprise-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        context = self.get_context_data()
        comptes_formset = context['comptes_formset']
        if comptes_formset.is_valid():
            self.object = form.save()
            comptes_formset.save()
            messages.success(self.request, _("Entreprise modifiée avec succès"))
            return redirect(self.get_success_url())
        else:
            return self.form_invalid(form)


# =============================================================================
# VUES INVITATIONS
# =============================================================================

class InvitationListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des invitations"""

    model = Invitation
    template_name = "core/admin/invitation_list.html"
    context_object_name = "invitations"
    paginate_by = 25

    def get_queryset(self):
        queryset = Invitation.objects.select_related(
            'invite_par', 'mandat', 'role_preassigne', 'utilisateur_cree'
        )

        # Filtres
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)

        type_inv = self.request.GET.get('type')
        if type_inv:
            queryset = queryset.filter(type_invitation=type_inv)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Statistiques
        queryset = Invitation.objects.all()
        context['stats'] = {
            'total': queryset.count(),
            'en_attente': queryset.filter(statut=Invitation.Statut.EN_ATTENTE).count(),
            'acceptees': queryset.filter(statut=Invitation.Statut.ACCEPTEE).count(),
            'expirees': queryset.filter(statut=Invitation.Statut.EXPIREE).count(),
        }

        return context


class InvitationDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Détail d'une invitation"""

    model = Invitation
    template_name = "core/admin/invitation_detail.html"
    context_object_name = "invitation"

    def get_queryset(self):
        return Invitation.objects.select_related(
            'invite_par', 'mandat', 'mandat__client', 'role_preassigne', 'utilisateur_cree'
        )


class InvitationStaffCreateView(LoginRequiredMixin, ManagerRequiredMixin, FormView):
    """Créer une invitation staff"""

    template_name = "core/admin/invitation_staff_form.html"
    form_class = InvitationStaffForm
    success_url = reverse_lazy('core:admin-invitation-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            invitation = InvitationService.creer_invitation_staff(
                email=form.cleaned_data['email'],
                invite_par=self.request.user,
                role=form.cleaned_data.get('role'),
                message=form.cleaned_data.get('message', ''),
                forcer_changement_mdp=form.cleaned_data.get('forcer_changement_mdp', True)
            )
            messages.success(
                self.request,
                _("Invitation envoyée à %(email)s") % {'email': invitation.email}
            )
        except (PermissionError, ValueError) as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        return super().form_valid(form)


class InvitationClientCreateView(LoginRequiredMixin, FormView):
    """Créer une invitation client"""

    template_name = "core/admin/invitation_client_form.html"
    form_class = InvitationClientForm
    success_url = reverse_lazy('core:admin-invitation-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            invitation = InvitationService.creer_invitation_client(
                email=form.cleaned_data['email'],
                invite_par=self.request.user,
                mandat=form.cleaned_data['mandat'],
                permissions=list(form.cleaned_data.get('permissions', [])),
                est_responsable=form.cleaned_data.get('est_responsable', False),
                limite_invitations=form.cleaned_data.get('limite_invitations', 5),
                message=form.cleaned_data.get('message', ''),
                forcer_changement_mdp=form.cleaned_data.get('forcer_changement_mdp', True)
            )
            messages.success(
                self.request,
                _("Invitation envoyée à %(email)s — Code: %(code)s") % {
                    'email': invitation.email,
                    'code': invitation.code_court
                }
            )
        except (PermissionError, ValueError) as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def invitation_resend(request, pk):
    """Renvoyer une invitation"""
    invitation = get_object_or_404(Invitation, pk=pk)

    # Vérifier les permissions
    if not (request.user.is_superuser or request.user.is_manager()):
        if invitation.invite_par != request.user:
            return HttpResponseForbidden()

    try:
        invitation = InvitationService.renvoyer_invitation(invitation, request.user)
        messages.success(request, _("Invitation renvoyée avec succès"))
    except Exception as e:
        messages.error(request, str(e))

    return redirect('core:admin-invitation-detail', pk=invitation.pk)


@login_required
@require_http_methods(["POST"])
def invitation_cancel(request, pk):
    """Annuler une invitation"""
    invitation = get_object_or_404(Invitation, pk=pk)

    try:
        InvitationService.annuler_invitation(invitation, request.user)
        messages.success(request, _("Invitation annulée"))
    except (PermissionError, ValueError) as e:
        messages.error(request, str(e))

    return redirect('core:admin-invitation-list')


# =============================================================================
# VUES ACCEPTATION INVITATION (PUBLIQUES)
# =============================================================================

class AcceptInvitationView(FormView):
    """Vue publique pour accepter une invitation"""

    template_name = "core/admin/accept_invitation.html"
    form_class = AcceptInvitationForm

    def dispatch(self, request, *args, **kwargs):
        # Valider le token
        token = kwargs.get('token')
        self.invitation = InvitationService.valider_token(token)

        if not self.invitation:
            messages.error(request, _("Cette invitation n'est plus valide ou a expiré"))
            return redirect('core:login')

        # Si l'utilisateur est déjà connecté, déconnecter
        if request.user.is_authenticated:
            from django.contrib.auth import logout
            logout(request)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invitation'] = self.invitation
        return context

    def form_valid(self, form):
        try:
            user = InvitationService.accepter_invitation(
                invitation=self.invitation,
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                phone=form.cleaned_data.get('phone', '')
            )

            # Connecter l'utilisateur
            auth_login(self.request, user)

            messages.success(
                self.request,
                _("Bienvenue %(name)s ! Votre compte a été créé avec succès.") % {
                    'name': user.first_name or user.username
                }
            )

            # Rediriger vers changement de mot de passe si nécessaire
            if user.doit_changer_mot_de_passe:
                return redirect('core:force-password-change')

            return redirect('core:dashboard')

        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


# =============================================================================
# VUES ACCES MANDAT
# =============================================================================

class AccesMandatListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des accès mandats (pour les clients externes)"""

    model = AccesMandat
    template_name = "core/admin/acces_mandat_list.html"
    context_object_name = "acces_list"
    paginate_by = 25

    def get_queryset(self):
        queryset = AccesMandat.objects.select_related(
            'utilisateur', 'mandat', 'mandat__client', 'accorde_par'
        )

        # Filtres
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        is_active = self.request.GET.get('active')
        if is_active == '1':
            queryset = queryset.filter(is_active=True)
        elif is_active == '0':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mandats pour le filtre
        context['mandats'] = Mandat.objects.filter(statut='ACTIF').order_by('numero')

        return context


class AccesMandatCreateView(LoginRequiredMixin, ManagerRequiredMixin, CreateView):
    """Créer un accès mandat"""

    model = AccesMandat
    form_class = AccesMandatForm
    template_name = "core/admin/acces_mandat_form.html"
    success_url = reverse_lazy('core:admin-acces-mandat-list')

    def form_valid(self, form):
        form.instance.accorde_par = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Accès créé avec succès"))
        return super().form_valid(form)


class AccesMandatUpdateView(LoginRequiredMixin, ManagerRequiredMixin, UpdateView):
    """Modifier un accès mandat"""

    model = AccesMandat
    form_class = AccesMandatForm
    template_name = "core/admin/acces_mandat_form.html"
    success_url = reverse_lazy('core:admin-acces-mandat-list')

    def form_valid(self, form):
        messages.success(self.request, _("Accès modifié avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def acces_mandat_toggle(request, pk):
    """Active/désactive un accès mandat"""
    if not (request.user.is_superuser or request.user.is_manager()):
        return HttpResponseForbidden()

    acces = get_object_or_404(AccesMandat, pk=pk)
    acces.is_active = not acces.is_active
    acces.save(update_fields=['is_active', 'updated_at'])

    status = _("activé") if acces.is_active else _("désactivé")
    messages.success(request, _("Accès %(status)s") % {'status': status})

    return redirect('core:admin-acces-mandat-list')


# =============================================================================
# VUE CHANGEMENT MOT DE PASSE OBLIGATOIRE
# =============================================================================

class ForcePasswordChangeView(LoginRequiredMixin, FormView):
    """Vue pour forcer le changement de mot de passe"""

    template_name = "core/admin/force_password_change.html"
    form_class = ForcePasswordChangeForm
    success_url = reverse_lazy('core:dashboard')

    def dispatch(self, request, *args, **kwargs):
        # Vérifier si le changement est vraiment requis
        if request.user.is_authenticated and not request.user.doit_changer_mot_de_passe:
            return redirect('core:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()

        # Désactiver le flag
        user = self.request.user
        user.doit_changer_mot_de_passe = False
        user.save(update_fields=['doit_changer_mot_de_passe'])

        messages.success(self.request, _("Mot de passe modifié avec succès"))
        return super().form_valid(form)


# =============================================================================
# VUE ADMINISTRATION DASHBOARD
# =============================================================================

class AdminDashboardView(LoginRequiredMixin, ManagerRequiredMixin, TemplateView):
    """Tableau de bord d'administration"""

    template_name = "core/admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Statistiques utilisateurs
        context['user_stats'] = {
            'total': User.objects.count(),
            'staff': User.objects.filter(type_utilisateur=User.TypeUtilisateur.STAFF).count(),
            'clients': User.objects.filter(type_utilisateur=User.TypeUtilisateur.CLIENT).count(),
            'actifs': User.objects.filter(is_active=True).count(),
            'nouveaux_30j': User.objects.filter(
                date_joined__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
        }

        # Statistiques invitations
        context['invitation_stats'] = {
            'en_attente': Invitation.objects.filter(
                statut=Invitation.Statut.EN_ATTENTE
            ).count(),
            'acceptees_30j': Invitation.objects.filter(
                statut=Invitation.Statut.ACCEPTEE,
                date_acceptation__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
        }

        # Derniers utilisateurs créés
        context['derniers_utilisateurs'] = User.objects.order_by('-date_joined')[:5]

        # Invitations en attente
        context['invitations_en_attente'] = Invitation.objects.filter(
            statut=Invitation.Statut.EN_ATTENTE
        ).order_by('-created_at')[:5]

        return context


# =============================================================================
# ADMINISTRATION - COLLABORATEURS FIDUCIAIRE (PRESTATAIRES)
# =============================================================================

class CollaborateurFiduciaireListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des affectations prestataires fiduciaires"""

    model = CollaborateurFiduciaire
    template_name = "core/admin/collaborateur_list.html"
    context_object_name = "collaborateurs"
    paginate_by = 25

    def get_queryset(self):
        queryset = CollaborateurFiduciaire.objects.select_related(
            'utilisateur', 'mandat', 'mandat__client', 'created_by'
        )

        # Filtres
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        utilisateur_id = self.request.GET.get('utilisateur')
        if utilisateur_id:
            queryset = queryset.filter(utilisateur_id=utilisateur_id)

        is_active = self.request.GET.get('active')
        if is_active == '1':
            queryset = queryset.filter(is_active=True)
        elif is_active == '0':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Mandats et prestataires pour les filtres
        context['mandats'] = Mandat.objects.filter(statut='ACTIF').order_by('numero')
        context['prestataires'] = User.objects.filter(
            type_utilisateur=User.TypeUtilisateur.STAFF,
            type_collaborateur='PRESTATAIRE',
            is_active=True
        ).order_by('last_name', 'first_name')

        return context


class CollaborateurFiduciaireCreateView(LoginRequiredMixin, ManagerRequiredMixin, CreateView):
    """Créer une affectation prestataire"""

    model = CollaborateurFiduciaire
    form_class = CollaborateurFiduciaireForm
    template_name = "core/admin/collaborateur_form.html"
    success_url = reverse_lazy('core:admin-collaborateur-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Affectation créée avec succès"))
        return super().form_valid(form)


class CollaborateurFiduciaireUpdateView(LoginRequiredMixin, ManagerRequiredMixin, UpdateView):
    """Modifier une affectation prestataire"""

    model = CollaborateurFiduciaire
    form_class = CollaborateurFiduciaireForm
    template_name = "core/admin/collaborateur_form.html"
    success_url = reverse_lazy('core:admin-collaborateur-list')

    def form_valid(self, form):
        messages.success(self.request, _("Affectation modifiée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def collaborateur_fiduciaire_toggle(request, pk):
    """Active/désactive une affectation prestataire"""
    if not (request.user.is_superuser or request.user.is_manager()):
        return HttpResponseForbidden()

    collab = get_object_or_404(CollaborateurFiduciaire, pk=pk)
    collab.is_active = not collab.is_active
    collab.save(update_fields=['is_active', 'updated_at'])

    status = _("activée") if collab.is_active else _("désactivée")
    messages.success(request, _("Affectation %(status)s") % {'status': status})

    return redirect('core:admin-collaborateur-list')


# =============================================================================
# VUES CLIENT — INVITATIONS (accessible par les clients responsables)
# =============================================================================

class MesInvitationsView(LoginRequiredMixin, ListView):
    """
    Vue client pour gérer ses invitations.
    Accessible par les clients responsables d'un mandat.
    """

    template_name = "core/client/mes_invitations.html"
    context_object_name = "invitations"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        # Client: invitations qu'il a envoyées
        if user.is_client_user():
            return Invitation.objects.filter(
                invite_par=user
            ).select_related('mandat', 'mandat__client', 'utilisateur_cree').order_by('-created_at')
        # Staff/admin: redirigé vers la vue admin
        return Invitation.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Mandats où le client est responsable (peut inviter)
        context['mandats_responsable'] = AccesMandat.objects.filter(
            utilisateur=user,
            est_responsable=True,
            is_active=True
        ).select_related('mandat', 'mandat__client')

        return context


class ClientInvitationCreateView(LoginRequiredMixin, FormView):
    """
    Vue client pour inviter un collaborateur sur un de ses mandats.
    Le mandat est pré-sélectionné via l'URL.
    """

    template_name = "core/client/invitation_create.html"
    form_class = InvitationClientForm

    def dispatch(self, request, *args, **kwargs):
        self.mandat = get_object_or_404(Mandat, pk=kwargs['mandat_pk'])

        # Vérifier que l'utilisateur peut inviter pour ce mandat
        if not request.user.peut_inviter_pour_mandat(self.mandat):
            messages.error(request, _("Vous n'avez pas le droit d'inviter pour ce mandat."))
            return redirect('core:mes-invitations')

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def get_initial(self):
        return {'mandat': self.mandat}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mandat'] = self.mandat

        # Quota restant
        acces = self.request.user.acces_mandats.filter(
            mandat=self.mandat,
            est_responsable=True,
            is_active=True
        ).first()
        context['acces'] = acces

        return context

    def get_success_url(self):
        return reverse('core:mes-invitations')

    def form_valid(self, form):
        try:
            invitation = InvitationService.creer_invitation_client(
                email=form.cleaned_data['email'],
                invite_par=self.request.user,
                mandat=self.mandat,
                permissions=list(form.cleaned_data.get('permissions', [])),
                est_responsable=form.cleaned_data.get('est_responsable', False),
                limite_invitations=form.cleaned_data.get('limite_invitations', 5),
                message=form.cleaned_data.get('message', ''),
                forcer_changement_mdp=form.cleaned_data.get('forcer_changement_mdp', True)
            )
            messages.success(
                self.request,
                _("Invitation envoyée à %(email)s. Code: %(code)s") % {
                    'email': invitation.email,
                    'code': invitation.code_court
                }
            )
        except (PermissionError, ValueError) as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def client_invitation_cancel(request, pk):
    """Annuler une invitation (côté client)"""
    invitation = get_object_or_404(Invitation, pk=pk, invite_par=request.user)

    try:
        InvitationService.annuler_invitation(invitation, request.user)
        messages.success(request, _("Invitation annulée"))
    except (PermissionError, ValueError) as e:
        messages.error(request, str(e))

    return redirect('core:mes-invitations')


class AcceptInvitationByCodeView(FormView):
    """Vue publique pour accepter une invitation via code court"""

    template_name = "core/client/accept_by_code.html"

    def get(self, request, *args, **kwargs):
        from core.forms import InvitationCodeForm
        return self.render_to_response(self.get_context_data(
            code_form=InvitationCodeForm()
        ))

    def post(self, request, *args, **kwargs):
        from core.forms import InvitationCodeForm
        code_form = InvitationCodeForm(request.POST)

        if code_form.is_valid():
            code = code_form.cleaned_data['code']
            invitation = InvitationService.valider_token(code)
            if invitation:
                # Rediriger vers la vue d'acceptation standard avec le token
                return redirect('core:invitation-accept', token=invitation.token)
            else:
                messages.error(request, _("Code d'invitation invalide ou expiré."))

        return self.render_to_response(self.get_context_data(
            code_form=code_form
        ))
