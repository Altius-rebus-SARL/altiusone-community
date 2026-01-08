# mailing/views.py
"""
Vues pour la gestion des emails.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from .models import ConfigurationEmail, TemplateEmail, EmailEnvoye, EmailRecu
from .forms import ConfigurationEmailForm, TemplateEmailForm
from .services import EmailService


class ManagerRequiredMixin(UserPassesTestMixin):
    """Mixin pour vérifier que l'utilisateur est manager ou superuser"""

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.is_manager()


# =============================================================================
# VUES CONFIGURATIONS EMAIL
# =============================================================================

class ConfigurationListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des configurations email"""

    model = ConfigurationEmail
    template_name = "mailing/configuration_list.html"
    context_object_name = "configurations"
    paginate_by = 25

    def get_queryset(self):
        return ConfigurationEmail.objects.order_by('-est_defaut', '-actif', 'nom')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total': ConfigurationEmail.objects.count(),
            'actives': ConfigurationEmail.objects.filter(actif=True).count(),
            'smtp': ConfigurationEmail.objects.filter(type_config='SMTP').count(),
            'imap': ConfigurationEmail.objects.filter(type_config__in=['IMAP', 'POP3']).count(),
        }
        return context


class ConfigurationDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Détail d'une configuration email"""

    model = ConfigurationEmail
    template_name = "mailing/configuration_detail.html"
    context_object_name = "configuration"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.object

        # Emails envoyés avec cette config
        context['emails_envoyes_count'] = EmailEnvoye.objects.filter(configuration=config).count()
        context['emails_recus_count'] = EmailRecu.objects.filter(configuration=config).count()

        # Derniers emails
        context['derniers_envoyes'] = EmailEnvoye.objects.filter(
            configuration=config
        ).order_by('-created_at')[:5]

        return context


