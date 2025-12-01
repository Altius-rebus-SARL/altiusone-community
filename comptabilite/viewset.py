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
    LettrageSerializer,
    BalanceSerializer,
    BilanSerializer,
    CompteResultatsSerializer,
)


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

    queryset = Journal.objects.all()
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
            "mandat", "journal", "compte", "exercice", "valide_par"
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
    """ViewSet pour les pièces comptables"""

    queryset = PieceComptable.objects.all()
    serializer_class = PieceComptableSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["mandat", "journal", "equilibree", "statut"]
    search_fields = ["numero_piece", "libelle"]
    ordering = ["-date_piece"]

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

        # Récupérer tous les comptes du mandat
        comptes = Compte.objects.filter(
            plan_comptable__mandat_id=mandat_id, imputable=True
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
        """Générer le bilan"""
        mandat_id = request.query_params.get("mandat")
        date = request.query_params.get("date")

        if not mandat_id or not date:
            return Response(
                {"error": "mandat et date requis"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Calculs simplifiés pour l'exemple
        actif_circulant = Decimal("0")
        actif_immobilise = Decimal("0")
        capitaux_tiers_ct = Decimal("0")
        capitaux_tiers_lt = Decimal("0")
        capitaux_propres = Decimal("0")

        # TODO: Implémenter la logique réelle de calcul

        bilan_data = {
            "actif_circulant": actif_circulant,
            "actif_immobilise": actif_immobilise,
            "total_actif": actif_circulant + actif_immobilise,
            "capitaux_tiers_ct": capitaux_tiers_ct,
            "capitaux_tiers_lt": capitaux_tiers_lt,
            "capitaux_propres": capitaux_propres,
            "total_passif": capitaux_tiers_ct + capitaux_tiers_lt + capitaux_propres,
            "details": {},
        }

        serializer = BilanSerializer(bilan_data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def compte_resultats(self, request):
        """Générer le compte de résultats"""
        mandat_id = request.query_params.get("mandat")
        date_debut = request.query_params.get("date_debut")
        date_fin = request.query_params.get("date_fin")

        if not mandat_id or not date_debut or not date_fin:
            return Response(
                {"error": "mandat, date_debut et date_fin requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculs simplifiés pour l'exemple
        produits_exploitation = Decimal("0")
        charges_exploitation = Decimal("0")
        produits_financiers = Decimal("0")
        charges_financieres = Decimal("0")
        impots = Decimal("0")

        # TODO: Implémenter la logique réelle de calcul

        resultat_exploitation = produits_exploitation - charges_exploitation
        resultat_financier = produits_financiers - charges_financieres
        resultat_avant_impots = resultat_exploitation + resultat_financier
        resultat_net = resultat_avant_impots - impots

        cr_data = {
            "produits_exploitation": produits_exploitation,
            "charges_exploitation": charges_exploitation,
            "resultat_exploitation": resultat_exploitation,
            "produits_financiers": produits_financiers,
            "charges_financieres": charges_financieres,
            "resultat_financier": resultat_financier,
            "resultat_avant_impots": resultat_avant_impots,
            "impots": impots,
            "resultat_net": resultat_net,
            "details": {},
        }

        serializer = CompteResultatsSerializer(cr_data)
        return Response(serializer.data)
