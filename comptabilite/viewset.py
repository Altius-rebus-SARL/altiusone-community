# comptabilite/viewset.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, F
from decimal import Decimal
from datetime import date

from .models import (
    PlanComptable,
    Compte,
    Journal,
    EcritureComptable,
    PieceComptable,
    Lettrage,
)
from .serializers import (
    PlanComptableSerializer,
    CompteListSerializer,
    CompteDetailSerializer,
    JournalSerializer,
    EcritureComptableListSerializer,
    EcritureComptableDetailSerializer,
    EcritureComptableCreateSerializer,
    PieceComptableSerializer,
    PieceComptableListSerializer,
    PieceComptableDetailSerializer,
    PieceComptableCreateSerializer,
    PieceComptableCreateWithEcrituresSerializer,
    TypePieceComptableSerializer,
    LettrageSerializer,
    BalanceSerializer,
    BilanSerializer,
    CompteResultatsSerializer,
)
from .models import TypePieceComptable
from core.models import Mandat


class PlanComptableViewSet(viewsets.ModelViewSet):
    """ViewSet pour les plans comptables"""

    queryset = PlanComptable.objects.all()
    serializer_class = PlanComptableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["type_plan", "is_template", "mandat"]
    search_fields = ["nom", "description"]
    ordering = ["nom"]

    @action(detail=False, methods=["get"])
    def templates(self, request):
        """Récupérer les plans comptables templates"""
        templates = self.queryset.filter(is_template=True)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def dupliquer(self, request, pk=None):
        """Dupliquer un plan comptable pour un mandat"""
        plan_source = self.get_object()
        mandat_id = request.data.get("mandat_id")

        if not mandat_id:
            return Response(
                {"error": "mandat_id requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Créer le nouveau plan
        nouveau_plan = PlanComptable.objects.create(
            nom=f"{plan_source.nom} - Copie",
            type_plan=plan_source.type_plan,
            mandat_id=mandat_id,
            base_sur=plan_source,
            is_template=False,
        )

        # Copier les comptes
        comptes_mapping = {}
        for compte in plan_source.comptes.all():
            nouveau_compte = Compte.objects.create(
                plan_comptable=nouveau_plan,
                numero=compte.numero,
                libelle=compte.libelle,
                libelle_court=compte.libelle_court,
                type_compte=compte.type_compte,
                classe=compte.classe,
                niveau=compte.niveau,
                est_collectif=compte.est_collectif,
                imputable=compte.imputable,
                lettrable=compte.lettrable,
                obligatoire_tiers=compte.obligatoire_tiers,
                soumis_tva=compte.soumis_tva,
                code_tva_defaut=compte.code_tva_defaut,
            )
            comptes_mapping[compte.id] = nouveau_compte

        # Mettre à jour les parents
        for ancien_id, nouveau_compte in comptes_mapping.items():
            ancien_compte = Compte.objects.get(id=ancien_id)
            if ancien_compte.compte_parent:
                nouveau_compte.compte_parent = comptes_mapping[
                    ancien_compte.compte_parent.id
                ]
                nouveau_compte.save()

        serializer = self.get_serializer(nouveau_plan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CompteViewSet(viewsets.ModelViewSet):
    """ViewSet pour les comptes"""

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "plan_comptable",
        "type_compte",
        "classe",
        "imputable",
        "lettrable",
    ]
    search_fields = ["numero", "libelle", "libelle_court"]
    ordering = ["numero"]

    def get_queryset(self):
        return Compte.objects.select_related(
            "plan_comptable", "compte_parent"
        ).prefetch_related("sous_comptes")

    def get_serializer_class(self):
        if self.action == "list":
            return CompteListSerializer
        return CompteDetailSerializer

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Récupérer l'arbre hiérarchique des comptes"""
        plan_comptable_id = request.query_params.get("plan_comptable")

        if not plan_comptable_id:
            return Response(
                {"error": "plan_comptable requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer les comptes racines
        comptes_racines = self.get_queryset().filter(
            plan_comptable_id=plan_comptable_id, compte_parent__isnull=True
        )

        def build_tree(compte):
            data = CompteListSerializer(compte).data
            sous_comptes = compte.sous_comptes.all()
            if sous_comptes:
                data["children"] = [build_tree(sc) for sc in sous_comptes]
            return data

        tree = [build_tree(compte) for compte in comptes_racines]
        return Response(tree)

    @action(detail=True, methods=["get"])
    def solde(self, request, pk=None):
        """Récupérer le solde détaillé d'un compte"""
        compte = self.get_object()

        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")

        ecritures = EcritureComptable.objects.filter(compte=compte, statut="VALIDE")

        if date_debut:
            ecritures = ecritures.filter(date_ecriture__gte=date_debut)
        if date_fin:
            ecritures = ecritures.filter(date_ecriture__lte=date_fin)

        totaux = ecritures.aggregate(
            total_debit=Sum("montant_debit"), total_credit=Sum("montant_credit")
        )

        return Response(
            {
                "compte": CompteListSerializer(compte).data,
                "total_debit": totaux["total_debit"] or Decimal("0"),
                "total_credit": totaux["total_credit"] or Decimal("0"),
                "solde": compte.solde,
                "periode": {"date_debut": date_debut, "date_fin": date_fin},
            }
        )


class JournalViewSet(viewsets.ModelViewSet):
    """ViewSet pour les journaux"""

    serializer_class = JournalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["mandat", "type_journal"]
    search_fields = ["code", "libelle"]
    ordering = ["code"]

    def get_queryset(self):
        return Journal.objects.filter(is_active=True).select_related(
            'mandat', 'compte_contrepartie_defaut'
        )

    @action(detail=True, methods=["post"])
    def generer_numero(self, request, pk=None):
        """Générer un nouveau numéro de pièce"""
        journal = self.get_object()
        numero = journal.get_next_numero()
        return Response({"numero_piece": numero})


class EcritureComptableViewSet(viewsets.ModelViewSet):
    """ViewSet pour les écritures comptables"""

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["mandat", "journal", "compte", "statut", "exercice"]
    search_fields = ["numero_piece", "libelle", "compte__numero", "compte__libelle"]
    ordering = ["-date_ecriture", "numero_piece", "numero_ligne"]

    def get_queryset(self):
        return EcritureComptable.objects.select_related(
            "mandat", "journal", "compte", "exercice", "piece", "tiers", "valide_par"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return EcritureComptableCreateSerializer
        elif self.action == "list":
            return EcritureComptableListSerializer
        return EcritureComptableDetailSerializer

    @action(detail=False, methods=["get"])
    def par_periode(self, request):
        """Récupérer les écritures pour une période"""
        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")

        if not date_debut or not date_fin:
            return Response(
                {"error": "date_debut et date_fin requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ecritures = self.get_queryset().filter(
            date_ecriture__gte=date_debut, date_ecriture__lte=date_fin
        )

        serializer = self.get_serializer(ecritures, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Valider une écriture"""
        ecriture = self.get_object()

        if ecriture.statut == "VALIDE":
            return Response(
                {"error": "Écriture déjà validée"}, status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone

        ecriture.statut = "VALIDE"
        ecriture.valide_par = request.user
        ecriture.date_validation = timezone.now()
        ecriture.save()

        # Mettre à jour les soldes du compte
        compte = ecriture.compte
        compte.solde_debit += ecriture.montant_debit
        compte.solde_credit += ecriture.montant_credit
        compte.save()

        serializer = self.get_serializer(ecriture)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def lettrer(self, request, pk=None):
        """Lettrer une écriture"""
        ecriture = self.get_object()
        code_lettrage = request.data.get("code_lettrage")

        if not code_lettrage:
            return Response(
                {"error": "code_lettrage requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone

        ecriture.code_lettrage = code_lettrage
        ecriture.date_lettrage = timezone.now().date()
        ecriture.statut = "LETTRE"
        ecriture.save()

        serializer = self.get_serializer(ecriture)
        return Response(serializer.data)


class PieceComptableViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les pièces comptables.

    Endpoints:
    - GET    /pieces/                    Liste des pièces
    - POST   /pieces/                    Créer une pièce
    - GET    /pieces/{id}/               Détail d'une pièce
    - PUT    /pieces/{id}/               Modifier une pièce
    - DELETE /pieces/{id}/               Supprimer une pièce
    - POST   /pieces/{id}/recalculer/    Recalculer l'équilibre
    - POST   /pieces/{id}/valider/       Valider une pièce
    - POST   /pieces/{id}/ajouter_document/  Ajouter un document
    - GET    /pieces/types/              Liste des types de pièces
    - GET    /pieces/statistiques/       Statistiques des pièces
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["mandat", "journal", "type_piece", "equilibree", "statut", "dossier"]
    search_fields = ["numero_piece", "libelle", "reference_externe", "tiers_nom"]
    ordering_fields = ["date_piece", "numero_piece", "montant_ttc", "created_at"]
    ordering = ["-date_piece", "-created_at"]

    def get_queryset(self):
        return PieceComptable.objects.select_related(
            "mandat", "mandat__client", "journal", "type_piece", "tiers", "dossier", "valide_par"
        ).prefetch_related("documents", "ecritures")

    def get_serializer_class(self):
        if self.action == "create":
            return PieceComptableCreateWithEcrituresSerializer
        elif self.action == "list":
            return PieceComptableListSerializer
        elif self.action in ["retrieve", "update", "partial_update"]:
            return PieceComptableDetailSerializer
        return PieceComptableSerializer

    def perform_create(self, serializer):
        """Ajoute le created_by automatiquement"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def recalculer(self, request, pk=None):
        """Recalculer l'équilibre d'une pièce"""
        piece = self.get_object()
        equilibree = piece.calculer_equilibre()

        return Response(
            {
                "equilibree": equilibree,
                "total_debit": piece.total_debit,
                "total_credit": piece.total_credit,
            }
        )

    @action(detail=True, methods=["post"])
    def valider(self, request, pk=None):
        """Valider une pièce comptable"""
        from django.utils import timezone

        piece = self.get_object()

        if piece.statut == "VALIDE":
            return Response(
                {"error": "Cette pièce est déjà validée"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier l'équilibre si des écritures sont associées
        if piece.ecritures.exists() and not piece.equilibree:
            piece.calculer_equilibre()
            if not piece.equilibree:
                return Response(
                    {"error": "La pièce n'est pas équilibrée"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        piece.statut = "VALIDE"
        piece.valide_par = request.user
        piece.date_validation = timezone.now()
        piece.save()

        serializer = PieceComptableDetailSerializer(piece)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def ajouter_document(self, request, pk=None):
        """Ajouter un document à une pièce comptable"""
        piece = self.get_object()
        document_id = request.data.get("document_id")

        if not document_id:
            return Response(
                {"error": "document_id requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from documents.models import Document
            document = Document.objects.get(id=document_id)
            piece.documents.add(document)

            return Response({
                "success": True,
                "message": f"Document {document.nom_fichier} ajouté à la pièce"
            })
        except Document.DoesNotExist:
            return Response(
                {"error": "Document non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["get"])
    def types(self, request):
        """Liste des types de pièces comptables"""
        types = TypePieceComptable.objects.filter(is_active=True).order_by("ordre", "code")
        serializer = TypePieceComptableSerializer(types, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def statistiques(self, request):
        """Statistiques des pièces comptables"""
        mandat_id = request.query_params.get("mandat")
        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")

        qs = self.get_queryset()

        if mandat_id:
            qs = qs.filter(mandat_id=mandat_id)
        if date_debut:
            qs = qs.filter(date_piece__gte=date_debut)
        if date_fin:
            qs = qs.filter(date_piece__lte=date_fin)

        # Statistiques par statut
        stats_statut = {}
        for statut, label in PieceComptable.STATUT_CHOICES:
            count = qs.filter(statut=statut).count()
            stats_statut[statut] = {"label": label, "count": count}

        # Statistiques par type de pièce
        stats_type = []
        for type_piece in TypePieceComptable.objects.filter(is_active=True):
            count = qs.filter(type_piece=type_piece).count()
            total = qs.filter(type_piece=type_piece).aggregate(
                total=Sum("montant_ttc")
            )["total"] or Decimal("0")
            stats_type.append({
                "type_piece": type_piece.code,
                "libelle": type_piece.libelle,
                "count": count,
                "total": float(total)
            })

        # Totaux globaux
        totaux = qs.aggregate(
            total_ht=Sum("montant_ht"),
            total_tva=Sum("montant_tva"),
            total_ttc=Sum("montant_ttc")
        )

        return Response({
            "nombre_total": qs.count(),
            "par_statut": stats_statut,
            "par_type": stats_type,
            "totaux": {
                "montant_ht": float(totaux["total_ht"] or 0),
                "montant_tva": float(totaux["total_tva"] or 0),
                "montant_ttc": float(totaux["total_ttc"] or 0),
            },
            "periode": {
                "date_debut": date_debut,
                "date_fin": date_fin
            }
        })


    @action(detail=False, methods=["get"], url_path="comptes/(?P<mandat_pk>[^/.]+)")
    def comptes(self, request, mandat_pk=None):
        """Retourne les comptes imputables du plan actif d'un mandat.

        GET /pieces/comptes/{mandat_pk}/
        """
        from django.shortcuts import get_object_or_404

        mandat = get_object_or_404(Mandat, pk=mandat_pk)
        plan = mandat.plan_comptable
        if not plan:
            return Response({"comptes": []})

        comptes = Compte.objects.filter(
            plan_comptable=plan, imputable=True, is_active=True,
        ).order_by("numero")

        serializer = CompteListSerializer(comptes, many=True)
        return Response({"comptes": serializer.data})


class LettrageViewSet(viewsets.ModelViewSet):
    """ViewSet pour les lettrages"""

    queryset = Lettrage.objects.all()
    serializer_class = LettrageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["mandat", "compte", "complet"]
    ordering = ["-date_lettrage"]

    @action(detail=True, methods=["get"])
    def ecritures(self, request, pk=None):
        """Récupérer les écritures lettrées"""
        lettrage = self.get_object()
        ecritures = EcritureComptable.objects.filter(
            code_lettrage=lettrage.code_lettrage
        )
        serializer = EcritureComptableListSerializer(ecritures, many=True)
        return Response(serializer.data)


class BankStatementViewSet(viewsets.ViewSet):
    """ViewSet pour l'import de releves bancaires camt.053."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def preview(self, request):
        """
        Upload XML camt.053 et retourne un preview JSON sans sauvegarder.
        POST /api/v1/comptabilite/releves-bancaires/preview/
        """
        from comptabilite.services import Camt053ParserService

        xml_file = request.FILES.get('file')
        if not xml_file:
            return Response(
                {'error': 'Fichier XML requis'}, status=status.HTTP_400_BAD_REQUEST
            )

        xml_content = xml_file.read()
        statement = Camt053ParserService.parse(xml_content)

        if statement.error:
            return Response({'error': statement.error}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'statement_id': statement.statement_id,
            'iban': statement.iban,
            'currency': statement.currency,
            'opening_balance': str(statement.opening_balance),
            'closing_balance': str(statement.closing_balance),
            'entries_count': len(statement.entries),
            'entries': [
                {
                    'booking_date': str(e.booking_date) if e.booking_date else None,
                    'value_date': str(e.value_date) if e.value_date else None,
                    'amount': str(e.amount),
                    'currency': e.currency,
                    'credit_debit': e.credit_debit,
                    'counterparty_name': e.counterparty_name,
                    'counterparty_iban': e.counterparty_iban,
                    'reference': e.reference,
                    'remittance_info': e.remittance_info,
                    'end_to_end_id': e.end_to_end_id,
                    'bank_reference': e.bank_reference,
                }
                for e in statement.entries
            ],
        })

    @action(detail=False, methods=['post'])
    def importer(self, request):
        """
        Upload XML camt.053 et cree les ecritures en brouillon.
        POST /api/v1/comptabilite/releves-bancaires/importer/
        """
        from comptabilite.services import Camt053ParserService
        from core.models import Mandat, ExerciceComptable

        xml_file = request.FILES.get('file')
        mandat_id = request.data.get('mandat_id')
        journal_id = request.data.get('journal_id')
        compte_banque_id = request.data.get('compte_banque_id')
        exercice_id = request.data.get('exercice_id')

        if not all([xml_file, mandat_id, journal_id, compte_banque_id, exercice_id]):
            return Response(
                {'error': 'file, mandat_id, journal_id, compte_banque_id et exercice_id requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        xml_content = xml_file.read()
        statement = Camt053ParserService.parse(xml_content)
        if statement.error:
            return Response({'error': statement.error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mandat = Mandat.objects.get(id=mandat_id)
            journal = Journal.objects.get(id=journal_id)
            from comptabilite.models import Compte
            compte_banque = Compte.objects.get(id=compte_banque_id)
            exercice = ExerciceComptable.objects.get(id=exercice_id)
        except (Mandat.DoesNotExist, Journal.DoesNotExist, Compte.DoesNotExist,
                ExerciceComptable.DoesNotExist) as e:
            return Response(
                {'error': f'Objet non trouve: {e}'},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = Camt053ParserService.generate_ecritures(
            statement, mandat, journal, compte_banque, exercice, request.user
        )
        return Response(result, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ViewSet):
    """ViewSet pour la generation de fichiers pain.001."""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='a-payer')
    def a_payer(self, request):
        """
        Liste des factures fournisseurs validees en attente de paiement.
        GET /api/v1/comptabilite/paiements/a-payer/?mandat=...
        """
        mandat_id = request.query_params.get('mandat')
        if not mandat_id:
            return Response(
                {'error': 'Parametre mandat requis'}, status=status.HTTP_400_BAD_REQUEST
            )

        pieces = PieceComptable.objects.filter(
            mandat_id=mandat_id,
            type_piece__code='FAC_ACH',
            statut='VALIDE',
        ).select_related('type_piece').order_by('-date_piece')

        data = [
            {
                'id': str(p.id),
                'numero_piece': p.numero_piece,
                'date_piece': str(p.date_piece),
                'libelle': p.libelle,
                'tiers_nom': p.tiers_nom,
                'montant_ttc': str(p.montant_ttc) if p.montant_ttc else '0.00',
                'reference_externe': p.reference_externe,
            }
            for p in pieces
        ]
        return Response({'count': len(data), 'results': data})

    @action(detail=False, methods=['post'], url_path='generer-pain001')
    def generer_pain001(self, request):
        """
        Genere un fichier XML pain.001.
        POST /api/v1/comptabilite/paiements/generer-pain001/
        Body: {piece_ids: [...], compte_bancaire_id: "..."}
        """
        from comptabilite.services import Pain001GeneratorService
        from core.models import CompteBancaire

        piece_ids = request.data.get('piece_ids', [])
        compte_bancaire_id = request.data.get('compte_bancaire_id')

        if not piece_ids or not compte_bancaire_id:
            return Response(
                {'error': 'piece_ids et compte_bancaire_id requis'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            compte_bancaire = CompteBancaire.objects.get(id=compte_bancaire_id)
        except CompteBancaire.DoesNotExist:
            return Response(
                {'error': 'Compte bancaire non trouve'},
                status=status.HTTP_404_NOT_FOUND,
            )

        order = Pain001GeneratorService.from_pieces_comptables(piece_ids, compte_bancaire)
        skipped = getattr(order, '_skipped', [])

        if not order.payments:
            return Response(
                {
                    'error': 'Aucune pièce valide pour générer le pain.001',
                    'pieces_ignorees': skipped,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        xml_bytes = Pain001GeneratorService.generate(order)

        from django.http import HttpResponse
        response = HttpResponse(xml_bytes, content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="pain001_{order.message_id}.xml"'
        if skipped:
            # Header informatif pour le frontend
            response['X-Pieces-Ignorees'] = str(len(skipped))
        return response


class RapportsViewSet(viewsets.ViewSet):
    """ViewSet pour les rapports comptables"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def balance(self, request):
        """Générer la balance des comptes"""
        mandat_id = request.query_params.get("mandat")
        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")

        if not mandat_id or not date_debut or not date_fin:
            return Response(
                {"error": "mandat, date_debut et date_fin requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupérer tous les comptes du mandat via le plan actif
        mandat = Mandat.objects.filter(pk=mandat_id).first()
        plan = mandat.plan_comptable if mandat else None
        if not plan:
            return Response(
                {"error": "Aucun plan comptable trouvé pour ce mandat"},
                status=status.HTTP_404_NOT_FOUND,
            )
        comptes = Compte.objects.filter(
            plan_comptable=plan, imputable=True
        )

        balance_data = []
        for compte in comptes:
            ecritures = EcritureComptable.objects.filter(
                compte=compte,
                mandat_id=mandat_id,
                date_ecriture__gte=date_debut,
                date_ecriture__lte=date_fin,
                statut="VALIDE",
            )

            totaux = ecritures.aggregate(
                total_debit=Sum("montant_debit"), total_credit=Sum("montant_credit")
            )

            balance_data.append(
                {
                    "compte": CompteListSerializer(compte).data,
                    "solde_debit_initial": compte.solde_debit,
                    "solde_credit_initial": compte.solde_credit,
                    "mouvements_debit": totaux["total_debit"] or Decimal("0"),
                    "mouvements_credit": totaux["total_credit"] or Decimal("0"),
                    "solde_debit_final": compte.solde_debit
                    + (totaux["total_debit"] or Decimal("0")),
                    "solde_credit_final": compte.solde_credit
                    + (totaux["total_credit"] or Decimal("0")),
                    "solde": compte.solde,
                }
            )

        serializer = BalanceSerializer(balance_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def bilan(self, request):
        """Générer le bilan (Actifs vs Passifs) — PME suisse classes 1 et 2"""
        mandat_id = request.query_params.get("mandat")
        date_bilan = request.query_params.get("date")
        exercice_id = request.query_params.get("exercice")

        if not mandat_id or not date_bilan:
            return Response(
                {"error": "mandat et date requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        mandat = Mandat.objects.filter(pk=mandat_id).first()
        plan = mandat.plan_comptable if mandat else None
        if not plan:
            return Response(
                {"error": "Aucun plan comptable trouvé pour ce mandat"},
                status=status.HTTP_404_NOT_FOUND,
            )

        def _solde_comptes(type_compte):
            comptes = Compte.objects.filter(
                plan_comptable=plan, imputable=True, type_compte=type_compte
            ).order_by("numero")
            items = []
            total = Decimal("0")
            for compte in comptes:
                qs = EcritureComptable.objects.filter(
                    compte=compte,
                    statut__in=["VALIDE", "LETTRE", "CLOTURE"],
                )
                if exercice_id:
                    qs = qs.filter(exercice_id=exercice_id)
                else:
                    qs = qs.filter(date_ecriture__lte=date_bilan)
                debit = qs.aggregate(s=Sum("montant_debit"))["s"] or Decimal("0")
                credit = qs.aggregate(s=Sum("montant_credit"))["s"] or Decimal("0")
                solde = debit - credit if type_compte == "ACTIF" else credit - debit
                if solde != 0:
                    items.append({
                        "compte": CompteListSerializer(compte).data,
                        "solde": solde,
                    })
                    total += solde
            return items, total

        actifs, total_actifs = _solde_comptes("ACTIF")
        passifs, total_passifs = _solde_comptes("PASSIF")

        bilan_data = {
            "actif_circulant": total_actifs,
            "actif_immobilise": Decimal("0"),
            "total_actif": total_actifs,
            "capitaux_tiers_ct": Decimal("0"),
            "capitaux_tiers_lt": Decimal("0"),
            "capitaux_propres": total_passifs,
            "total_passif": total_passifs,
            "details": {
                "actifs": actifs,
                "passifs": passifs,
                "equilibre": total_actifs == total_passifs,
            },
        }

        serializer = BilanSerializer(bilan_data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def compte_resultats(self, request):
        """Générer le compte de résultats (Produits vs Charges) — PME suisse classes 3-8"""
        mandat_id = request.query_params.get("mandat")
        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")
        exercice_id = request.query_params.get("exercice")

        if not mandat_id or not date_debut or not date_fin:
            return Response(
                {"error": "mandat, date_debut et date_fin requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mandat = Mandat.objects.filter(pk=mandat_id).first()
        plan = mandat.plan_comptable if mandat else None
        if not plan:
            return Response(
                {"error": "Aucun plan comptable trouvé pour ce mandat"},
                status=status.HTTP_404_NOT_FOUND,
            )

        def _solde_comptes(type_compte):
            comptes = Compte.objects.filter(
                plan_comptable=plan, imputable=True, type_compte=type_compte
            ).order_by("numero")
            items = []
            total = Decimal("0")
            for compte in comptes:
                qs = EcritureComptable.objects.filter(
                    compte=compte,
                    date_ecriture__gte=date_debut,
                    date_ecriture__lte=date_fin,
                    statut__in=["VALIDE", "LETTRE", "CLOTURE"],
                )
                if exercice_id:
                    qs = qs.filter(exercice_id=exercice_id)
                debit = qs.aggregate(s=Sum("montant_debit"))["s"] or Decimal("0")
                credit = qs.aggregate(s=Sum("montant_credit"))["s"] or Decimal("0")
                solde = debit - credit if type_compte == "CHARGE" else credit - debit
                if solde != 0:
                    items.append({
                        "compte": CompteListSerializer(compte).data,
                        "solde": solde,
                    })
                    total += solde
            return items, total

        produits, total_produits = _solde_comptes("PRODUIT")
        charges, total_charges = _solde_comptes("CHARGE")
        resultat = total_produits - total_charges

        cr_data = {
            "produits_exploitation": total_produits,
            "charges_exploitation": total_charges,
            "resultat_exploitation": resultat,
            "produits_financiers": Decimal("0"),
            "charges_financieres": Decimal("0"),
            "resultat_financier": Decimal("0"),
            "resultat_avant_impots": resultat,
            "impots": Decimal("0"),
            "resultat_net": resultat,
            "details": {
                "produits": produits,
                "charges": charges,
            },
        }

        serializer = CompteResultatsSerializer(cr_data)
        return Response(serializer.data)


# ══════════════════════════════════════════════════════════════
# COMPTABILITE ANALYTIQUE
# ══════════════════════════════════════════════════════════════

from .models import AxeAnalytique, SectionAnalytique, VentilationAnalytique
from .serializers import (
    AxeAnalytiqueSerializer,
    SectionAnalytiqueSerializer,
    VentilationAnalytiqueSerializer,
)


class AxeAnalytiqueViewSet(viewsets.ModelViewSet):
    serializer_class = AxeAnalytiqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['mandat']

    def get_queryset(self):
        return AxeAnalytique.objects.filter(
            is_active=True
        ).prefetch_related('sections')


class SectionAnalytiqueViewSet(viewsets.ModelViewSet):
    serializer_class = SectionAnalytiqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['axe', 'axe__mandat', 'parent']
    search_fields = ['code', 'libelle']

    def get_queryset(self):
        return SectionAnalytique.objects.filter(
            is_active=True
        ).select_related('axe', 'parent')


class VentilationAnalytiqueViewSet(viewsets.ModelViewSet):
    serializer_class = VentilationAnalytiqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ecriture', 'section', 'section__axe']

    def get_queryset(self):
        return VentilationAnalytique.objects.select_related(
            'section', 'section__axe'
        )


# ══════════════════════════════════════════════════════════════
# IMMOBILISATIONS
# ══════════════════════════════════════════════════════════════

from .models import Immobilisation
from .serializers import (
    ImmobilisationListSerializer,
    ImmobilisationDetailSerializer,
    ImmobilisationCreateSerializer,
)


class ImmobilisationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mandat', 'statut', 'categorie', 'methode_amortissement']
    search_fields = ['numero', 'designation', 'fournisseur']
    ordering_fields = ['numero', 'date_acquisition', 'valeur_nette_comptable']
    ordering = ['numero']

    def get_queryset(self):
        return Immobilisation.objects.filter(
            is_active=True
        ).select_related('compte_immobilisation', 'compte_amortissement', 'devise')

    def get_serializer_class(self):
        if self.action == 'list':
            return ImmobilisationListSerializer
        if self.action == 'create':
            return ImmobilisationCreateSerializer
        return ImmobilisationDetailSerializer


# ══════════════════════════════════════════════════════════════
# RAPPROCHEMENT BANCAIRE
# ══════════════════════════════════════════════════════════════

from .models import ReleveBancaire, LigneReleve
from .serializers import (
    ReleveBancaireListSerializer,
    ReleveBancaireDetailSerializer,
    LigneReleveSerializer,
)


class ReleveBancaireViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['mandat', 'compte_bancaire', 'statut']
    ordering = ['-date_fin']

    def get_queryset(self):
        return ReleveBancaire.objects.filter(
            is_active=True
        ).select_related('compte_bancaire', 'devise')

    def get_serializer_class(self):
        if self.action in ('retrieve',):
            return ReleveBancaireDetailSerializer
        return ReleveBancaireListSerializer


class LigneReleveViewSet(viewsets.ModelViewSet):
    serializer_class = LigneReleveSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['releve', 'statut']
    search_fields = ['libelle', 'reference']

    def get_queryset(self):
        return LigneReleve.objects.filter(
            is_active=True
        ).select_related('ecriture')
