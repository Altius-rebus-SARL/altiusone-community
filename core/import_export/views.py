# core/import_export/views.py
"""
Vues génériques pour l'import/export de données.

Ces vues peuvent être utilisées directement ou servir de base
pour des vues personnalisées dans chaque module.
"""

from typing import Optional, Type, Dict, Any

from django.views.generic import FormView, View
from django.views.generic.base import TemplateResponseMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils.translation import gettext_lazy as _, gettext
from django.urls import reverse
from django.apps import apps

from import_export import resources

from core.permissions import BusinessPermissionMixin
from .forms import ImportForm, ExportForm
from .services import ImportExportService


# Registre des Resources par modèle
# Format: {'app_label.model_name': ResourceClass}
RESOURCE_REGISTRY: Dict[str, Type[resources.ModelResource]] = {}


def register_resource(app_label: str, model_name: str):
    """
    Décorateur pour enregistrer une Resource dans le registre.

    Usage:
        @register_resource('core', 'client')
        class ClientResource(BaseImportExportResource):
            ...
    """
    def decorator(resource_class: Type[resources.ModelResource]):
        key = f"{app_label}.{model_name}"
        RESOURCE_REGISTRY[key] = resource_class
        return resource_class
    return decorator


def get_resource_for_model(app_label: str, model_name: str) -> Optional[Type[resources.ModelResource]]:
    """
    Récupère la Resource enregistrée pour un modèle.

    Args:
        app_label: Label de l'app Django (ex: 'core')
        model_name: Nom du modèle en minuscules (ex: 'client')

    Returns:
        La classe Resource ou None
    """
    key = f"{app_label}.{model_name}"
    return RESOURCE_REGISTRY.get(key)


class ImportView(LoginRequiredMixin, BusinessPermissionMixin, FormView):
    """
    Vue générique d'import avec support dry-run.

    Cette vue affiche un formulaire d'upload et traite l'import.
    Elle peut être utilisée de deux manières:
    1. En héritant et en définissant resource_class
    2. Via l'URL dynamique avec app_label et model_name

    Attributes:
        resource_class: La classe Resource à utiliser
        template_name: Template pour le formulaire
        success_url: URL de redirection après import réussi
    """

    template_name = 'import_export/import_form.html'
    form_class = ImportForm
    resource_class: Optional[Type[resources.ModelResource]] = None
    business_permission = None  # À définir dans les sous-classes

    def get_resource_class(self) -> Type[resources.ModelResource]:
        """Retourne la classe Resource à utiliser."""
        if self.resource_class:
            return self.resource_class

        # Essayer de récupérer depuis les paramètres URL
        app_label = self.kwargs.get('app_label')
        model_name = self.kwargs.get('model_name')

        if app_label and model_name:
            resource_class = get_resource_for_model(app_label, model_name)
            if resource_class:
                return resource_class

        raise NotImplementedError(
            "Définissez resource_class ou passez app_label/model_name dans l'URL"
        )

    def get_resource(self) -> resources.ModelResource:
        """Instancie la Resource."""
        return self.get_resource_class()()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resource = self.get_resource()

        context['model_name'] = resource._meta.model._meta.verbose_name_plural
        context['template_url'] = self.get_template_url()

        return context

    def get_template_url(self) -> str:
        """Retourne l'URL pour télécharger le template."""
        app_label = self.kwargs.get('app_label', '')
        model_name = self.kwargs.get('model_name', '')

        if app_label and model_name:
            return reverse('import_export:template', kwargs={
                'app_label': app_label,
                'model_name': model_name,
            })

        return ''

    def get_import_context(self) -> Dict[str, Any]:
        """Retourne le contexte pour l'import."""
        request = self.request
        context = {
            'user': request.user,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }

        # Ajouter le mandat si disponible
        mandat_id = self.kwargs.get('mandat_id') or request.GET.get('mandat')
        if mandat_id:
            from core.models import Mandat
            try:
                context['mandat'] = Mandat.objects.get(pk=mandat_id)
            except Mandat.DoesNotExist:
                pass

        return context

    def _get_client_ip(self, request: HttpRequest) -> Optional[str]:
        """Récupère l'adresse IP du client."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def form_valid(self, form):
        """Traite l'import après validation du formulaire."""
        uploaded_file = form.cleaned_data['import_file']
        dry_run = form.cleaned_data.get('dry_run', True)

        resource = self.get_resource()
        context = self.get_import_context()

        result = ImportExportService.import_file(
            file=uploaded_file,
            resource=resource,
            dry_run=dry_run,
            **context
        )

        # Afficher le résultat
        if result.get('success'):
            if dry_run:
                messages.info(
                    self.request,
                    gettext("Simulation réussie. {message}").format(
                        message=result.get('message', '')
                    )
                )
                # Rester sur la page pour confirmer l'import réel
                return self.render_to_response(self.get_context_data(
                    form=form,
                    result=result,
                    show_confirm=True,
                ))
            else:
                messages.success(
                    self.request,
                    gettext("Import réussi. {message}").format(
                        message=result.get('message', '')
                    )
                )
                return redirect(self.get_success_url())
        else:
            messages.error(
                self.request,
                result.get('error', gettext("Erreur lors de l'import."))
            )
            return self.render_to_response(self.get_context_data(
                form=form,
                result=result,
            ))

    def get_success_url(self):
        """URL de redirection après import réussi."""
        app_label = self.kwargs.get('app_label', '')
        model_name = self.kwargs.get('model_name', '')

        # Essayer de construire l'URL de la liste
        try:
            return reverse(f'{app_label}:{model_name}-list')
        except:
            return '/'


