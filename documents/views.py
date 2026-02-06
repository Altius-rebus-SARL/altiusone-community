# documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from core.permissions import BusinessPermissionMixin, permission_required_business
from django.db.models import Q, Count, Sum
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils.translation import gettext_lazy as _
from datetime import datetime
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
        ).select_related('mandat', 'document').order_by('-updated_at')[:20]

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

        return context


# ============ DOSSIERS ============


class DossierListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des dossiers"""

    model = Dossier
    template_name = "documents/dossier_list.html"
    context_object_name = "dossiers"
    paginate_by = 50
    business_permission = 'documents.view_documents'

    def get_queryset(self):
        queryset = Dossier.objects.select_related(
            "parent", "client", "mandat", "proprietaire"
        ).annotate(nb_documents=Count("documents"))

        # Filtrer selon le rôle
        user = self.request.user
        if not user.is_manager():
            queryset = queryset.filter(
                Q(mandat__responsable=user)
                | Q(mandat__equipe=user)
                | Q(proprietaire=user)
            ).distinct()

        # Appliquer les filtres
        if self.request.GET:
            self.filterset = DossierFilter(self.request.GET, queryset=queryset)
            if self.filterset.is_valid():
                return self.filterset.qs.order_by("chemin_complet")

        self.filterset = DossierFilter(queryset=queryset)
        return queryset.order_by("chemin_complet")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filterset

        full_queryset = self.get_queryset()

        # Calculer les statistiques depuis les documents réels
        dossier_ids = list(full_queryset.values_list('id', flat=True))
        doc_stats = Document.objects.filter(
            dossier_id__in=dossier_ids,
            is_active=True
        ).aggregate(
            total_docs=Count('id'),
            total_size=Sum('taille')
        )

        context["stats"] = {
            "total": full_queryset.count(),
            "total_documents": doc_stats['total_docs'] or 0,
            "total_taille": doc_stats['total_size'] or 0,
        }

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


class DocumentListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des documents"""

    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"
    paginate_by = 50
    business_permission = 'documents.view_documents'

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
                return self.filterset.qs.order_by("-date_upload")

        self.filterset = DocumentFilter(queryset=queryset)
        return queryset.order_by("-date_upload")

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
            .prefetch_related("versions", "traitements")
        )

    def get_context_data(self, **kwargs):
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
        from documents.tasks import traiter_document_ocr
        from django.conf import settings

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

        # Lancer le traitement OCR en arrière-plan si activé
        if getattr(settings, 'OCR_SERVICE_ENABLED', False):
            traiter_document_ocr.delay(str(document.id))
            messages.info(self.request, _("Traitement OCR lancé en arrière-plan"))

        messages.success(self.request, _("Document uploadé avec succès"))
        return super().form_valid(form)


@login_required
def document_telecharger(request, pk):
    """Télécharge un document depuis S3/MinIO ou stockage local"""
    document = get_object_or_404(Document, pk=pk)

    # Vérifier que le fichier existe
    if not document.fichier:
        messages.error(request, _("Fichier non disponible"))
        return redirect("documents:document-detail", pk=pk)

    try:
        # Lire le contenu du fichier via le FileField
        document.fichier.open('rb')
        content = document.fichier.read()
        document.fichier.close()
    except Exception as e:
        messages.error(request, _("Impossible de télécharger le fichier: %(error)s") % {'error': str(e)})
        return redirect("documents:document-detail", pk=pk)

    # Créer la réponse avec le contenu du fichier
    response = HttpResponse(content, content_type=document.mime_type)
    response['Content-Disposition'] = f'attachment; filename="{document.nom_original}"'
    response['Content-Length'] = len(content)

    return response


@login_required
def document_apercu(request, pk):
    """
    Retourne l'aperçu d'un document (inline).
    Pour les images et PDF, renvoie le fichier directement.
    """
    from django.http import Http404

    document = get_object_or_404(Document, pk=pk)

    # Vérifier que le fichier existe
    if not document.fichier:
        raise Http404("Fichier non disponible")

    try:
        # Lire le contenu du fichier via le FileField
        document.fichier.open('rb')
        content = document.fichier.read()
        document.fichier.close()
    except Exception as e:
        raise Http404(f"Fichier non trouvé sur le stockage: {e}")

    # Déterminer le Content-Type
    content_type = document.mime_type or mimetypes.guess_type(document.nom_fichier)[0] or 'application/octet-stream'

    # Créer la réponse avec le contenu du fichier
    response = HttpResponse(content, content_type=content_type)
    # Content-Disposition: inline pour afficher dans le navigateur
    response['Content-Disposition'] = f'inline; filename="{document.nom_original}"'
    response['Content-Length'] = len(content)

    # Cache headers pour les aperçus
    response['Cache-Control'] = 'private, max-age=3600'

    # Permettre l'affichage dans iframe (pour PDF)
    response['X-Frame-Options'] = 'SAMEORIGIN'

    return response


@login_required
def document_valider(request, pk):
    """Valide un document"""
    document = get_object_or_404(Document, pk=pk, statut_validation="EN_ATTENTE")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "valider":
            document.statut_validation = "VALIDE"
            document.valide_par = request.user
            document.date_validation = datetime.now()
            document.commentaire_validation = request.POST.get("commentaire", "")
            document.save()
            messages.success(request, _("Document validé avec succès"))
        elif action == "rejeter":
            document.statut_validation = "REJETE"
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