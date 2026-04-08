# documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from core.permissions import BusinessPermissionMixin, permission_required_business
from core.mixins import SearchMixin
from django.db.models import Q, Count, Sum
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import mimetypes
import os

from .models import (
    Document,
    Dossier,
    CategorieDocument,
    TypeDocument,
    TraitementDocument,
    Conversation,
)
from .forms import DocumentForm, DocumentUploadForm, DossierForm, TypeDocumentForm, CategorieDocumentForm
from .filters import DocumentFilter, DossierFilter
from core.models import Mandat


# ============ CHAT AI ============

class ChatView(LoginRequiredMixin, TemplateView):
    """
    Vue principale pour le chat avec l'assistant AI.

    Affiche l'interface de chat qui utilise l'API REST
    pour communiquer avec le backend.
    """
    template_name = "documents/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Recuperer les conversations de l'utilisateur
        context['conversations'] = Conversation.objects.filter(
            utilisateur=user,
            statut='ACTIVE'
        ).select_related('document').prefetch_related('mandats').order_by('-updated_at')[:20]

        # Mandats accessibles pour le filtre
        if user.is_manager():
            context['mandats'] = Mandat.objects.filter(
                is_active=True,
                statut='ACTIF'
            ).select_related('client')
        else:
            context['mandats'] = Mandat.objects.filter(
                Q(responsable=user) | Q(equipe=user),
                is_active=True,
                statut='ACTIF'
            ).distinct().select_related('client')

        # Conversation selectionnee (si ID dans l'URL)
        conversation_id = self.request.GET.get('conversation')
        if conversation_id:
            try:
                context['current_conversation'] = Conversation.objects.get(
                    id=conversation_id,
                    utilisateur=user
                )
            except Conversation.DoesNotExist:
                pass

        # Verifier si le service AI est disponible
        from .ai_service import ai_service
        context['ai_enabled'] = ai_service.enabled

        # Utilisateurs actifs pour la messagerie (exclure l'utilisateur courant)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        context['users'] = User.objects.filter(
            is_active=True
        ).exclude(id=user.id).select_related('role').order_by('first_name', 'last_name')

        return context


# ============ DOSSIERS ============