class ExportView(LoginRequiredMixin, BusinessPermissionMixin, View):
    """
    Vue générique d'export.

    Exporte les données filtrées au format demandé (CSV ou Excel).
    """

    resource_class: Optional[Type[resources.ModelResource]] = None
    business_permission = None

    def get_resource_class(self) -> Type[resources.ModelResource]:
        """Retourne la classe Resource à utiliser."""
        if self.resource_class:
            return self.resource_class

        app_label = self.kwargs.get('app_label')
        model_name = self.kwargs.get('model_name')

        if app_label and model_name:
            resource_class = get_resource_for_model(app_label, model_name)
            if resource_class:
                return resource_class

        raise NotImplementedError(
            "Définissez resource_class ou passez app_label/model_name dans l'URL"
        )

    def get_resource(self) -> resources.ModelResource:
        """Instancie la Resource."""
        return self.get_resource_class()()

    def get_queryset(self):
        """Retourne le queryset à exporter."""
        resource = self.get_resource()

        # Récupérer le modèle depuis la Resource
        model = resource._meta.model
        queryset = model.objects.all()

        # Appliquer les filtres de la Resource (accès Mandat, etc.)
        if hasattr(resource, 'get_queryset'):
            queryset = resource.get_queryset()

        # Appliquer les filtres de l'URL
        # TODO: intégrer avec django-filter si disponible

        return queryset

    def get_filename(self, format_type: str) -> str:
        """Retourne le nom du fichier d'export."""
        resource = self.get_resource()
        model_name = resource._meta.model._meta.model_name
        return f"{model_name}.{format_type}"

    def get(self, request, *args, **kwargs):
        """Traite la requête d'export."""
        format_type = request.GET.get('format', 'xlsx')

        if format_type not in ['csv', 'xlsx']:
            messages.error(request, _("Format invalide."))
            return redirect(request.META.get('HTTP_REFERER', '/'))

        queryset = self.get_queryset()
        resource = self.get_resource()
        filename = self.get_filename(format_type)

        return ImportExportService.export_queryset(
            queryset=queryset,
            resource=resource,
            format_type=format_type,
            filename=filename,
        )


class TemplateDownloadView(LoginRequiredMixin, View):
    """
    Vue pour télécharger un template vide.

    Génère un fichier CSV ou Excel avec les en-têtes corrects
    et une ligne d'exemple.
    """

    resource_class: Optional[Type[resources.ModelResource]] = None

    def get_resource_class(self) -> Type[resources.ModelResource]:
        """Retourne la classe Resource à utiliser."""
        if self.resource_class:
            return self.resource_class

        app_label = self.kwargs.get('app_label')
        model_name = self.kwargs.get('model_name')

        if app_label and model_name:
            resource_class = get_resource_for_model(app_label, model_name)
            if resource_class:
                return resource_class

        raise NotImplementedError(
            "Définissez resource_class ou passez app_label/model_name dans l'URL"
        )

    def get_resource(self) -> resources.ModelResource:
        """Instancie la Resource."""
        return self.get_resource_class()()

    def get_filename(self, format_type: str) -> str:
        """Retourne le nom du fichier template."""
        resource = self.get_resource()
        model_name = resource._meta.model._meta.model_name
        return f"template_{model_name}.{format_type}"

    def get(self, request, *args, **kwargs):
        """Génère et retourne le template."""
        format_type = request.GET.get('format', 'xlsx')

        if format_type not in ['csv', 'xlsx']:
            return JsonResponse({'error': _("Format invalide.")}, status=400)

        resource = self.get_resource()
        filename = self.get_filename(format_type)

        return ImportExportService.generate_template(
            resource=resource,
            format_type=format_type,
            filename=filename,
            include_example=True,
        )