class ConfigurationCreateView(LoginRequiredMixin, ManagerRequiredMixin, CreateView):
    """Création d'une configuration email"""

    model = ConfigurationEmail
    form_class = ConfigurationEmailForm
    template_name = "mailing/configuration_form.html"
    success_url = reverse_lazy('mailing:configuration-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Configuration créée avec succès"))
        return super().form_valid(form)


class ConfigurationUpdateView(LoginRequiredMixin, ManagerRequiredMixin, UpdateView):
    """Modification d'une configuration email"""

    model = ConfigurationEmail
    form_class = ConfigurationEmailForm
    template_name = "mailing/configuration_form.html"

    def get_success_url(self):
        return reverse('mailing:configuration-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Configuration modifiée avec succès"))
        return super().form_valid(form)


@login_required
@require_http_methods(["POST"])
def configuration_test(request, pk):
    """Teste une configuration email"""
    if not (request.user.is_superuser or request.user.is_manager()):
        return JsonResponse({'success': False, 'message': 'Non autorisé'}, status=403)

    config = get_object_or_404(ConfigurationEmail, pk=pk)
    service = EmailService()

    success, message = service.test_configuration(config)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': success, 'message': message})

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('mailing:configuration-detail', pk=pk)


# =============================================================================
# VUES TEMPLATES EMAIL
# =============================================================================

class TemplateListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des templates email"""

    model = TemplateEmail
    template_name = "mailing/template_list.html"
    context_object_name = "templates"
    paginate_by = 25

    def get_queryset(self):
        queryset = TemplateEmail.objects.select_related('configuration')

        # Filtre par type
        type_template = self.request.GET.get('type')
        if type_template:
            queryset = queryset.filter(type_template=type_template)

        return queryset.order_by('-actif', 'type_template', 'nom')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types'] = TemplateEmail.TypeTemplate.choices
        return context


class TemplateDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Détail d'un template email"""

    model = TemplateEmail
    template_name = "mailing/template_detail.html"
    context_object_name = "template"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Emails envoyés avec ce template
        context['emails_count'] = EmailEnvoye.objects.filter(
            content_type=self.object.type_template
        ).count()

        return context


class TemplateCreateView(LoginRequiredMixin, ManagerRequiredMixin, CreateView):
    """Création d'un template email"""

    model = TemplateEmail
    form_class = TemplateEmailForm
    template_name = "mailing/template_form.html"
    success_url = reverse_lazy('mailing:template-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("Template créé avec succès"))
        return super().form_valid(form)


class TemplateUpdateView(LoginRequiredMixin, ManagerRequiredMixin, UpdateView):
    """Modification d'un template email"""

    model = TemplateEmail
    form_class = TemplateEmailForm
    template_name = "mailing/template_form.html"

    def get_success_url(self):
        return reverse('mailing:template-detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Template modifié avec succès"))
        return super().form_valid(form)


@login_required
def template_preview(request, pk):
    """Prévisualisation d'un template email"""
    template = get_object_or_404(TemplateEmail, pk=pk)

    # Variables de test
    context = {
        'prenom': 'Jean',
        'nom': 'Dupont',
        'email': 'jean.dupont@example.com',
        'lien_acceptation': 'https://example.com/invitation/abc123',
        'date_expiration': '31/12/2026',
        'invite_par': request.user,
        'mandat': {'numero': 'M-2026-001'},
    }

    sujet, corps_html, corps_texte = template.render(context)

    return render(request, 'mailing/template_preview.html', {
        'template': template,
        'sujet_rendu': sujet,
        'corps_html_rendu': corps_html,
        'corps_texte_rendu': corps_texte,
    })


# =============================================================================
# VUES EMAILS ENVOYES
# =============================================================================

class EmailEnvoyeListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des emails envoyés"""

    model = EmailEnvoye
    template_name = "mailing/email_envoye_list.html"
    context_object_name = "emails"
    paginate_by = 50

    def get_queryset(self):
        queryset = EmailEnvoye.objects.select_related('configuration', 'utilisateur')

        # Filtres
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(destinataire__icontains=search)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = EmailEnvoye.Statut.choices
        context['stats'] = {
            'total': EmailEnvoye.objects.count(),
            'envoyes': EmailEnvoye.objects.filter(statut='ENVOYE').count(),
            'en_attente': EmailEnvoye.objects.filter(statut='EN_ATTENTE').count(),
            'echecs': EmailEnvoye.objects.filter(statut='ECHEC').count(),
        }
        return context


class EmailEnvoyeDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Détail d'un email envoyé"""

    model = EmailEnvoye
    template_name = "mailing/email_envoye_detail.html"
    context_object_name = "email"

    def get_queryset(self):
        return EmailEnvoye.objects.select_related('configuration', 'utilisateur', 'mandat')


@login_required
@require_http_methods(["POST"])
def email_renvoyer(request, pk):
    """Renvoyer un email en échec"""
    if not (request.user.is_superuser or request.user.is_manager()):
        messages.error(request, _("Non autorisé"))
        return redirect('mailing:email-envoye-list')

    email = get_object_or_404(EmailEnvoye, pk=pk)

    if email.statut not in ['ECHEC', 'EN_ATTENTE']:
        messages.warning(request, _("Cet email ne peut pas être renvoyé"))
        return redirect('mailing:email-envoye-detail', pk=pk)

    # Remettre en file d'attente
    email.statut = EmailEnvoye.Statut.EN_ATTENTE
    email.save(update_fields=['statut'])

    from .tasks import envoyer_email_task
    envoyer_email_task.delay(str(email.id))

    messages.success(request, _("Email remis en file d'envoi"))
    return redirect('mailing:email-envoye-detail', pk=pk)


# =============================================================================
# VUES EMAILS RECUS
# =============================================================================

class EmailRecuListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Liste des emails reçus"""

    model = EmailRecu
    template_name = "mailing/email_recu_list.html"
    context_object_name = "emails"
    paginate_by = 50

    def get_queryset(self):
        queryset = EmailRecu.objects.select_related('configuration', 'mandat_detecte', 'client_detecte')

        # Filtres
        lu = self.request.GET.get('lu')
        if lu == '1':
            queryset = queryset.filter(date_lecture__isnull=False)
        elif lu == '0':
            queryset = queryset.filter(date_lecture__isnull=True)

        important = self.request.GET.get('important')
        if important == '1':
            queryset = queryset.filter(est_important=True)

        search = self.request.GET.get('q')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(expediteur__icontains=search) |
                Q(expediteur_nom__icontains=search) |
                Q(sujet__icontains=search)
            )

        configuration = self.request.GET.get('configuration')
        if configuration:
            queryset = queryset.filter(configuration_id=configuration)

        analyse = self.request.GET.get('analyse')
        if analyse == '1':
            queryset = queryset.filter(analyse_effectuee=True)
        elif analyse == '0':
            queryset = queryset.filter(analyse_effectuee=False)

        return queryset.order_by('-date_reception')

    def get_context_data(self, **kwargs):
        from django.utils import timezone
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'total': EmailRecu.objects.count(),
            'non_lus': EmailRecu.objects.filter(date_lecture__isnull=True).count(),
            'analyses': EmailRecu.objects.filter(analyse_effectuee=True).count(),
            'avec_pieces': EmailRecu.objects.exclude(pieces_jointes=[]).exclude(pieces_jointes__isnull=True).count(),
        }
        context['configurations'] = ConfigurationEmail.objects.filter(
            actif=True
        ).exclude(imap_host='')
        # Configurations SMTP pour le modal de composition
        context['configurations_smtp'] = ConfigurationEmail.objects.filter(
            actif=True
        ).exclude(smtp_host='')
        context['today'] = timezone.now().date()
        return context


class EmailRecuDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Détail d'un email reçu"""

    model = EmailRecu
    template_name = "mailing/email_recu_detail.html"
    context_object_name = "email"

    def get_queryset(self):
        return EmailRecu.objects.select_related('configuration', 'mandat_detecte', 'client_detecte')

    def get_object(self, queryset=None):
        from django.utils import timezone
        obj = super().get_object(queryset)
        # Marquer comme lu
        if obj.date_lecture is None:
            obj.date_lecture = timezone.now()
            obj.save(update_fields=['date_lecture'])
        return obj


@login_required
@require_http_methods(["POST"])
def email_analyser(request, pk):
    """Analyser un email avec l'IA"""
    if not (request.user.is_superuser or request.user.is_manager()):
        messages.error(request, _("Non autorisé"))
        return redirect('mailing:email-recu-list')

    email = get_object_or_404(EmailRecu, pk=pk)

    from .tasks import analyser_email_task
    analyser_email_task.delay(str(email.id))

    messages.success(request, _("Analyse en cours..."))
    return redirect('mailing:email-recu-detail', pk=pk)


@login_required
@require_http_methods(["POST"])
def emails_fetch(request):
    """Récupérer les nouveaux emails"""
    if not (request.user.is_superuser or request.user.is_manager()):
        messages.error(request, _("Non autorisé"))
        return redirect('mailing:email-recu-list')

    from .tasks import fetch_emails_task
    fetch_emails_task.delay()

    messages.success(request, _("Récupération des emails lancée"))
    return redirect('mailing:email-recu-list')


@login_required
@require_http_methods(["POST"])
def email_compose(request):
    """Composer et envoyer un nouvel email"""
    if not (request.user.is_superuser or request.user.is_manager()):
        messages.error(request, _("Non autorisé"))
        return redirect('mailing:email-recu-list')

    from .forms import ComposeEmailForm

    form = ComposeEmailForm(request.POST, request.FILES)

    if form.is_valid():
        # Récupérer la configuration
        configuration = form.cleaned_data.get('configuration')
        if not configuration:
            configuration = ConfigurationEmail.objects.filter(
                actif=True, est_defaut=True
            ).exclude(smtp_host='').first()

        if not configuration:
            messages.error(request, _("Aucune configuration email disponible"))
            return redirect('mailing:email-recu-list')

        # Créer l'email
        email = EmailEnvoye.objects.create(
            configuration=configuration,
            utilisateur=request.user,
            destinataire=form.cleaned_data['destinataire'],
            cc=','.join(form.cleaned_data.get('cc', [])),
            sujet=form.cleaned_data['sujet'],
            corps_texte=form.cleaned_data['message'],
            statut=EmailEnvoye.Statut.EN_ATTENTE,
        )

        # Lancer l'envoi en tâche async
        from .tasks import envoyer_email_task
        envoyer_email_task.delay(str(email.id))

        messages.success(request, _("Email en cours d'envoi"))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect('mailing:email-recu-list')