class DossierListView(SearchMixin, LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """
    Liste des dossiers avec navigation hiérarchique:
    - Niveau 0: Clients (racine)
    - Niveau 1: Mandats du client sélectionné
    - Niveau 2+: Dossiers et sous-dossiers
    """

    model = Dossier
    template_name = "documents/dossier_list.html"
    context_object_name = "dossiers"
    paginate_by = 50
    business_permission = 'documents.view_documents'
    search_fields = ['nom', 'description', 'mandat__numero', 'client__raison_sociale']

    def get_queryset(self):
        from core.models import Client

        user = self.request.user
        client_id = self.request.GET.get('client')
        mandat_id = self.request.GET.get('mandat')
        parent_id = self.request.GET.get('parent')

        # Si on a un parent, on affiche les sous-dossiers
        if parent_id:
            queryset = Dossier.objects.filter(
                parent_id=parent_id,
                is_active=True
            ).select_related("parent", "client", "mandat", "proprietaire")
        # Si on a un mandat, on affiche les dossiers racines du mandat
        elif mandat_id:
            queryset = Dossier.objects.filter(
                Q(mandat_id=mandat_id) | Q(mandat__isnull=True, client__mandats__id=mandat_id),
                parent__isnull=True,
                is_active=True
            ).select_related("parent", "client", "mandat", "proprietaire").distinct()
        # Si on a un client, on affiche les mandats (pas les dossiers)
        elif client_id:
            # Retourne un queryset vide - on affichera les mandats dans le contexte
            queryset = Dossier.objects.none()
        else:
            # Niveau racine: on retourne un queryset vide, on affichera les clients
            queryset = Dossier.objects.none()

        # Annoter avec le nombre de documents
        queryset = queryset.annotate(nb_documents=Count("documents"))

        # Filtrer selon le rôle
        if not user.is_manager() and (mandat_id or parent_id):
            queryset = queryset.filter(
                Q(mandat__responsable=user)
                | Q(mandat__equipe=user)
                | Q(proprietaire=user)
            ).distinct()

        self.filterset = None
        return self.apply_search(queryset.order_by("nom"))

    def get_context_data(self, **kwargs):
        from core.models import Client, Mandat

        context = super().get_context_data(**kwargs)
        user = self.request.user

        client_id = self.request.GET.get('client')
        mandat_id = self.request.GET.get('mandat')
        parent_id = self.request.GET.get('parent')

        # Niveau de navigation actuel
        context['nav_level'] = 'clients'  # Par défaut
        context['current_client'] = None
        context['current_mandat'] = None
        context['current_parent'] = None
        context['breadcrumb_items'] = []

        # Construire le fil d'ariane et déterminer le niveau
        if parent_id:
            # On navigue dans les sous-dossiers
            parent = Dossier.objects.select_related('client', 'mandat__client', 'parent').get(id=parent_id)
            context['current_parent'] = parent
            context['nav_level'] = 'subfolders'

            # Construire l'arborescence complète
            breadcrumb = []
            current = parent
            while current:
                breadcrumb.insert(0, current)
                current = current.parent
            context['breadcrumb_items'] = breadcrumb

            if parent.mandat:
                context['current_mandat'] = parent.mandat
                context['current_client'] = parent.mandat.client
            elif parent.client:
                context['current_client'] = parent.client

            # Récupérer les documents de ce dossier
            context['documents'] = Document.objects.filter(
                dossier=parent,
                is_active=True
            ).select_related('type_document').order_by('-date_upload')

        elif mandat_id:
            # On affiche les dossiers d'un mandat
            mandat = Mandat.objects.select_related('client').get(id=mandat_id)
            context['current_mandat'] = mandat
            context['current_client'] = mandat.client
            context['nav_level'] = 'dossiers'

            # Récupérer TOUS les documents du mandat (y compris ceux dans des dossiers)
            # Si aucun dossier racine n'existe, on affiche tous les documents
            context['documents'] = Document.objects.filter(
                mandat=mandat,
                is_active=True
            ).select_related('type_document', 'dossier').order_by('-date_upload')

        elif client_id:
            # On affiche les mandats d'un client
            client = Client.objects.get(id=client_id)
            context['current_client'] = client
            context['nav_level'] = 'mandats'

            # Récupérer les mandats du client
            mandats_qs = Mandat.objects.filter(
                client_id=client_id,
                is_active=True,
                statut='ACTIF'
            )
            if not user.is_manager():
                mandats_qs = mandats_qs.filter(
                    Q(responsable=user) | Q(equipe=user)
                ).distinct()

            # Annoter avec le nombre de dossiers et documents
            mandats_qs = mandats_qs.annotate(
                nb_dossiers=Count('dossiers', distinct=True),
                nb_documents=Count('documents', distinct=True)
            )
            context['mandats'] = mandats_qs.order_by('numero')

        else:
            # Niveau racine: afficher les clients
            context['nav_level'] = 'clients'

            # Récupérer les clients qui ont des dossiers
            clients_qs = Client.objects.filter(
                is_active=True
            ).annotate(
                nb_mandats=Count('mandats', filter=Q(mandats__is_active=True, mandats__statut='ACTIF'), distinct=True),
                nb_dossiers=Count('dossiers', distinct=True),
                nb_documents=Count('mandats__documents', distinct=True)
            ).filter(
                Q(nb_mandats__gt=0) | Q(nb_dossiers__gt=0)
            )

            if not user.is_manager():
                # Filtrer les clients accessibles
                accessible_mandats = Mandat.objects.filter(
                    Q(responsable=user) | Q(equipe=user)
                ).values_list('client_id', flat=True)
                clients_qs = clients_qs.filter(id__in=accessible_mandats)

            context['clients'] = clients_qs.order_by('raison_sociale')

        # Statistiques CONTEXTUELLES selon le niveau de navigation
        if parent_id:
            # Stats du dossier courant (récursif)
            parent = context['current_parent']

            # Fonction pour récupérer tous les IDs de sous-dossiers récursivement
            def get_all_subfolder_ids(dossier):
                ids = [dossier.id]
                for sous_dossier in Dossier.objects.filter(parent=dossier, is_active=True):
                    ids.extend(get_all_subfolder_ids(sous_dossier))
                return ids

            all_folder_ids = get_all_subfolder_ids(parent)

            # Compter les sous-dossiers directs
            total_dossiers = Dossier.objects.filter(parent=parent, is_active=True).count()
            # Compter TOUS les documents (dossier actuel + tous les sous-dossiers récursivement)
            doc_stats = Document.objects.filter(dossier_id__in=all_folder_ids, is_active=True).aggregate(
                total_docs=Count('id'),
                total_size=Sum('taille')
            )
        elif mandat_id:
            # Stats du mandat courant
            mandat = context['current_mandat']
            total_dossiers = Dossier.objects.filter(
                Q(mandat=mandat) | Q(mandat__isnull=True, client=mandat.client),
                parent__isnull=True,
                is_active=True
            ).distinct().count()
            doc_stats = Document.objects.filter(mandat=mandat, is_active=True).aggregate(
                total_docs=Count('id'),
                total_size=Sum('taille')
            )
        elif client_id:
            # Stats du client courant
            client = context['current_client']
            total_dossiers = Dossier.objects.filter(
                Q(client=client) | Q(mandat__client=client),
                is_active=True
            ).distinct().count()
            doc_stats = Document.objects.filter(
                mandat__client=client,
                is_active=True
            ).aggregate(
                total_docs=Count('id'),
                total_size=Sum('taille')
            )
        else:
            # Stats globales (niveau racine - tous les clients)
            if user.is_manager():
                total_dossiers = Dossier.objects.filter(is_active=True).count()
                doc_stats = Document.objects.filter(is_active=True).aggregate(
                    total_docs=Count('id'),
                    total_size=Sum('taille')
                )
            else:
                accessible_mandats = Mandat.objects.filter(
                    Q(responsable=user) | Q(equipe=user)
                ).values_list('id', flat=True)
                total_dossiers = Dossier.objects.filter(
                    Q(mandat_id__in=accessible_mandats) | Q(proprietaire=user),
                    is_active=True
                ).distinct().count()
                doc_stats = Document.objects.filter(
                    Q(mandat_id__in=accessible_mandats),
                    is_active=True
                ).aggregate(
                    total_docs=Count('id'),
                    total_size=Sum('taille')
                )

        context["stats"] = {
            "total": total_dossiers,
            "total_documents": doc_stats['total_docs'] or 0,
            "total_taille": doc_stats['total_size'] or 0,
        }

        context["filter"] = self.filterset

        # Construire les paramètres de contexte pour les URLs de documents
        params = []
        if context.get('current_client'):
            params.append(f"client={context['current_client'].id}")
        if context.get('current_mandat'):
            params.append(f"mandat={context['current_mandat'].id}")
        if context.get('current_parent'):
            params.append(f"parent={context['current_parent'].id}")
        context['context_params'] = '&'.join(params)

        # Documents non classés (sans dossier) pour le niveau mandat
        if mandat_id and not parent_id:
            context['documents_non_classes'] = Document.objects.filter(
                mandat_id=mandat_id,
                dossier__isnull=True,
                is_active=True
            ).select_related('type_document').order_by('-date_upload')[:20]

        return context


class DossierDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un dossier avec liste complète des documents"""

    model = Dossier
    template_name = "documents/dossier_detail.html"
    context_object_name = "dossier"
    business_permission = 'documents.view_documents'
    paginate_by = 50

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("parent", "client", "mandat", "proprietaire")
            .prefetch_related("sous_dossiers")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dossier = self.object

        # Documents du dossier - TOUS les documents avec pagination
        documents_qs = Document.objects.filter(
            dossier=dossier,
            is_active=True
        ).select_related(
            "type_document", "categorie", "mandat__client"
        ).order_by("-date_upload")

        # Appliquer filtre si present
        if self.request.GET:
            filterset = DocumentFilter(self.request.GET, queryset=documents_qs)
            if filterset.is_valid():
                documents_qs = filterset.qs
            context["filter"] = filterset
        else:
            context["filter"] = DocumentFilter(queryset=documents_qs)

        # Pagination manuelle
        page = self.request.GET.get('page', 1)
        from django.core.paginator import Paginator
        paginator = Paginator(documents_qs, self.paginate_by)
        context["documents"] = paginator.get_page(page)
        context["documents_count"] = documents_qs.count()

        # Sous-dossiers
        context["sous_dossiers"] = dossier.sous_dossiers.filter(is_active=True).annotate(
            nb_documents=Count('documents')
        )

        # Arborescence (breadcrumb)
        context["arborescence"] = self.get_arborescence(dossier)

        # Stats du dossier
        context["stats"] = {
            "total_documents": documents_qs.count(),
            "total_taille": documents_qs.aggregate(Sum('taille'))['taille__sum'] or 0,
            "sous_dossiers": dossier.sous_dossiers.filter(is_active=True).count(),
        }

        return context

    def get_arborescence(self, dossier):
        """Construit le fil d'ariane"""
        arbo = []
        current = dossier
        while current:
            arbo.insert(0, current)
            current = current.parent
        return arbo


class DossierCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un dossier"""

    model = Dossier
    form_class = DossierForm
    template_name = "documents/dossier_form.html"
    business_permission = 'documents.add_document'

    def get_success_url(self):
        return reverse_lazy("documents:dossier-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passer le mandat initial pour le filtrage des dossiers parents
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            try:
                kwargs['mandat'] = Mandat.objects.get(pk=mandat_id)
            except Mandat.DoesNotExist:
                pass
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        # Pré-sélectionner le mandat si passé en paramètre
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            initial['mandat'] = mandat_id
        return initial

    def form_valid(self, form):
        form.instance.proprietaire = self.request.user
        messages.success(self.request, _("Dossier créé avec succès"))
        return super().form_valid(form)


# ============ DOCUMENTS ============


class DocumentListView(SearchMixin, LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des documents"""

    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"
    paginate_by = 50
    business_permission = 'documents.view_documents'
    search_fields = ['nom_fichier', 'description', 'mandat__numero', 'mandat__client__raison_sociale']

    def get_queryset(self):
        queryset = Document.objects.select_related(
            "mandat__client", "dossier", "type_document", "categorie", "valide_par"
        ).filter(is_active=True)

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user) | Q(mandat__equipe=user)
            ).distinct()

        # Appliquer les filtres
        if self.request.GET:
            self.filterset = DocumentFilter(self.request.GET, queryset=queryset)
            if self.filterset.is_valid():
                return self.apply_search(self.filterset.qs.order_by("-date_upload"))

        self.filterset = DocumentFilter(queryset=queryset)
        return self.apply_search(queryset.order_by("-date_upload"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        full_queryset = self.get_queryset()
        context["stats"] = {
            "total": full_queryset.count(),
            "en_attente": full_queryset.filter(statut_validation="EN_ATTENTE").count(),
            "valide": full_queryset.filter(statut_validation="VALIDE").count(),
            "taille_totale": full_queryset.aggregate(Sum("taille"))["taille__sum"] or 0,
        }

        return context


class DocumentDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un document"""

    model = Document
    template_name = "documents/document_detail.html"
    context_object_name = "document"
    business_permission = 'documents.view_documents'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "mandat__client",
                "dossier",
                "type_document",
                "categorie",
                "valide_par",
                "ecriture_comptable",
                "facture",
            )
            .prefetch_related("historique_versions", "traitements")
        )

    def get_context_data(self, **kwargs):
        from core.models import Client, Mandat

        context = super().get_context_data(**kwargs)
        document = self.object

        # Historique versions
        context["versions"] = document.historique_versions.select_related(
            "modifie_par"
        ).all()

        # Traitements
        context["traitements"] = document.traitements.order_by("-date_debut")[:10]

        # Métadonnées formatées
        context["metadata_display"] = self.format_metadata(document.metadata_extraite)

        # Fil d'Ariane contextuel
        client_id = self.request.GET.get('client')
        mandat_id = self.request.GET.get('mandat')
        parent_id = self.request.GET.get('parent')

        breadcrumb = []
        context['nav_context'] = {}

        if client_id or mandat_id or parent_id:
            # Navigation contextuelle depuis les dossiers
            if client_id:
                try:
                    client = Client.objects.get(id=client_id)
                    breadcrumb.append({
                        'label': client.raison_sociale,
                        'url': f"?client={client_id}",
                        'icon': 'buildings'
                    })
                    context['nav_context']['client'] = client
                except Client.DoesNotExist:
                    pass

            if mandat_id:
                try:
                    mandat = Mandat.objects.select_related('client').get(id=mandat_id)
                    if not client_id:
                        breadcrumb.append({
                            'label': mandat.client.raison_sociale,
                            'url': f"?client={mandat.client_id}",
                            'icon': 'buildings'
                        })
                    breadcrumb.append({
                        'label': mandat.numero,
                        'url': f"?mandat={mandat_id}",
                        'icon': 'briefcase'
                    })
                    context['nav_context']['mandat'] = mandat
                except Mandat.DoesNotExist:
                    pass

            if parent_id:
                try:
                    parent = Dossier.objects.select_related('client', 'mandat__client', 'parent').get(id=parent_id)
                    # Construire l'arborescence des dossiers
                    dossier_path = []
                    current = parent
                    while current:
                        dossier_path.insert(0, current)
                        current = current.parent

                    for dossier in dossier_path:
                        breadcrumb.append({
                            'label': dossier.nom,
                            'url': f"?parent={dossier.id}",
                            'icon': 'folder'
                        })
                    context['nav_context']['parent'] = parent
                except Dossier.DoesNotExist:
                    pass

            context['contextual_breadcrumb'] = breadcrumb
            context['has_context'] = True
        else:
            context['has_context'] = False

        # Relations de ce document (Intelligence AI)
        try:
            from documents.models_intelligence import DocumentRelation
            context['relations'] = DocumentRelation.objects.filter(
                Q(document_source=document) | Q(document_cible=document)
            ).select_related(
                'document_source', 'document_cible'
            ).order_by('-score_similarite')[:5]
        except Exception:
            context['relations'] = []

        return context

    def format_metadata(self, metadata):
        """Formate les métadonnées pour affichage"""
        if not metadata:
            return []

        formatted = []
        for key, value in metadata.items():
            formatted.append(
                {
                    "label": key.replace("_", " ").title(),
                    "value": value,
                }
            )
        return formatted


class DocumentUploadView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Upload d'un document"""

    model = Document
    form_class = DocumentUploadForm
    template_name = "documents/document_upload.html"
    business_permission = 'documents.add_document'

    def get_success_url(self):
        return reverse_lazy("documents:document-detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passer le mandat initial pour le filtrage des dossiers
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            try:
                kwargs['mandat'] = Mandat.objects.get(pk=mandat_id)
            except Mandat.DoesNotExist:
                pass
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        # Pré-sélectionner le mandat si passé en paramètre
        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            initial['mandat'] = mandat_id
        return initial

    def form_valid(self, form):
        from documents.storage import storage_service

        fichier = self.request.FILES["fichier"]

        # Valider le fichier
        validation = storage_service.valider_fichier(
            fichier.name, fichier.size, fichier.content_type
        )
        if not validation['valid']:
            for error in validation['errors']:
                messages.error(self.request, error)
            return self.form_invalid(form)

        # Créer le document
        document = form.save(commit=False)
        document.nom_original = fichier.name
        document.nom_fichier = fichier.name
        document.taille = fichier.size
        document.mime_type = (
            fichier.content_type or mimetypes.guess_type(fichier.name)[0]
        )

        # Extension
        _, ext = os.path.splitext(fichier.name)
        document.extension = ext.lower()

        # Calculer le hash du fichier
        import hashlib
        fichier.seek(0)
        file_content = fichier.read()
        document.hash_fichier = hashlib.sha256(file_content).hexdigest()
        fichier.seek(0)  # Reset pour la sauvegarde

        document.statut_traitement = 'UPLOAD'

        # Sauvegarder d'abord le document (sans le fichier)
        document.save()

        # Puis sauvegarder le fichier via le FileField (utilise DocumentStorage/S3)
        document.fichier.save(fichier.name, fichier, save=True)

        # Le signal post_save lance automatiquement l'OCR si OCR_SERVICE_ENABLED=True
        # (voir documents/signals.py - traiter_document_apres_upload)

        messages.success(self.request, _("Document uploadé avec succès"))
        return super().form_valid(form)


@login_required
def document_telecharger(request, pk):
    """Télécharge un document depuis S3/MinIO ou stockage local via streaming."""
    document = get_object_or_404(Document, pk=pk)

    if not document.fichier:
        messages.error(request, _("Fichier non disponible"))
        return redirect("documents:document-detail", pk=pk)

    try:
        file_obj = document.fichier.open('rb')
        response = FileResponse(
            file_obj,
            content_type=document.mime_type or 'application/octet-stream',
            as_attachment=True,
            filename=document.nom_original,
        )
        if document.taille:
            response['Content-Length'] = document.taille
        return response
    except Exception as e:
        messages.error(request, _("Impossible de télécharger le fichier: %(error)s") % {'error': str(e)})
        return redirect("documents:document-detail", pk=pk)


@login_required
def document_apercu(request, pk):
    """
    Retourne l'aperçu d'un document (inline) via streaming.
    Pour les images et PDF, renvoie le fichier directement sans charger en RAM.
    """
    from django.http import Http404

    document = get_object_or_404(Document, pk=pk)

    if not document.fichier:
        raise Http404("Fichier non disponible")

    try:
        file_obj = document.fichier.open('rb')
        content_type = document.mime_type or mimetypes.guess_type(document.nom_fichier)[0] or 'application/octet-stream'

        response = FileResponse(
            file_obj,
            content_type=content_type,
            as_attachment=False,
        )
        response['Content-Disposition'] = f'inline; filename="{document.nom_original}"'
        if document.taille:
            response['Content-Length'] = document.taille

        # Cache et iframe
        response['Cache-Control'] = 'private, max-age=3600'
        response['X-Frame-Options'] = 'SAMEORIGIN'

        return response
    except Exception as e:
        raise Http404(f"Fichier non trouvé sur le stockage: {e}")


@login_required
def document_valider(request, pk):
    """Valide un document"""
    document = get_object_or_404(Document, pk=pk, statut_validation="EN_ATTENTE")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "valider":
            document.statut_validation = "VALIDE"
            document.statut_traitement = "VALIDE"
            document.valide_par = request.user
            document.date_validation = timezone.now()
            document.commentaire_validation = request.POST.get("commentaire", "")
            document.save()
            messages.success(request, _("Document validé avec succès"))
        elif action == "rejeter":
            document.statut_validation = "REJETE"
            document.valide_par = request.user
            document.date_validation = timezone.now()
            document.commentaire_validation = request.POST.get("commentaire", "")
            document.save()
            messages.warning(request, _("Document rejeté"))

        return redirect("documents:document-detail", pk=pk)

    return render(request, "documents/document_valider.html", {"document": document})


@login_required
def document_ocr(request, pk):
    """Lance ou relance l'OCR sur un document via le service AI"""
    from documents.tasks import traiter_document_ocr
    from documents.ai_service import ai_service

    document = get_object_or_404(Document, pk=pk)

    # Vérifier si le service AI est disponible
    if not ai_service.enabled:
        messages.warning(request, _("Le service AI n'est pas configuré. Vérifiez AI_API_KEY dans .env"))
        return redirect("documents:document-detail", pk=pk)

    # Vérifier que le document n'est pas déjà en traitement
    if document.statut_traitement in ['OCR_EN_COURS', 'CLASSIFICATION_EN_COURS', 'EXTRACTION_EN_COURS']:
        messages.warning(request, _("Le document est déjà en cours de traitement"))
        return redirect("documents:document-detail", pk=pk)

    # Vérifier que le document a un fichier
    if not document.fichier:
        messages.error(request, _("Le document n'a pas de fichier associé"))
        return redirect("documents:document-detail", pk=pk)

    # Lancer le traitement en arrière-plan
    traiter_document_ocr.delay(str(document.id))

    document.statut_traitement = "OCR_EN_COURS"
    document.save(update_fields=['statut_traitement'])

    messages.info(request, _("Traitement OCR lancé en arrière-plan"))
    return redirect("documents:document-detail", pk=pk)


@login_required
def recherche_documents(request):
    """
    Recherche de documents avec support hybride (full-text + sémantique).

    Utilise PGVector pour la recherche sémantique locale.
    """
    from documents.search import search_service
    from django.conf import settings
    import time

    query = request.GET.get("q", "")
    search_type = request.GET.get("type", "hybrid")  # fulltext, semantic, ou hybrid
    mandat_id = request.GET.get("mandat", "")
    error_message = None
    search_results = []
    search_time_ms = 0

    if query:
        start_time = time.time()

        try:
            # Utiliser le service de recherche hybride
            search_results = search_service.search(
                query=query,
                mandat_id=mandat_id if mandat_id else None,
                user=request.user,
                search_type=search_type,
                limit=50,
                semantic_threshold=getattr(settings, 'SEARCH_SEMANTIC_THRESHOLD', 0.5),
                fulltext_weight=getattr(settings, 'SEARCH_FULLTEXT_WEIGHT', 0.4),
                semantic_weight=getattr(settings, 'SEARCH_SEMANTIC_WEIGHT', 0.6),
            )
        except Exception as e:
            error_message = f"Erreur recherche: {str(e)}"
            search_results = []

        search_time_ms = int((time.time() - start_time) * 1000)

    # Mandats pour le filtre
    mandats = Mandat.objects.filter(is_active=True)
    user = request.user
    if not user.is_manager():
        mandats = mandats.filter(
            Q(responsable=user) | Q(equipe=user)
        ).distinct()

    # Statistiques par type de match
    match_stats = {
        'fulltext': sum(1 for r in search_results if r.match_type == 'fulltext'),
        'semantic': sum(1 for r in search_results if r.match_type == 'semantic'),
        'combined': sum(1 for r in search_results if r.match_type == 'combined'),
    }

    return render(
        request,
        "documents/recherche.html",
        {
            "query": query,
            "search_type": search_type,
            "results": search_results,
            "count": len(search_results),
            "search_time_ms": search_time_ms,
            "match_stats": match_stats,
            "mandats": mandats,
            "selected_mandat": mandat_id,
            "error_message": error_message,
            "search_types": [
                ('hybrid', _('Recherche hybride (recommandé)')),
                ('fulltext', _('Recherche textuelle')),
                ('semantic', _('Recherche sémantique')),
            ],
        },
    )


# ============ CATÉGORIES ============


class CategorieDocumentListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des catégories de documents"""

    model = CategorieDocument
    template_name = "documents/categorie_list.html"
    context_object_name = "categories"
    business_permission = 'documents.view_documents'

    def get_queryset(self):
        return CategorieDocument.objects.annotate(nb_types=Count("types_document"))


class CategorieDocumentDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'une catégorie de document"""

    model = CategorieDocument
    template_name = "documents/categorie_detail.html"
    context_object_name = "categorie"
    business_permission = 'documents.view_documents'

    def get_queryset(self):
        return (
            super().get_queryset().prefetch_related("types_document", "sous_categories")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categorie = self.object

        # Statistiques
        context["stats"] = {
            "nb_types": categorie.types_document.count(),
            "nb_sous_categories": categorie.sous_categories.count(),
            "nb_documents": Document.objects.filter(categorie=categorie).count(),
        }

        return context


class CategorieDocumentCreateView(
    LoginRequiredMixin, BusinessPermissionMixin, CreateView
):
    """Création d'une catégorie de document"""

    model = CategorieDocument
    form_class = CategorieDocumentForm
    template_name = "documents/categorie_form.html"
    business_permission = 'documents.view_documents'

    def get_success_url(self):
        return reverse_lazy("documents:categorie-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Catégorie créée avec succès"))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Nouvelle catégorie")
        return context


class CategorieDocumentUpdateView(
    LoginRequiredMixin, BusinessPermissionMixin, UpdateView
):
    """Modification d'une catégorie de document"""

    model = CategorieDocument
    form_class = CategorieDocumentForm
    template_name = "documents/categorie_form.html"
    business_permission = 'documents.view_documents'

    def get_success_url(self):
        return reverse_lazy("documents:categorie-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Catégorie modifiée avec succès"))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Modifier la catégorie")
        context["is_update"] = True
        return context


@login_required
@permission_required_business('documents.add_document')
@require_http_methods(["POST"])
def categorie_document_create_ajax(request):
    """Création d'une catégorie via AJAX (pour modal)"""
    form = CategorieDocumentForm(request.POST)

    if form.is_valid():
        categorie = form.save()
        return JsonResponse(
            {
                "success": True,
                "message": _("Catégorie créée avec succès"),
                "categorie_id": str(categorie.pk),
                "categorie_nom": categorie.nom,
            }
        )
    else:
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )


@login_required
@permission_required_business('documents.add_document')
@require_http_methods(["POST"])
def categorie_document_update_ajax(request, pk):
    """Modification d'une catégorie via AJAX (pour modal)"""
    categorie = get_object_or_404(CategorieDocument, pk=pk)
    form = CategorieDocumentForm(request.POST, instance=categorie)

    if form.is_valid():
        categorie = form.save()
        return JsonResponse(
            {
                "success": True,
                "message": _("Catégorie modifiée avec succès"),
                "categorie_id": str(categorie.pk),
                "categorie_nom": categorie.nom,
            }
        )
    else:
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )


@login_required
@require_http_methods(["GET"])
def categorie_document_get_data(request, pk):
    """Récupérer les données d'une catégorie pour le modal de modification"""
    categorie = get_object_or_404(CategorieDocument, pk=pk)

    return JsonResponse(
        {
            "success": True,
            "data": {
                "pk": str(categorie.pk),
                "nom": categorie.nom,
                "description": categorie.description,
                "mots_cles": categorie.mots_cles,
                "patterns_regex": categorie.patterns_regex,
                "icone": categorie.icone,
                "couleur": categorie.couleur,
                "ordre": categorie.ordre,
                "parent": str(categorie.parent.pk) if categorie.parent else "",
            },
        }
    )



# ============ TYPES ============

class TypeDocumentListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des types de documents"""

    model = TypeDocument
    template_name = "documents/type_list.html"
    context_object_name = "types"
    business_permission = 'documents.view_documents'

    def get_queryset(self):
        return TypeDocument.objects.select_related("categorie").annotate(
            nb_documents=Count("document")
        )



class TypeDocumentDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un type de document avec liste des documents associés"""

    model = TypeDocument
    template_name = "documents/type_detail.html"
    context_object_name = "type_document"
    business_permission = 'documents.view_documents'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("categorie")
            .prefetch_related("validateurs")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        type_doc = self.object

        # Documents de ce type
        documents_qs = Document.objects.filter(
            type_document=type_doc, is_active=True
        ).select_related("mandat__client", "dossier", "valide_par")

        # Appliquer les filtres si présents
        if self.request.GET:
            self.filterset = DocumentFilter(self.request.GET, queryset=documents_qs)
            if self.filterset.is_valid():
                documents_qs = self.filterset.qs

        context["filter"] = DocumentFilter(queryset=documents_qs)
        context["documents"] = documents_qs.order_by("-date_upload")[:50]

        # Statistiques
        context["stats"] = {
            "total": documents_qs.count(),
            "en_attente": documents_qs.filter(statut_validation="EN_ATTENTE").count(),
            "valide": documents_qs.filter(statut_validation="VALIDE").count(),
            "rejete": documents_qs.filter(statut_validation="REJETE").count(),
            "taille_totale": documents_qs.aggregate(Sum("taille"))["taille__sum"] or 0,
        }

        # Répartition par mandat
        context["par_mandat"] = (
            documents_qs.values("mandat__numero", "mandat__client__raison_sociale")
            .annotate(
                nb_docs=Count("id"),
                taille=Sum("taille"),
            )
            .order_by("-nb_docs")[:10]
        )

        # Documents récents
        context["documents_recents"] = documents_qs.order_by("-date_upload")[:5]

        return context
    


class TypeDocumentCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un type de document"""

    model = TypeDocument
    form_class = TypeDocumentForm
    template_name = "documents/type_form.html"
    business_permission = 'documents.view_documents'

    def get_success_url(self):
        return reverse_lazy("documents:type-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Type de document créé avec succès"))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Nouveau type de document")
        return context
    

class TypeDocumentUpdateView(LoginRequiredMixin, BusinessPermissionMixin, UpdateView):
    """Modification d'un type de document"""

    model = TypeDocument
    form_class = TypeDocumentForm
    template_name = "documents/type_form.html"
    business_permission = 'documents.view_documents'

    def get_success_url(self):
        return reverse_lazy("documents:type-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Type de document modifié avec succès"))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Modifier le type de document")
        context["is_update"] = True
        return context


@login_required
@permission_required_business('documents.add_document')
@require_http_methods(["POST"])
def type_document_update_ajax(request, pk):
    """Modification d'un type de document via AJAX (pour modal)"""
    type_doc = get_object_or_404(TypeDocument, pk=pk)
    form = TypeDocumentForm(request.POST, instance=type_doc)

    if form.is_valid():
        type_doc = form.save()
        return JsonResponse(
            {
                "success": True,
                "message": _("Type de document modifié avec succès"),
                "type_id": str(type_doc.pk),
                "type_code": type_doc.code,
                "type_libelle": type_doc.libelle,
            }
        )
    else:
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )


@login_required
@require_http_methods(["GET"])
def type_document_get_data(request, pk):
    """Récupérer les données d'un type pour le modal de modification"""
    type_doc = get_object_or_404(TypeDocument, pk=pk)

    return JsonResponse(
        {
            "success": True,
            "data": {
                "pk": str(type_doc.pk),
                "code": type_doc.code,
                "libelle": type_doc.libelle,
                "type_document": type_doc.type_document,
                "categorie": str(type_doc.categorie.pk),
                "champs_extraire": type_doc.champs_extraire,
                "validation_requise": type_doc.validation_requise,
                "validateurs": [str(v.pk) for v in type_doc.validateurs.all()],
            },
        }
    )


@login_required
@permission_required_business('documents.add_document')
@require_http_methods(["POST"])
def type_document_create_ajax(request):
    """Création d'un type de document via AJAX (pour modal)"""
    form = TypeDocumentForm(request.POST)

    if form.is_valid():
        type_doc = form.save()
        return JsonResponse(
            {
                "success": True,
                "message": _("Type de document créé avec succès"),
                "type_id": str(type_doc.pk),
                "type_code": type_doc.code,
                "type_libelle": type_doc.libelle,
            }
        )
    else:
        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )


# ============ API AJAX POUR FILTRAGE DYNAMIQUE ============

