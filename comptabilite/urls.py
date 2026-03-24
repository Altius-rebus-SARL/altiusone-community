# comptabilite/urls.py
from django.urls import path
from . import views

app_name = "comptabilite"

urlpatterns = [
    # =========================================================================
    # TYPES DE PLANS COMPTABLES (PME, OHADA, Swiss GAAP, etc.)
    # =========================================================================
    path("types-plans/", views.TypePlanComptableListView.as_view(), name="type-plan-list"),
    path(
        "types-plans/<uuid:pk>/",
        views.TypePlanComptableDetailView.as_view(),
        name="type-plan-detail"
    ),
    path(
        "types-plans/<uuid:pk>/classes/",
        views.ClasseComptableListView.as_view(),
        name="classe-list"
    ),

    # =========================================================================
    # PLANS COMPTABLES (instances pour mandats)
    # =========================================================================
    path("plans/", views.PlanComptableListView.as_view(), name="plan-list"),
    path(
        "plans/type/<uuid:type_pk>/",
        views.PlanComptableListView.as_view(),
        name="plan-list-by-type"
    ),
    path("plans/nouveau/", views.PlanComptableCreateView.as_view(), name="plan-create"),
    path(
        "plans/nouveau/type/<uuid:type_pk>/",
        views.PlanComptableCreateView.as_view(),
        name="plan-create-with-type"
    ),
    path(
        "plans/<uuid:pk>/", views.PlanComptableDetailView.as_view(), name="plan-detail"
    ),
    path(
        "plans/<uuid:pk>/modifier/",
        views.PlanComptableUpdateView.as_view(),
        name="plan-update",
    ),
    # Comptes
    path("comptes/", views.CompteListView.as_view(), name="compte-list"),
    path(
        "comptes/plan/<uuid:plan_pk>/",
        views.CompteListView.as_view(),
        name="compte-list-plan",
    ),
    path("comptes/nouveau/", views.CompteCreateView.as_view(), name="compte-create"),
    path(
        "comptes/plan/<uuid:plan_pk>/nouveau/",
        views.CompteCreateView.as_view(),
        name="compte-create-plan",
    ),
    path("comptes/<uuid:pk>/", views.CompteDetailView.as_view(), name="compte-detail"),
    path(
        "comptes/<uuid:pk>/modifier/",
        views.CompteUpdateView.as_view(),
        name="compte-update",
    ),
    path("comptes/<uuid:compte_pk>/grand-livre/", views.grand_livre, name="grand-livre"),
    # Journaux
    path("journaux/", views.JournalListView.as_view(), name="journal-list"),
    path("journaux/nouveau/", views.JournalCreateView.as_view(), name="journal-create"),
    path(
        "journaux/<uuid:pk>/", views.JournalDetailView.as_view(), name="journal-detail"
    ),
    path(
        "journaux/<uuid:pk>/modifier/",
        views.JournalUpdateView.as_view(),
        name="journal-update",
    ),
    # Écritures comptables
    path("ecritures/", views.EcritureComptableListView.as_view(), name="ecriture-list"),
    path(
        "ecritures/nouvelle/",
        views.EcritureComptableCreateView.as_view(),
        name="ecriture-create",
    ),
    path(
        "ecritures/<uuid:pk>/",
        views.EcritureComptableDetailView.as_view(),
        name="ecriture-detail",
    ),
    path(
        "ecritures/<uuid:pk>/modifier/",
        views.EcritureComptableUpdateView.as_view(),
        name="ecriture-update",
    ),
    # Pièces comptables
    path("pieces/", views.PieceComptableListView.as_view(), name="piece-list"),
    path(
        "pieces/nouvelle/",
        views.PieceComptableCreateView.as_view(),
        name="piece-create",
    ),
    path(
        "pieces/<uuid:pk>/",
        views.PieceComptableDetailView.as_view(),
        name="piece-detail",
    ),
    path(
        "pieces/<uuid:pk>/modifier/",
        views.PieceComptableUpdateView.as_view(),
        name="piece-update",
    ),
    path(
        "pieces/<uuid:pk>/valider/",
        views.piece_valider,
        name="piece-valider",
    ),
    path(
        "pieces/<uuid:pk>/ajouter-document/",
        views.piece_ajouter_document,
        name="piece-ajouter-document",
    ),
    path(
        "pieces/<uuid:pk>/extraire-ocr/",
        views.piece_extraire_ocr,
        name="piece-extraire-ocr",
    ),
    # Lettrage
    path("lettrages/", views.LettrageListView.as_view(), name="lettrage-list"),
    path(
        "lettrages/compte/<uuid:compte_pk>/",
        views.lettrage_compte,
        name="lettrage-compte",
    ),
    # Rapports
    path(
        "rapports/balance/<uuid:mandat_pk>/",
        views.balance_generale,
        name="balance-generale",
    ),
    path(
        "rapports/bilan/<uuid:mandat_pk>/",
        views.bilan,
        name="bilan",
    ),
    path(
        "rapports/compte-resultat/<uuid:mandat_pk>/",
        views.compte_resultat,
        name="compte-resultat",
    ),
    path(
        "rapports/cloture/<uuid:mandat_pk>/",
        views.cloture_exercice,
        name="cloture-exercice",
    ),
    # Exports
    path("comptes/export/csv/", views.export_comptes_csv, name="compte-export-csv"),
    path("comptes/export/excel/", views.export_comptes_excel, name="compte-export-excel"),
    path("ecritures/export/csv/", views.export_ecritures_csv, name="ecriture-export-csv"),
    path("ecritures/export/excel/", views.export_ecritures_excel, name="ecriture-export-excel"),

    # =========================================================================
    # IMPORT RELEVÉ BANCAIRE (camt.053)
    # =========================================================================
    path(
        "releves-bancaires/import/",
        views.ReleveBancaireImportView.as_view(),
        name="releve-bancaire-import",
    ),
    # =========================================================================
    # PAIEMENTS FOURNISSEURS (pain.001)
    # =========================================================================
    path(
        "paiements/",
        views.PaiementListView.as_view(),
        name="paiement-list",
    ),
    # =========================================================================
    # API AJAX (filtrage dynamique)
    # =========================================================================
    path(
        "api/mandat/<uuid:mandat_pk>/journaux/",
        views.api_journaux_par_mandat,
        name="api-journaux-mandat",
    ),
    path(
        "api/mandat/<uuid:mandat_pk>/dossiers/",
        views.api_dossiers_par_mandat,
        name="api-dossiers-mandat",
    ),
    path(
        "api/mandat/<uuid:mandat_pk>/comptes/",
        views.api_comptes_par_mandat,
        name="api-comptes-mandat",
    ),
    path(
        "api/types-pieces/",
        views.api_types_pieces,
        name="api-types-pieces",
    ),

    # =========================================================================
    # COMPTABILITÉ ANALYTIQUE
    # =========================================================================
    path("analytique/", views.AxeAnalytiqueListView.as_view(), name="axe-list"),
    path("analytique/sections/", views.SectionAnalytiqueListView.as_view(), name="section-list"),

    # =========================================================================
    # IMMOBILISATIONS
    # =========================================================================
    path("immobilisations/", views.ImmobilisationListView.as_view(), name="immobilisation-list"),
    path("immobilisations/nouveau/", views.ImmobilisationCreateView.as_view(), name="immobilisation-create"),
    path("immobilisations/<uuid:pk>/", views.ImmobilisationDetailView.as_view(), name="immobilisation-detail"),
    path("immobilisations/<uuid:pk>/modifier/", views.ImmobilisationUpdateView.as_view(), name="immobilisation-update"),

    # =========================================================================
    # RAPPROCHEMENT BANCAIRE
    # =========================================================================
    path("releves/", views.ReleveBancaireListView.as_view(), name="releve-list"),
    path("releves/<uuid:pk>/", views.ReleveBancaireDetailView.as_view(), name="releve-detail"),
]
