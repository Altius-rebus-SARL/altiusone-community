"""
Vues pour l'application Éditeur Collaboratif.

Interface utilisateur pour la gestion des documents collaboratifs
et l'intégration avec Docs (La Suite Numérique).
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from core.permissions import BusinessPermissionMixin
from .models import (
    DocumentCollaboratif,
    PartageDocument,
    LienPartagePublic,
    SessionEdition,
    VersionExportee,
    ModeleDocument
)
from .forms import (
    DocumentCollaboratifForm,
    PartageDocumentForm,
    LienPartagePublicForm,
    ModeleDocumentForm
)
from .docs_service import docs_service, DocsServiceError

logger = logging.getLogger(__name__)


# =============================================================================
# Dashboard et liste des documents
# =============================================================================

class EditeurDashboardView(LoginRequiredMixin, BusinessPermissionMixin, TemplateView):
    """
    Dashboard principal de l'éditeur collaboratif.

    Affiche les documents récents, partagés et les modèles disponibles.
    """
    template_name = 'editeur/dashboard.html'
    permission_required = 'editeur.view_documentcollaboratif'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Documents récents de l'utilisateur
        context['documents_recents'] = DocumentCollaboratif.objects.filter(
            Q(createur=user) | Q(partages__utilisateur=user)
        ).distinct().order_by('-date_modification')[:10]

        # Documents partagés avec l'utilisateur
        context['documents_partages'] = DocumentCollaboratif.objects.filter(
            partages__utilisateur=user
        ).exclude(createur=user).order_by('-date_modification')[:10]

        # Modèles disponibles
        context['modeles'] = ModeleDocument.objects.filter(
            Q(est_public=True) | Q(cree_par=user)
        ).order_by('-nombre_utilisations')[:6]

        # Sessions actives
        context['sessions_actives'] = SessionEdition.objects.filter(
            document__createur=user,
            est_active=True
        ).select_related('utilisateur', 'document')[:5]

        # État du service Docs
        context['docs_status'] = docs_service.health_check()

        return context


class DocumentListView(LoginRequiredMixin, BusinessPermissionMixin, ListView):
    """Liste des documents collaboratifs."""
    model = DocumentCollaboratif
    template_name = 'editeur/document_list.html'
    context_object_name = 'documents'
    permission_required = 'editeur.view_documentcollaboratif'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        queryset = DocumentCollaboratif.objects.filter(
            Q(createur=user) |
            Q(partages__utilisateur=user) |
            Q(est_public=True, mandat__in=user.mandats_accessibles)
        ).distinct()

        # Filtres
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)

        type_doc = self.request.GET.get('type')
        if type_doc:
            queryset = queryset.filter(type_document=type_doc)

        mandat_id = self.request.GET.get('mandat')
        if mandat_id:
            queryset = queryset.filter(mandat_id=mandat_id)

        # Recherche
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(titre__icontains=q) | Q(description__icontains=q)
            )

        return queryset.order_by('-date_modification')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['statuts'] = DocumentCollaboratif.Statut.choices
        context['types'] = DocumentCollaboratif.TypeDocument.choices
        context['filtres_actifs'] = {
            'statut': self.request.GET.get('statut'),
            'type': self.request.GET.get('type'),
            'mandat': self.request.GET.get('mandat'),
            'q': self.request.GET.get('q'),
        }
        return context


# =============================================================================
# Création et édition de documents
# =============================================================================

class DocumentCreateView(LoginRequiredMixin, BusinessPermissionMixin, CreateView):
    """Création d'un nouveau document collaboratif."""
    model = DocumentCollaboratif
    form_class = DocumentCollaboratifForm
    template_name = 'editeur/document_form.html'
    permission_required = 'editeur.add_documentcollaboratif'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        document = form.save(commit=False)
        document.createur = user

        try:
            # Créer le document dans Docs
            modele_id = self.request.POST.get('modele')
            modele = None
            content = None

            if modele_id:
                modele = ModeleDocument.objects.get(id=modele_id)
                content = modele.contenu_json
                modele.incrementer_utilisation()

            docs_doc = docs_service.create_document(
                title=document.titre,
                user=user,
                content=content
            )

            document.docs_id = docs_doc.id
            document.save()

            messages.success(
                self.request,
                _("Document '%(titre)s' créé avec succès.") % {'titre': document.titre}
            )

            # Rediriger vers l'éditeur
            return redirect('editeur:document_edit', pk=document.pk)

        except DocsServiceError as e:
            logger.error(f"Erreur création document Docs: {e}")
            messages.error(
                self.request,
                _("Erreur lors de la création du document: %(error)s") % {'error': str(e)}
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modeles'] = ModeleDocument.objects.filter(
            Q(est_public=True) | Q(cree_par=self.request.user)
        ).order_by('categorie', 'nom')
        return context