@login_required
def api_dossiers_par_mandat(request, mandat_pk):
    """
    Retourne les dossiers d'un mandat (API AJAX).

    Retourne TOUS les dossiers accessibles pour ce mandat:
    - Dossiers directement liés au mandat
    - Dossiers liés au client du mandat

    Si mandat_pk est vide ou None, retourne tous les dossiers actifs
    avec une indication du mandat/client pour chaque dossier.
    """
    mandat = get_object_or_404(Mandat, pk=mandat_pk)

    # Dossiers liés au mandat OU au client du mandat
    dossiers = Dossier.objects.filter(
        Q(mandat=mandat) | Q(client=mandat.client),
        is_active=True
    ).select_related('parent', 'mandat', 'mandat__client', 'client').order_by('chemin_complet')

    return JsonResponse({
        'success': True,
        'dossiers': [
            {
                'id': str(d.id),
                'nom': d.nom,
                'chemin': d.chemin_complet or d.nom,
                # Affichage avec contexte pour éviter confusion entre dossiers homonymes
                'display': d.get_path_display(include_context=True),
                'mandat_id': str(d.mandat_id) if d.mandat_id else None,
                'client_id': str(d.client_id) if d.client_id else None,
            }
            for d in dossiers
        ]
    })


@login_required
def api_tous_dossiers(request):
    """
    Retourne tous les dossiers actifs avec indication du mandat.

    Utilisé quand le mandat n'est pas obligatoire mais qu'on veut
    afficher le contexte (mandat/client) pour éviter la confusion
    entre dossiers homonymes.
    """
    dossiers = Dossier.objects.filter(
        is_active=True
    ).select_related('parent', 'mandat', 'mandat__client', 'client').order_by('chemin_complet')

    result = []
    for d in dossiers:
        # Construire un affichage avec contexte
        contexte = ""
        if d.mandat:
            contexte = f" [{d.mandat.numero}]"
        elif d.client:
            contexte = f" [{d.client.nom}]"

        result.append({
            'id': str(d.id),
            'nom': d.nom,
            'chemin': d.chemin_complet or d.nom,
            'display': f"{d.get_path_display()}{contexte}",
            'mandat_id': str(d.mandat_id) if d.mandat_id else None,
            'client_id': str(d.client_id) if d.client_id else None,
        })

    return JsonResponse({
        'success': True,
        'dossiers': result
    })