class ImportResultsView(LoginRequiredMixin, TemplateResponseMixin, View):
    """
    Vue pour afficher les résultats détaillés d'un import.

    Affiche un rapport avec:
    - Nombre de lignes créées/mises à jour/ignorées
    - Liste des erreurs avec numéros de ligne
    - Option pour réessayer l'import
    """

    template_name = 'import_export/import_results.html'

    def get(self, request, *args, **kwargs):
        """Affiche les résultats stockés en session."""
        result = request.session.get('import_result', {})

        if not result:
            messages.warning(request, _("Aucun résultat d'import à afficher."))
            return redirect('/')

        return self.render_to_response({
            'result': result,
        })


# ============================================================================
# API Views (pour les appels AJAX/REST)
# ============================================================================

class ImportAPIView(LoginRequiredMixin, View):
    """
    API endpoint pour l'import de données.

    POST /api/import/<app>/<model>/
    Body: multipart/form-data avec 'file' et optionnel 'dry_run'
    """

    def post(self, request, app_label: str, model_name: str):
        """Traite l'import via API."""
        resource_class = get_resource_for_model(app_label, model_name)

        if not resource_class:
            return JsonResponse(
                {'error': _("Resource non trouvée pour ce modèle.")},
                status=404
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse(
                {'error': _("Aucun fichier fourni.")},
                status=400
            )

        dry_run = request.POST.get('dry_run', 'true').lower() == 'true'

        resource = resource_class()
        context = {
            'user': request.user,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }

        result = ImportExportService.import_file(
            file=uploaded_file,
            resource=resource,
            dry_run=dry_run,
            **context
        )

        return JsonResponse(result)


class ExportAPIView(LoginRequiredMixin, View):
    """
    API endpoint pour l'export de données.

    GET /api/export/<app>/<model>/?format=xlsx
    """

    def get(self, request, app_label: str, model_name: str):
        """Traite l'export via API."""
        resource_class = get_resource_for_model(app_label, model_name)

        if not resource_class:
            return JsonResponse(
                {'error': _("Resource non trouvée pour ce modèle.")},
                status=404
            )

        format_type = request.GET.get('format', 'xlsx')
        if format_type not in ['csv', 'xlsx']:
            return JsonResponse(
                {'error': _("Format invalide.")},
                status=400
            )

        resource = resource_class()
        queryset = resource._meta.model.objects.all()

        # Appliquer le filtrage de la Resource
        if hasattr(resource, 'get_queryset'):
            resource.user = request.user
            resource._load_accessible_mandats()
            queryset = resource.get_queryset()

        filename = f"{model_name}.{format_type}"

        return ImportExportService.export_queryset(
            queryset=queryset,
            resource=resource,
            format_type=format_type,
            filename=filename,
        )


class TemplateAPIView(LoginRequiredMixin, View):
    """
    API endpoint pour télécharger un template.

    GET /api/template/<app>/<model>/?format=xlsx
    """

    def get(self, request, app_label: str, model_name: str):
        """Génère le template via API."""
        resource_class = get_resource_for_model(app_label, model_name)

        if not resource_class:
            return JsonResponse(
                {'error': _("Resource non trouvée pour ce modèle.")},
                status=404
            )

        format_type = request.GET.get('format', 'xlsx')
        if format_type not in ['csv', 'xlsx']:
            return JsonResponse(
                {'error': _("Format invalide.")},
                status=400
            )

        resource = resource_class()
        filename = f"template_{model_name}.{format_type}"

        return ImportExportService.generate_template(
            resource=resource,
            format_type=format_type,
            filename=filename,
        )
