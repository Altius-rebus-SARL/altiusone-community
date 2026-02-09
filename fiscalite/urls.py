# fiscalite/urls.py
from django.urls import path
from . import views

app_name = "fiscalite"

urlpatterns = [
    # Déclarations fiscales
    path(
        "declarations/",
        views.DeclarationFiscaleListView.as_view(),
        name="declaration-list",
    ),
    path(
        "declarations/nouvelle/",
        views.DeclarationFiscaleCreateView.as_view(),
        name="declaration-create",
    ),
    path(
        "declarations/<uuid:pk>/",
        views.DeclarationFiscaleDetailView.as_view(),
        name="declaration-detail",
    ),
    path(
        "declarations/<uuid:pk>/valider/",
        views.declaration_valider,
        name="declaration-valider",
    ),
    path(
        "declarations/<uuid:pk>/deposer/",
        views.declaration_deposer,
        name="declaration-deposer",
    ),
    path(
        "declarations/<uuid:pk>/telecharger-declaration/",
        views.declaration_telecharger_fichier,
        name="declaration-telecharger-fichier",
    ),
    path(
        "declarations/<uuid:pk>/telecharger-taxation/",
        views.declaration_telecharger_taxation,
        name="declaration-telecharger-taxation",
    ),
    path(
        "declarations/<uuid:pk>/preview-pdf/",
        views.declaration_preview_fichier,
        name="declaration-preview-pdf",
    ),
    # Annexes
    path(
        "declarations/<uuid:declaration_pk>/annexes/nouvelle/",
        views.annexe_create,
        name="annexe-create",
    ),
    path(
        "annexes/<uuid:pk>/telecharger/",
        views.annexe_telecharger,
        name="annexe-telecharger",
    ),
    # Corrections
    path(
        "declarations/<uuid:declaration_pk>/corrections/nouvelle/",
        views.correction_create,
        name="correction-create",
    ),
    # Reports de pertes
    path(
        "reports-pertes/", views.ReportPerteListView.as_view(), name="report-perte-list"
    ),
    path(
        "reports-pertes/<uuid:pk>/",
        views.ReportPerteDetailView.as_view(),
        name="report-perte-detail",
    ),
    # Réclamations
    path(
        "reclamations/",
        views.ReclamationFiscaleListView.as_view(),
        name="reclamation-list",
    ),
    path(
        "declarations/<uuid:declaration_pk>/reclamations/nouvelle/",
        views.reclamation_create,
        name="reclamation-create",
    ),
    # Optimisations
    path(
        "optimisations/",
        views.OptimisationFiscaleListView.as_view(),
        name="optimisation-list",
    ),
    path(
        "optimisations/nouvelle/",
        views.OptimisationFiscaleCreateView.as_view(),
        name="optimisation-create",
    ),
    path(
        "optimisations/<uuid:pk>/",
        views.OptimisationFiscaleDetailView.as_view(),
        name="optimisation-detail",
    ),
    path(
        "optimisations/<uuid:pk>/changer-statut/",
        views.optimisation_changer_statut,
        name="optimisation-changer-statut",
    ),
    # Taux d'imposition
    path(
        "taux-imposition/",
        views.TauxImpositionListView.as_view(),
        name="taux-imposition-list",
    ),
    # Rapports
    path(
        "mandats/<uuid:mandat_pk>/rapport-annuel/",
        views.rapport_fiscal_annuel,
        name="rapport-annuel",
    ),
]

# # fiscalite/urls.py
# from django.urls import path
# from django.views.decorators.http import require_http_methods
# from . import views

# app_name = "fiscalite"

# urlpatterns = [
#     # Déclarations fiscales
#     path(
#         "declarations/",
#         views.DeclarationFiscaleListView.as_view(),
#         name="declaration-list",
#     ),
#     path(
#         "declarations/nouvelle/",
#         views.DeclarationFiscaleCreateView.as_view(),
#         name="declaration-create",
#     ),
#     path(
#         "declarations/<uuid:pk>/",
#         views.DeclarationFiscaleDetailView.as_view(),
#         name="declaration-detail",
#     ),
#     path(
#         "declarations/<uuid:pk>/valider/",
#         views.declaration_valider,
#         name="declaration-valider",
#     ),
#     path(
#         "declarations/<uuid:pk>/deposer/",
#         views.declaration_deposer,
#         name="declaration-deposer",
#     ),
#     # Annexes
#     path(
#         "declarations/<uuid:declaration_pk>/annexes/nouvelle/",
#         views.annexe_create,
#         name="annexe-create",
#     ),
#     # Corrections
#     path(
#         "declarations/<uuid:declaration_pk>/corrections/nouvelle/",
#         views.correction_create,
#         name="correction-create",
#     ),
#     # Reports de pertes
#     path(
#         "reports-pertes/", views.ReportPerteListView.as_view(), name="report-perte-list"
#     ),
#     path(
#         "reports-pertes/<uuid:pk>/",
#         views.ReportPerteDetailView.as_view(),
#         name="report-perte-detail",
#     ),
#     # Réclamations
#     path(
#         "reclamations/",
#         views.ReclamationFiscaleListView.as_view(),
#         name="reclamation-list",
#     ),
#     path(
#         "declarations/<uuid:declaration_pk>/reclamations/nouvelle/",
#         views.reclamation_create,
#         name="reclamation-create",
#     ),
#     # Optimisations fiscales
#     path(
#         "optimisations/",
#         views.OptimisationFiscaleListView.as_view(),
#         name="optimisation-list",
#     ),
#     path(
#         "optimisations/nouvelle/",
#         views.OptimisationFiscaleCreateView.as_view(),
#         name="optimisation-create",
#     ),
#     path(
#         "optimisations/<uuid:pk>/",
#         views.OptimisationFiscaleDetailView.as_view(),
#         name="optimisation-detail",
#     ),
#     path(
#         "optimisations/<uuid:pk>/statut/",
#         views.optimisation_changer_statut,
#         name="optimisation-changer-statut",
#     ),
#     # Taux d'imposition
#     path(
#         "taux-imposition/",
#         views.TauxImpositionListView.as_view(),
#         name="taux-imposition-list",
#     ),
#     # Rapports
#     path(
#         "rapports/<uuid:mandat_pk>/annuel/",
#         views.rapport_fiscal_annuel,
#         name="rapport-annuel",
#     ),
# ]