# ============ AI FEATURES (Résumé, Q&A, Documents similaires) ============

@login_required
@require_http_methods(["GET", "POST"])
def document_summarize(request, pk):
    """
    Génère un résumé du document via le service AI.

    GET: Affiche la page de résumé
    POST: Génère le résumé (AJAX)
    """
    from documents.ai_service import ai_service

    document = get_object_or_404(Document, pk=pk)

    # Vérifier que le service AI est disponible
    if not ai_service.enabled:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(_("Le service AI n'est pas configuré"))
            })
        messages.warning(request, _("Le service AI n'est pas configuré"))
        return redirect("documents:document-detail", pk=pk)

    # Vérifier que le document a du texte
    if not document.ocr_text:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(_("Le document n'a pas de texte extrait. Lancez l'OCR d'abord."))
            })
        messages.warning(request, _("Le document n'a pas de texte extrait. Lancez l'OCR d'abord."))
        return redirect("documents:document-detail", pk=pk)

    if request.method == 'POST':
        # Générer le résumé
        max_length = request.POST.get('max_length', 'medium')

        try:
            result = ai_service.summarize_document(
                text=document.ocr_text,
                max_length=max_length,
                language='fr'
            )

            return JsonResponse({
                'success': True,
                'summary': result.get('summary', ''),
                'key_points': result.get('key_points', []),
                'entities': result.get('entities', {}),
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    # GET: Afficher la page
    return render(request, "documents/document_summarize.html", {
        'document': document,
    })


@login_required
@require_http_methods(["GET", "POST"])
def document_ask(request, pk):
    """
    Q&A sur un document spécifique (RAG-like).

    GET: Affiche l'interface de Q&A
    POST: Répond à une question (AJAX)
    """
    from documents.ai_service import ai_service

    document = get_object_or_404(Document, pk=pk)

    # Vérifier que le service AI est disponible
    if not ai_service.enabled:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(_("Le service AI n'est pas configuré"))
            })
        messages.warning(request, _("Le service AI n'est pas configuré"))
        return redirect("documents:document-detail", pk=pk)

    # Vérifier que le document a du texte
    if not document.ocr_text:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(_("Le document n'a pas de texte extrait"))
            })
        messages.warning(request, _("Le document n'a pas de texte extrait"))
        return redirect("documents:document-detail", pk=pk)

    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

        question = data.get('question', '').strip()
        history = data.get('history', [])

        if not question:
            return JsonResponse({
                'success': False,
                'error': str(_("Veuillez poser une question"))
            })

        try:
            result = ai_service.ask_document(
                text=document.ocr_text,
                question=question,
                history=history,
                language='fr'
            )

            return JsonResponse({
                'success': True,
                'answer': result.get('answer', ''),
                'confidence': result.get('confidence', 0),
                'sources': result.get('sources', []),
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    # GET: Afficher l'interface
    return render(request, "documents/document_ask.html", {
        'document': document,
    })


@login_required
def document_similar(request, pk):
    """
    Trouve les documents similaires via recherche sémantique.
    """
    from documents.search import search_service
    from documents.models import DocumentEmbedding
    from documents.embeddings import embedding_service

    document = get_object_or_404(Document, pk=pk)

    similar_documents = []
    error_message = None

    try:
        # Vérifier si le document a un embedding
        embedding_obj = DocumentEmbedding.objects.filter(document=document).first()

        if not embedding_obj:
            # Essayer de générer l'embedding
            text = document.ocr_text or document.description or document.nom_fichier
            if text:
                search_service.index_document(document)
                embedding_obj = DocumentEmbedding.objects.filter(document=document).first()

        if embedding_obj and embedding_obj.embedding is not None:
            # Rechercher les documents similaires
            similar = DocumentEmbedding.search_similar(
                query_embedding=embedding_obj.embedding,
                limit=11,  # +1 car le document lui-même sera inclus
                threshold=0.3,
                mandat_id=None  # Chercher dans tous les mandats
            )

            for s in similar:
                if str(s.document.id) != str(document.id):  # Exclure le document actuel
                    similarity = 1 - s.distance
                    similar_documents.append({
                        'document': s.document,
                        'similarity': similarity,
                        'similarity_percent': int(similarity * 100),
                    })

            similar_documents = similar_documents[:10]  # Limiter à 10

    except Exception as e:
        error_message = str(e)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': error_message is None,
            'error': error_message,
            'similar': [
                {
                    'id': str(s['document'].id),
                    'nom_fichier': s['document'].nom_fichier,
                    'similarity': s['similarity'],
                    'similarity_percent': s['similarity_percent'],
                    'type': s['document'].prediction_type or 'Inconnu',
                    'mandat': s['document'].mandat.numero if s['document'].mandat else '',
                }
                for s in similar_documents
            ]
        })

    return render(request, "documents/document_similar.html", {
        'document': document,
        'similar_documents': similar_documents,
        'error_message': error_message,
    })


