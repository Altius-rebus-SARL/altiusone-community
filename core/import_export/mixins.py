# core/import_export/mixins.py
"""
Mixins pour intégrer l'import/export dans les vues existantes.

Ces mixins ajoutent automatiquement les fonctionnalités d'import/export
aux vues de liste (ListView, FilterView) et aux ViewSets REST.
"""

from typing import Optional, Type, Dict, Any, List
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.views import View
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _, gettext
from django.urls import reverse

from import_export import resources

from .services import ImportExportService


class ImportExportViewMixin:
    """
    Mixin pour ajouter l'import/export aux CBV (Class-Based Views).

    Ajoute les méthodes et URLs pour:
    - Exporter les données filtrées
    - Importer depuis un fichier CSV/Excel
    - Télécharger un template vide

    Usage:
        class ClientListView(ImportExportViewMixin, FilterView):
            model = Client
            resource_class = ClientResource
            import_permission = 'core.import_client'
            export_permission = 'core.export_client'
    """

    # Resource à utiliser pour l'import/export
    resource_class: Optional[Type[resources.ModelResource]] = None

    # Permissions requises
    import_permission: Optional[str] = None
    export_permission: Optional[str] = None

    # Formats supportés
    export_formats: List[str] = ['csv', 'xlsx']
    import_formats: List[str] = ['csv', 'xlsx']

    # Nom de base pour les fichiers exportés
    export_filename: Optional[str] = None

    def get_resource_class(self) -> Type[resources.ModelResource]:
        """Retourne la classe Resource à utiliser."""
        if self.resource_class is None:
            raise NotImplementedError(
                "Vous devez définir resource_class ou surcharger get_resource_class()"
            )
        return self.resource_class

    def get_resource_kwargs(self) -> Dict[str, Any]:
        """Retourne les kwargs pour instancier la Resource."""
        return {}

    def get_resource(self) -> resources.ModelResource:
        """Instancie et retourne la Resource."""
        return self.get_resource_class()(**self.get_resource_kwargs())

    def get_export_filename(self, format_type: str) -> str:
        """Retourne le nom du fichier d'export."""
        if self.export_filename:
            base_name = self.export_filename
        else:
            base_name = self.model._meta.model_name

        return f"{base_name}.{format_type}"

    def can_import(self, request: HttpRequest) -> bool:
        """Vérifie si l'utilisateur peut importer."""
        if self.import_permission:
            return request.user.has_perm(self.import_permission)
        return request.user.is_staff

    def can_export(self, request: HttpRequest) -> bool:
        """Vérifie si l'utilisateur peut exporter."""
        if self.export_permission:
            return request.user.has_perm(self.export_permission)
        return request.user.is_authenticated

    def get_export_queryset(self):
        """
        Retourne le queryset pour l'export.
        Par défaut, utilise le queryset filtré de la vue.
        """
        if hasattr(self, 'get_queryset'):
            return self.get_queryset()
        return self.model.objects.all()

    def get_import_context(self, request: HttpRequest) -> Dict[str, Any]:
        """Retourne le contexte pour l'import (user, mandat, etc.)."""
        context = {
            'user': request.user,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }

        # Ajouter le mandat du contexte si disponible
        if hasattr(self, 'get_mandat'):
            context['mandat'] = self.get_mandat()
        elif hasattr(request, 'mandat'):
            context['mandat'] = request.mandat

        return context

    def _get_client_ip(self, request: HttpRequest) -> Optional[str]:
        """Récupère l'adresse IP du client."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def get_context_data(self, **kwargs):
        """Ajoute les données d'import/export au contexte."""
        context = super().get_context_data(**kwargs)

        context['can_import'] = self.can_import(self.request)
        context['can_export'] = self.can_export(self.request)
        context['export_formats'] = self.export_formats
        context['import_formats'] = self.import_formats

        # URLs d'import/export
        if hasattr(self, 'get_import_url'):
            context['import_url'] = self.get_import_url()
        if hasattr(self, 'get_export_url'):
            context['export_url'] = self.get_export_url()
        if hasattr(self, 'get_template_url'):
            context['template_url'] = self.get_template_url()

        return context


class ExportMixin(ImportExportViewMixin):
    """
    Mixin spécifique pour l'export.

    Ajoute une méthode export() qui peut être appelée par une URL.
    """

    def export(self, request: HttpRequest, format_type: str = 'xlsx') -> HttpResponse:
        """
        Exporte les données au format demandé.

        Args:
            request: La requête HTTP
            format_type: 'csv' ou 'xlsx'

        Returns:
            HttpResponse avec le fichier à télécharger
        """
        if not self.can_export(request):
            messages.error(request, _("Vous n'avez pas la permission d'exporter."))
            return redirect(request.path)

        queryset = self.get_export_queryset()
        resource = self.get_resource()
        filename = self.get_export_filename(format_type)

        return ImportExportService.export_queryset(
            queryset=queryset,
            resource=resource,
            format_type=format_type,
            filename=filename,
        )


