# comptabilite/urls.py
from django.urls import path
from . import views

app_name = "comptabilite"

urlpatterns = [
    # Plans comptables
    path("plans/", views.PlanComptableListView.as_view(), name="plan-list"),
    path("plans/nouveau/", views.PlanComptableCreateView.as_view(), name="plan-create"),
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
        "pieces/<uuid:pk>/",
        views.PieceComptableDetailView.as_view(),
        name="piece-detail",
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
]
