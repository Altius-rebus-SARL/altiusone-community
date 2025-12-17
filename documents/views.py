# documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
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
)
from .forms import DocumentForm, DocumentUploadForm, DossierForm, TypeDocumentForm, CategorieDocumentForm
from .filters import DocumentFilter, DossierFilter
from core.models import Mandat


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
        context["stats"] = {
            "total": full_queryset.count(),
            "total_documents": full_queryset.aggregate(Sum("nombre_documents"))[
                "nombre_documents__sum"
            ]
            or 0,
            "total_taille": full_queryset.aggregate(Sum("taille_totale"))[
                "taille_totale__sum"
            ]
            or 0,
        }

        return context


class DossierDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Détail d'un dossier"""

    model = Dossier
    template_name = "documents/dossier_detail.html"
    context_object_name = "dossier"
    business_permission = 'documents.view_documents'

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("parent", "client", "mandat", "proprietaire")
            .prefetch_related("sous_dossiers", "documents")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dossier = self.object

        # Documents du dossier
        context["documents"] = dossier.documents.select_related(
            "type_document", "categorie"
        ).order_by("-date_upload")[:20]

        # Sous-dossiers
        context["sous_dossiers"] = dossier.sous_dossiers.all()

        # Arborescence (breadcrumb)
        context["arborescence"] = self.get_arborescence(dossier)

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

        # Upload vers le stockage (GCS ou local)
        upload_result = storage_service.upload_fichier(
            file_obj=fichier,
            filename=fichier.name,
            mandat_id=str(document.mandat_id)
        )

        if not upload_result['success']:
            for error in upload_result.get('errors', ['Erreur upload']):
                messages.error(self.request, error)
            return self.form_invalid(form)

        document.path_storage = upload_result['path']
        document.hash_fichier = upload_result['hash']
        document.statut_traitement = 'UPLOAD'

        document.save()

        # Lancer le traitement OCR en arrière-plan si activé
        if getattr(settings, 'OCR_SERVICE_ENABLED', False):
            traiter_document_ocr.delay(str(document.id))
            messages.info(self.request, _("Traitement OCR lancé en arrière-plan"))

        messages.success(self.request, _("Document uploadé avec succès"))
        return super().form_valid(form)


@login_required
def document_telecharger(request, pk):
    """Télécharge un document depuis GCS ou stockage local"""
    from documents.storage import storage_service

    document = get_object_or_404(Document, pk=pk)

    # Récupérer le fichier depuis le stockage
    content = storage_service.telecharger_fichier(document.path_storage)

    if content is None:
        messages.error(request, _("Impossible de télécharger le fichier"))
        return redirect("documents:document-detail", pk=pk)

    # Créer la réponse avec le contenu du fichier
    response = HttpResponse(content, content_type=document.mime_type)
    response['Content-Disposition'] = f'attachment; filename="{document.nom_original}"'
    response['Content-Length'] = len(content)

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
    """Lance l'OCR sur un document via le service externe"""
    from documents.tasks import traiter_document_ocr
    from django.conf import settings

    document = get_object_or_404(Document, pk=pk)

    # Vérifier si le service OCR est disponible
    if not getattr(settings, 'OCR_SERVICE_ENABLED', False):
        messages.warning(request, _("Le service OCR n'est pas activé"))
        return redirect("documents:document-detail", pk=pk)

    # Vérifier que le document n'est pas déjà en traitement
    if document.statut_traitement in ['OCR_EN_COURS', 'CLASSIFICATION_EN_COURS', 'EXTRACTION_EN_COURS']:
        messages.warning(request, _("Le document est déjà en cours de traitement"))
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