class ImportMixin(ImportExportViewMixin):
    """
    Mixin spécifique pour l'import.

    Ajoute les méthodes pour:
    - Afficher le formulaire d'import
    - Traiter l'import (avec dry-run)
    - Télécharger le template
    """

    def get_import_form_class(self):
        """Retourne la classe du formulaire d'import."""
        from .forms import ImportForm
        return ImportForm

    def import_data(
        self,
        request: HttpRequest,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Importe les données depuis le fichier uploadé.

        Args:
            request: La requête HTTP avec le fichier
            dry_run: Si True, simule l'import sans modifier la DB

        Returns:
            Dict avec les résultats de l'import
        """
        if not self.can_import(request):
            return {
                'success': False,
                'error': gettext("Vous n'avez pas la permission d'importer."),
            }

        uploaded_file = request.FILES.get('import_file')
        if not uploaded_file:
            return {
                'success': False,
                'error': gettext("Aucun fichier fourni."),
            }

        resource = self.get_resource()
        context = self.get_import_context(request)

        return ImportExportService.import_file(
            file=uploaded_file,
            resource=resource,
            dry_run=dry_run,
            **context
        )

    def download_template(
        self,
        request: HttpRequest,
        format_type: str = 'xlsx'
    ) -> HttpResponse:
        """
        Génère et retourne un template vide à remplir.

        Args:
            request: La requête HTTP
            format_type: 'csv' ou 'xlsx'

        Returns:
            HttpResponse avec le fichier template
        """
        resource = self.get_resource()
        filename = f"template_{self.get_export_filename(format_type)}"

        return ImportExportService.generate_template(
            resource=resource,
            format_type=format_type,
            filename=filename,
        )


class ImportExportAPIViewMixin:
    """
    Mixin pour ajouter l'import/export aux ViewSets REST.

    Ajoute des actions:
    - POST /export/ - Exporter les données
    - POST /import/ - Importer des données
    - GET /template/ - Télécharger le template

    Usage:
        class ClientViewSet(ImportExportAPIViewMixin, ModelViewSet):
            queryset = Client.objects.all()
            resource_class = ClientResource
    """

    resource_class: Optional[Type[resources.ModelResource]] = None

    def get_resource_class(self) -> Type[resources.ModelResource]:
        """Retourne la classe Resource à utiliser."""
        if self.resource_class is None:
            raise NotImplementedError(
                "Vous devez définir resource_class ou surcharger get_resource_class()"
            )
        return self.resource_class

    def get_resource(self) -> resources.ModelResource:
        """Instancie et retourne la Resource."""
        return self.get_resource_class()()

    def get_export_queryset(self):
        """Retourne le queryset pour l'export."""
        return self.filter_queryset(self.get_queryset())

    def _get_import_context(self, request) -> Dict[str, Any]:
        """Retourne le contexte pour l'import."""
        return {
            'user': request.user,
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }

    def _get_client_ip(self, request) -> Optional[str]:
        """Récupère l'adresse IP du client."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    # Ces méthodes seront décorées avec @action dans les ViewSets

    def export_action(self, request):
        """
        Action d'export pour ViewSet.

        POST /api/v1/{resource}/export/
        Body: {"format": "xlsx"}
        """
        format_type = request.data.get('format', 'xlsx')

        if format_type not in ['csv', 'xlsx']:
            return JsonResponse(
                {'error': _("Format invalide. Utilisez 'csv' ou 'xlsx'.")},
                status=400
            )

        queryset = self.get_export_queryset()
        resource = self.get_resource()
        model_name = self.get_queryset().model._meta.model_name
        filename = f"{model_name}.{format_type}"

        return ImportExportService.export_queryset(
            queryset=queryset,
            resource=resource,
            format_type=format_type,
            filename=filename,
        )

    def import_action(self, request):
        """
        Action d'import pour ViewSet.

        POST /api/v1/{resource}/import/
        Body: FormData avec 'file' et optionnel 'dry_run'
        """
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse(
                {'error': _("Aucun fichier fourni.")},
                status=400
            )

        dry_run = request.data.get('dry_run', 'false').lower() == 'true'

        resource = self.get_resource()
        context = self._get_import_context(request)

        result = ImportExportService.import_file(
            file=uploaded_file,
            resource=resource,
            dry_run=dry_run,
            **context
        )

        return JsonResponse(result)

    def template_action(self, request):
        """
        Action pour télécharger le template.

        GET /api/v1/{resource}/template/?format=xlsx
        """
        format_type = request.query_params.get('format', 'xlsx')

        if format_type not in ['csv', 'xlsx']:
            return JsonResponse(
                {'error': _("Format invalide. Utilisez 'csv' ou 'xlsx'.")},
                status=400
            )

        resource = self.get_resource()
        model_name = self.get_queryset().model._meta.model_name
        filename = f"template_{model_name}.{format_type}"

        return ImportExportService.generate_template(
            resource=resource,
            format_type=format_type,
            filename=filename,
        )
