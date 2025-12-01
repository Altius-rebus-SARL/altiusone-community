# documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
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


class DossierListView(LoginRequiredMixin, ListView):
    """Liste des dossiers"""

    model = Dossier
    template_name = "documents/dossier_list.html"
    context_object_name = "dossiers"
    paginate_by = 50

    def get_queryset(self):
        queryset = Dossier.objects.select_related(
            "parent", "client", "mandat", "proprietaire"
        ).annotate(nb_documents=Count("documents"))

        # Filtrer selon le rôle
        user = self.request.user
        if user.role not in ["ADMIN", "MANAGER"]:
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


class DossierDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un dossier"""

    model = Dossier
    template_name = "documents/dossier_detail.html"
    context_object_name = "dossier"

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


class DossierCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Création d'un dossier"""

    model = Dossier
    form_class = DossierForm
    template_name = "documents/dossier_form.html"
    permission_required = "documents.add_dossier"

    def get_success_url(self):
        return reverse_lazy("documents:dossier-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        form.instance.proprietaire = self.request.user
        messages.success(self.request, _("Dossier créé avec succès"))
        return super().form_valid(form)


# ============ DOCUMENTS ============


class DocumentListView(LoginRequiredMixin, ListView):
    """Liste des documents"""

    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"
    paginate_by = 50

    def get_queryset(self):
        queryset = Document.objects.select_related(
            "mandat__client", "dossier", "type_document", "categorie", "valide_par"
        ).filter(is_active=True)

        # Filtrer selon le rôle
        user = self.request.user
        if user.role not in ["ADMIN", "MANAGER"]:
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


class DocumentDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un document"""

    model = Document
    template_name = "documents/document_detail.html"
    context_object_name = "document"

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


class DocumentUploadView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Upload d'un document"""

    model = Document
    form_class = DocumentUploadForm
    template_name = "documents/document_upload.html"
    permission_required = "documents.add_document"

    def get_success_url(self):
        return reverse_lazy("documents:document-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        fichier = self.request.FILES["fichier"]

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

        # Hash
        import hashlib

        hash_md5 = hashlib.sha256()
        for chunk in fichier.chunks():
            hash_md5.update(chunk)
        document.hash_fichier = hash_md5.hexdigest()

        # Path storage (à adapter selon ton système de stockage)
        document.path_storage = document.generer_path_storage()

        document.save()

        # TODO: Sauvegarder le fichier sur S3/Minio
        # TODO: Déclencher OCR/AI si nécessaire

        messages.success(self.request, _("Document uploadé avec succès"))
        return super().form_valid(form)


@login_required
def document_telecharger(request, pk):
    """Télécharge un document"""
    document = get_object_or_404(Document, pk=pk)

    # TODO: Récupérer le fichier depuis S3/Minio
    # Pour l'instant, retourner une réponse vide
    messages.info(request, _("Téléchargement en cours..."))
    return redirect("documents:document-detail", pk=pk)


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
    """Lance l'OCR sur un document"""
    document = get_object_or_404(Document, pk=pk)

    # TODO: Lancer le traitement OCR
    document.statut_traitement = "OCR_EN_COURS"
    document.save()

    messages.info(request, _("Traitement OCR lancé"))
    return redirect("documents:document-detail", pk=pk)


@login_required
def recherche_documents(request):
    """Recherche de documents"""
    query = request.GET.get("q", "")
    results = []

    if query:
        results = (
            Document.objects.filter(
                Q(nom_fichier__icontains=query)
                | Q(ocr_text__icontains=query)
                | Q(description__icontains=query)
            )
            .select_related("mandat__client", "type_document")
            .order_by("-date_upload")[:50]
        )

    return render(
        request,
        "documents/recherche.html",
        {"query": query, "results": results, "count": len(results)},
    )


# ============ CATÉGORIES ============


class CategorieDocumentListView(LoginRequiredMixin, ListView):
    """Liste des catégories de documents"""

    model = CategorieDocument
    template_name = "documents/categorie_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return CategorieDocument.objects.annotate(nb_types=Count("types_document"))


class CategorieDocumentDetailView(LoginRequiredMixin, DetailView):
    """Détail d'une catégorie de document"""

    model = CategorieDocument
    template_name = "documents/categorie_detail.html"
    context_object_name = "categorie"

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
    LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    """Création d'une catégorie de document"""

    model = CategorieDocument
    form_class = CategorieDocumentForm
    template_name = "documents/categorie_form.html"
    permission_required = "documents.add_categoriedocument"

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
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    """Modification d'une catégorie de document"""

    model = CategorieDocument
    form_class = CategorieDocumentForm
    template_name = "documents/categorie_form.html"
    permission_required = "documents.change_categoriedocument"

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

class TypeDocumentListView(LoginRequiredMixin, ListView):
    """Liste des types de documents"""

    model = TypeDocument
    template_name = "documents/type_list.html"
    context_object_name = "types"

    def get_queryset(self):
        return TypeDocument.objects.select_related("categorie").annotate(
            nb_documents=Count("document")
        )



class TypeDocumentDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un type de document avec liste des documents associés"""

    model = TypeDocument
    template_name = "documents/type_detail.html"
    context_object_name = "type_document"

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
    


class TypeDocumentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Création d'un type de document"""

    model = TypeDocument
    form_class = TypeDocumentForm
    template_name = "documents/type_form.html"
    permission_required = "documents.add_typedocument"

    def get_success_url(self):
        return reverse_lazy("documents:type-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, _("Type de document créé avec succès"))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Nouveau type de document")
        return context
    

class TypeDocumentUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modification d'un type de document"""

    model = TypeDocument
    form_class = TypeDocumentForm
    template_name = "documents/type_form.html"
    permission_required = "documents.change_typedocument"

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