class DocumentEditView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """
    Vue d'édition d'un document collaboratif.

    Affiche l'éditeur Docs en iframe avec authentification SSO.
    """
    model = DocumentCollaboratif
    template_name = 'editeur/document_edit.html'
    context_object_name = 'document'
    permission_required = 'editeur.change_documentcollaboratif'

    def get_queryset(self):
        user = self.request.user
        return DocumentCollaboratif.objects.filter(
            Q(createur=user) |
            Q(partages__utilisateur=user, partages__niveau_acces__in=['EDITION', 'ADMIN'])
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object
        user = self.request.user

        try:
            # Générer le token d'édition
            token = docs_service.generate_edit_token(user, document.docs_id)
            context['editor_url'] = docs_service.get_embed_url(
                document.docs_id,
                token,
                readonly=False
            )
            context['docs_available'] = True
        except DocsServiceError as e:
            logger.error(f"Erreur génération token: {e}")
            context['docs_available'] = False
            context['docs_error'] = str(e)

        # Collaborateurs actuels
        context['collaborateurs'] = document.partages.select_related('utilisateur')

        # Sessions actives sur ce document
        context['sessions'] = SessionEdition.objects.filter(
            document=document,
            est_active=True
        ).select_related('utilisateur')

        return context


class DocumentDetailView(LoginRequiredMixin, BusinessPermissionMixin, DetailView):
    """Vue détaillée d'un document (lecture seule)."""
    model = DocumentCollaboratif
    template_name = 'editeur/document_detail.html'
    context_object_name = 'document'
    permission_required = 'editeur.view_documentcollaboratif'

    def get_queryset(self):
        user = self.request.user
        return DocumentCollaboratif.objects.filter(
            Q(createur=user) |
            Q(partages__utilisateur=user) |
            Q(est_public=True, mandat__in=user.mandats_accessibles)
        ).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object
        user = self.request.user

        # Déterminer les permissions de l'utilisateur
        is_owner = document.createur == user
        partage = document.partages.filter(utilisateur=user).first()

        context['can_edit'] = is_owner or (partage and partage.peut_editer)
        context['can_share'] = is_owner or (partage and partage.niveau_acces == 'ADMIN')

        # Versions exportées
        context['exports'] = document.versions_exportees.order_by('-date_export')[:5]

        # Historique des partages
        context['partages'] = document.partages.select_related('utilisateur', 'partage_par')

        try:
            # URL de visualisation
            token = docs_service.generate_readonly_token(document.docs_id)
            context['preview_url'] = docs_service.get_embed_url(
                document.docs_id,
                token,
                readonly=True
            )
            context['docs_available'] = True
        except DocsServiceError:
            context['docs_available'] = False

        return context


class DocumentDeleteView(LoginRequiredMixin, BusinessPermissionMixin, DeleteView):
    """Suppression d'un document collaboratif."""
    model = DocumentCollaboratif
    template_name = 'editeur/document_confirm_delete.html'
    success_url = reverse_lazy('editeur:document_list')
    permission_required = 'editeur.delete_documentcollaboratif'

    def get_queryset(self):
        # Seul le créateur peut supprimer
        return DocumentCollaboratif.objects.filter(createur=self.request.user)

    def delete(self, request, *args, **kwargs):
        document = self.get_object()

        try:
            # Supprimer dans Docs
            docs_service.delete_document(document.docs_id)
        except DocsServiceError as e:
            logger.warning(f"Erreur suppression Docs (document local supprimé quand même): {e}")

        messages.success(request, _("Document supprimé avec succès."))
        return super().delete(request, *args, **kwargs)


# =============================================================================
# Partage de documents
# =============================================================================

class PartageCreateView(LoginRequiredMixin, View):
    """Partage d'un document avec un utilisateur."""

    def post(self, request, pk):
        document = get_object_or_404(
            DocumentCollaboratif,
            pk=pk,
            createur=request.user
        )

        form = PartageDocumentForm(request.POST, document=document)
        if form.is_valid():
            partage = form.save(commit=False)
            partage.document = document
            partage.partage_par = request.user

            try:
                # Ajouter le collaborateur dans Docs
                permission_map = {
                    'LECTURE': 'view',
                    'COMMENTAIRE': 'comment',
                    'EDITION': 'edit',
                    'ADMIN': 'admin'
                }
                docs_service.add_collaborator(
                    document.docs_id,
                    partage.utilisateur,
                    permission_map.get(partage.niveau_acces, 'view')
                )

                partage.save()
                document.nombre_collaborateurs = document.partages.count() + 1
                document.save(update_fields=['nombre_collaborateurs'])

                messages.success(
                    request,
                    _("Document partagé avec %(user)s.") % {'user': partage.utilisateur}
                )
            except DocsServiceError as e:
                messages.error(request, _("Erreur de partage: %(error)s") % {'error': str(e)})

        return redirect('editeur:document_detail', pk=pk)


class PartageDeleteView(LoginRequiredMixin, View):
    """Retrait du partage d'un document."""

    def post(self, request, pk, partage_pk):
        document = get_object_or_404(
            DocumentCollaboratif,
            pk=pk,
            createur=request.user
        )
        partage = get_object_or_404(PartageDocument, pk=partage_pk, document=document)

        try:
            docs_service.remove_collaborator(document.docs_id, partage.utilisateur)
        except DocsServiceError as e:
            logger.warning(f"Erreur retrait collaborateur Docs: {e}")

        partage.delete()
        document.nombre_collaborateurs = document.partages.count() + 1
        document.save(update_fields=['nombre_collaborateurs'])

        messages.success(request, _("Partage retiré."))
        return redirect('editeur:document_detail', pk=pk)


# =============================================================================
# Liens publics
# =============================================================================

class LienPublicCreateView(LoginRequiredMixin, View):
    """Création d'un lien de partage public."""

    def post(self, request, pk):
        document = get_object_or_404(
            DocumentCollaboratif,
            pk=pk,
            createur=request.user
        )

        form = LienPartagePublicForm(request.POST)
        if form.is_valid():
            lien = form.save(commit=False)
            lien.document = document
            lien.cree_par = request.user
            lien.save()

            messages.success(
                request,
                _("Lien public créé: %(url)s") % {'url': lien.url_complet}
            )
        else:
            messages.error(request, _("Erreur lors de la création du lien."))

        return redirect('editeur:document_detail', pk=pk)


class LienPublicView(View):
    """Accès à un document via lien public."""

    def get(self, request, token):
        lien = get_object_or_404(LienPartagePublic, token=token)

        if not lien.est_valide:
            raise Http404(_("Ce lien n'est plus valide."))

        # Vérifier le mot de passe si nécessaire
        if lien.mot_de_passe_hash:
            if not request.session.get(f'lien_auth_{token}'):
                return render(request, 'editeur/lien_password.html', {'token': token})

        lien.incrementer_acces()

        try:
            readonly = not lien.permet_edition
            token_docs = docs_service.generate_readonly_token(lien.document.docs_id)
            editor_url = docs_service.get_embed_url(
                lien.document.docs_id,
                token_docs,
                readonly=readonly
            )

            return render(request, 'editeur/document_public.html', {
                'document': lien.document,
                'lien': lien,
                'editor_url': editor_url,
            })
        except DocsServiceError:
            raise Http404(_("Service temporairement indisponible."))


# =============================================================================
# Export de documents
# =============================================================================

class DocumentExportView(LoginRequiredMixin, View):
    """Export d'un document dans différents formats."""

    def get(self, request, pk, format='pdf'):
        document = get_object_or_404(
            DocumentCollaboratif,
            pk=pk
        )

        # Vérifier l'accès
        user = request.user
        has_access = (
            document.createur == user or
            document.partages.filter(utilisateur=user).exists()
        )
        if not has_access:
            raise Http404()

        try:
            # Exporter depuis Docs
            content = docs_service.export_document(document.docs_id, format)

            # Sauvegarder la version exportée
            from django.core.files.base import ContentFile
            import hashlib

            version = VersionExportee(
                document=document,
                format_export=format.upper(),
                exporte_par=user,
                numero_version=document.versions_exportees.count() + 1,
                hash_contenu=hashlib.sha256(content).hexdigest(),
                taille=len(content)
            )

            filename = f"{document.titre}.{format}"
            version.fichier.save(filename, ContentFile(content))
            version.save()

            # Renvoyer le fichier
            content_types = {
                'pdf': 'application/pdf',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'odt': 'application/vnd.oasis.opendocument.text',
                'html': 'text/html',
                'md': 'text/markdown',
            }

            response = HttpResponse(content, content_type=content_types.get(format, 'application/octet-stream'))
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except DocsServiceError as e:
            messages.error(request, _("Erreur d'export: %(error)s") % {'error': str(e)})
            return redirect('editeur:document_detail', pk=pk)


class DocumentArchiveToGEDView(LoginRequiredMixin, View):
    """Archive un document collaboratif dans la GED."""

    def post(self, request, pk):
        document = get_object_or_404(
            DocumentCollaboratif,
            pk=pk,
            createur=request.user
        )

        try:
            # Exporter en PDF
            content = docs_service.export_document(document.docs_id, 'pdf')

            # Créer le document dans la GED
            from documents.models import Document as DocumentGED, TypeDocument
            from django.core.files.base import ContentFile

            type_doc = TypeDocument.objects.filter(code='AUTRE').first()

            doc_ged = DocumentGED(
                nom=f"{document.titre}.pdf",
                description=document.description or f"Export depuis l'éditeur collaboratif",
                mandat=document.mandat,
                dossier=document.dossier,
                type_document=type_doc,
                createur=request.user,
            )

            doc_ged.fichier.save(f"{document.titre}.pdf", ContentFile(content))
            doc_ged.save()

            # Lier les documents
            document.document_exporte = doc_ged
            document.statut = DocumentCollaboratif.Statut.ARCHIVE
            document.save()

            messages.success(
                request,
                _("Document archivé dans la GED avec succès.")
            )

        except DocsServiceError as e:
            messages.error(request, _("Erreur d'archivage: %(error)s") % {'error': str(e)})
        except Exception as e:
            logger.exception(f"Erreur archivage GED: {e}")
            messages.error(request, _("Erreur lors de l'archivage dans la GED."))

        return redirect('editeur:document_detail', pk=pk)


# =============================================================================
# Modèles de documents
# =============================================================================

class ModeleListView(LoginRequiredMixin, ListView):
    """Liste des modèles de documents."""
    model = ModeleDocument
    template_name = 'editeur/modele_list.html'
    context_object_name = 'modeles'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        queryset = ModeleDocument.objects.filter(
            Q(est_public=True) | Q(cree_par=user)
        )

        categorie = self.request.GET.get('categorie')
        if categorie:
            queryset = queryset.filter(categorie=categorie)

        return queryset.order_by('categorie', 'nom')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ModeleDocument.Categorie.choices
        return context


class ModeleCreateView(LoginRequiredMixin, CreateView):
    """Création d'un modèle de document."""
    model = ModeleDocument
    form_class = ModeleDocumentForm
    template_name = 'editeur/modele_form.html'
    success_url = reverse_lazy('editeur:modele_list')

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        messages.success(self.request, _("Modèle créé avec succès."))
        return super().form_valid(form)


# =============================================================================
# Webhooks (synchronisation avec Docs)
# =============================================================================

@method_decorator(csrf_exempt, name='dispatch')
class DocsWebhookView(View):
    """
    Webhook pour recevoir les événements de Docs.

    Événements gérés:
    - document.updated: Mise à jour d'un document
    - session.started: Début d'édition
    - session.ended: Fin d'édition
    """

    def post(self, request):
        # Vérifier la signature du webhook
        # TODO: Implémenter la vérification HMAC

        try:
            import json
            data = json.loads(request.body)
            event_type = data.get('event')
            payload = data.get('payload', {})

            if event_type == 'document.updated':
                self._handle_document_updated(payload)
            elif event_type == 'session.started':
                self._handle_session_started(payload)
            elif event_type == 'session.ended':
                self._handle_session_ended(payload)

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            logger.exception(f"Erreur webhook Docs: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def _handle_document_updated(self, payload):
        """Gère la mise à jour d'un document."""
        docs_id = payload.get('document_id')
        if not docs_id:
            return

        try:
            document = DocumentCollaboratif.objects.get(docs_id=docs_id)
            document.marquer_modifie()

            # Mettre à jour les stats
            if 'title' in payload:
                document.titre = payload['title']
            if 'content_length' in payload:
                document.taille_contenu = payload['content_length']

            document.save()
            logger.info(f"Document {docs_id} mis à jour via webhook")

        except DocumentCollaboratif.DoesNotExist:
            logger.warning(f"Document Docs {docs_id} non trouvé dans AltiusOne")

    def _handle_session_started(self, payload):
        """Gère le début d'une session d'édition."""
        docs_id = payload.get('document_id')
        external_user_id = payload.get('user_external_id', '')

        if not docs_id or not external_user_id.startswith('altiusone_'):
            return

        try:
            document = DocumentCollaboratif.objects.get(docs_id=docs_id)
            user_id = external_user_id.replace('altiusone_', '')

            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)

            SessionEdition.objects.create(
                document=document,
                utilisateur=user,
                session_id=payload.get('session_id', ''),
                user_agent=payload.get('user_agent', ''),
                ip_address=payload.get('ip_address')
            )

            logger.info(f"Session démarrée: {user.email} sur {document.titre}")

        except Exception as e:
            logger.warning(f"Erreur création session: {e}")

    def _handle_session_ended(self, payload):
        """Gère la fin d'une session d'édition."""
        session_id = payload.get('session_id')
        if not session_id:
            return

        try:
            session = SessionEdition.objects.get(session_id=session_id, est_active=True)
            session.terminer()
            logger.info(f"Session terminée: {session}")

        except SessionEdition.DoesNotExist:
            pass