# ============ INTELLIGENCE AI ============


@login_required
@require_http_methods(["POST"])
def mandat_analyser(request, mandat_pk):
    """Déclenche l'analyse AI complète d'un mandat."""
    from documents.tasks_intelligence import analyser_mandat_complet

    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    analyser_mandat_complet.delay(str(mandat.id))
    return JsonResponse({'success': True, 'message': 'Analyse lancée'})


@login_required
@require_http_methods(["POST"])
def insight_traiter(request, pk):
    """Marquer un insight comme traité."""
    from documents.models_intelligence import MandatInsight

    insight = get_object_or_404(MandatInsight, pk=pk)
    insight.traite = True
    insight.save(update_fields=['traite'])
    return JsonResponse({'success': True})


@login_required
def mandat_insights(request, mandat_pk):
    """Liste complète des insights d'un mandat."""
    from documents.models_intelligence import MandatInsight

    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    insights = MandatInsight.objects.filter(mandat=mandat).order_by('-created_at')
    return render(request, 'documents/mandat_insights.html', {
        'mandat': mandat, 'insights': insights
    })


@login_required
def mandat_digests(request, mandat_pk):
    """Liste des digests d'un mandat."""
    from documents.models_intelligence import MandatDigest

    mandat = get_object_or_404(Mandat, pk=mandat_pk)
    digests = MandatDigest.objects.filter(mandat=mandat).order_by('-periode_fin')
    return render(request, 'documents/mandat_digests.html', {
        'mandat': mandat, 'digests': digests
    })