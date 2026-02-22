# analytics/tests.py
"""
Tests pour les vues des rapports de l'application analytics.

Ce module teste:
- L'API de preview des rapports
- La génération des rapports (PDF, Excel, CSV)
- Le filtrage par mandat
- Les différents types de rapports (Bilan, Compte de résultats, Trésorerie, etc.)
"""

import unittest
import json
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase, Client as TestClient, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model

from analytics.models import Rapport, TableauBord, Indicateur
from core.models import Mandat, Client, Adresse, Devise
from tva.models import RegimeFiscal

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class BaseAnalyticsTestCase(TestCase):
    """Classe de base pour les tests analytics avec fixtures communes."""

    @classmethod
    def setUpTestData(cls):
        """Créer les données de test partagées par toutes les méthodes de test."""
        # Créer un utilisateur de test (superuser pour passer BusinessPermissionMixin)
        cls.user = User.objects.create_superuser(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Créer les données de référence pour le support international
        cls.devise_chf = Devise.objects.get_or_create(
            code='CHF',
            defaults={
                'nom': 'Franc suisse',
                'symbole': 'Fr.',
                'decimales': 2,
            }
        )[0]
        cls.regime_ch = RegimeFiscal.objects.get_or_create(
            code='CH',
            defaults={
                'nom': 'Suisse',
                'pays': 'CH',
                'devise_defaut': cls.devise_chf,
                'taux_normal': Decimal('8.1'),
            }
        )[0]

        # Créer une adresse pour le client
        cls.adresse = Adresse.objects.create(
            rue='Rue de Test',
            numero='1',
            code_postal='1000',
            localite='Lausanne',
            canton='VD',
            pays='CH'
        )

        # Créer un client avec tous les champs requis
        cls.client_obj = Client.objects.create(
            raison_sociale='Test Client SA',
            forme_juridique='SA',
            ide_number='CHE-123.456.789',
            adresse_siege=cls.adresse,
            email='client@test.com',
            telephone='+41 21 123 45 67',
            date_creation=date(2020, 1, 1),
            date_debut_exercice=date(2025, 1, 1),
            date_fin_exercice=date(2025, 12, 31),
            statut='ACTIF',
            responsable=cls.user,
            created_by=cls.user
        )

        # Créer un mandat actif
        cls.mandat = Mandat.objects.create(
            numero='M-2025-001',
            client=cls.client_obj,
            statut='ACTIF',
            date_debut=date(2025, 1, 1),
            responsable=cls.user,
            created_by=cls.user,
            regime_fiscal=cls.regime_ch,
            devise=cls.devise_chf,
        )

        # Créer un second mandat pour tester le filtrage
        cls.mandat2 = Mandat.objects.create(
            numero='M-2025-002',
            client=cls.client_obj,
            statut='ACTIF',
            date_debut=date(2025, 1, 1),
            responsable=cls.user,
            created_by=cls.user,
            regime_fiscal=cls.regime_ch,
            devise=cls.devise_chf,
        )

    def setUp(self):
        """Initialiser le client de test et authentifier l'utilisateur."""
        self.test_client = TestClient()
        self.test_client.login(username='testuser', password='testpass123')


class RapportPreviewAPITestCase(BaseAnalyticsTestCase):
    """Tests pour l'API de preview des rapports."""

    def test_preview_api_requires_authentication(self):
        """L'API de preview doit requérir une authentification."""
        # Déconnecter
        self.test_client.logout()

        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        # Doit rediriger vers la page de login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_preview_api_bilan_without_mandat(self):
        """Test de la preview du bilan sans filtre mandat (données globales)."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Vérifier la structure de la réponse
        self.assertIn('type', data)
        self.assertEqual(data['type'], 'BILAN')
        self.assertIn('has_data', data)
        self.assertIn('summary', data)
        self.assertIn('chart_data', data)
        self.assertIn('chart_type', data)
        self.assertIn('warnings', data)

    def test_preview_api_bilan_with_mandat(self):
        """Test de la preview du bilan avec filtre mandat."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
            'mandat_id': str(self.mandat.id),
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'BILAN')
        self.assertIn('has_data', data)

    def test_preview_api_compte_resultats(self):
        """Test de la preview du compte de résultats."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'COMPTE_RESULTATS',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'COMPTE_RESULTATS')
        self.assertIn('summary', data)

    def test_preview_api_tresorerie(self):
        """Test de la preview de la trésorerie."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'TRESORERIE',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'TRESORERIE')

    def test_preview_api_tva(self):
        """Test de la preview TVA."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'TVA',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'TVA')

    def test_preview_api_evolution_ca(self):
        """Test de la preview évolution CA."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'EVOLUTION_CA',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'EVOLUTION_CA')
        # Ce type utilise un graphique area
        self.assertEqual(data['chart_type'], 'area')

    def test_preview_api_rentabilite(self):
        """Test de la preview rentabilité."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'RENTABILITE',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'RENTABILITE')

    def test_preview_api_salaires(self):
        """Test de la preview salaires."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'SALAIRES',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'SALAIRES')

    def test_preview_api_balance(self):
        """Test de la preview balance."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BALANCE',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'BALANCE')

    def test_preview_api_custom(self):
        """Test de la preview rapport personnalisé."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'CUSTOM',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['type'], 'CUSTOM')

    def test_preview_api_invalid_mandat(self):
        """Test avec un mandat invalide - doit retourner les données globales."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
            'mandat_id': '00000000-0000-0000-0000-000000000000',  # UUID invalide
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Doit quand même retourner une réponse valide
        self.assertIn('type', data)

    def test_preview_api_invalid_dates(self):
        """Test avec des dates invalides."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': 'invalid-date',
            'date_fin': '2025-12-31',
        })

        self.assertEqual(response.status_code, 200)
        # Doit quand même retourner une réponse (dates seront None)
        data = response.json()
        self.assertIn('type', data)

    def test_preview_api_mandat_parameter_alias(self):
        """Test que 'mandat' fonctionne aussi comme 'mandat_id'."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
            'mandat': str(self.mandat.id),  # Utiliser 'mandat' au lieu de 'mandat_id'
        })

        self.assertEqual(response.status_code, 200)


class RapportGenerationTestCase(BaseAnalyticsTestCase):
    """Tests pour la génération de rapports."""

    def test_rapport_generer_view_get(self):
        """Test d'accès à la page de génération de rapport (GET)."""
        url = reverse('analytics:rapport-generer')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/rapport_generer_v2.html')
        self.assertIn('form', response.context)
        self.assertIn('types_graphiques', response.context)
        self.assertIn('modeles_rapport', response.context)

    def test_rapport_generer_view_requires_auth(self):
        """La page de génération doit requérir une authentification."""
        self.test_client.logout()

        url = reverse('analytics:rapport-generer')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_rapport_generer_post_pdf(self):
        """Test de génération d'un rapport PDF."""
        url = reverse('analytics:rapport-generer')
        response = self.test_client.post(url, {
            'nom': 'Test Rapport Bilan',
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
            'format_fichier': 'PDF',
            'mandat': str(self.mandat.id),
        })

        # La réponse doit être un StreamingHttpResponse avec le fichier PDF
        # ou une redirection en cas d'erreur
        self.assertIn(response.status_code, [200, 302])

        if response.status_code == 200:
            # Vérifier que c'est bien un PDF
            self.assertEqual(response.get('Content-Type'), 'application/pdf')

    def test_rapport_generer_post_excel(self):
        """Test de génération d'un rapport Excel."""
        url = reverse('analytics:rapport-generer')
        response = self.test_client.post(url, {
            'nom': 'Test Rapport Excel',
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
            'format_fichier': 'EXCEL',
        })

        self.assertIn(response.status_code, [200, 302])

    def test_rapport_generer_post_csv(self):
        """Test de génération d'un rapport CSV."""
        url = reverse('analytics:rapport-generer')
        response = self.test_client.post(url, {
            'nom': 'Test Rapport CSV',
            'type_rapport': 'BALANCE',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
            'format_fichier': 'CSV',
        })

        self.assertIn(response.status_code, [200, 302])

    def test_rapport_generer_invalid_dates(self):
        """Test avec date_debut > date_fin (doit échouer)."""
        url = reverse('analytics:rapport-generer')
        response = self.test_client.post(url, {
            'nom': 'Test Rapport Invalid',
            'type_rapport': 'BILAN',
            'date_debut': '2025-12-31',  # Date début après date fin
            'date_fin': '2025-01-01',
            'format_fichier': 'PDF',
        })

        # Doit afficher le formulaire avec une erreur
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        # Le formulaire doit avoir des erreurs
        self.assertTrue(response.context['form'].errors)

    def test_rapport_generer_without_mandat(self):
        """Test de génération sans mandat (données globales)."""
        url = reverse('analytics:rapport-generer')
        response = self.test_client.post(url, {
            'nom': 'Test Rapport Global',
            'type_rapport': 'EVOLUTION_CA',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
            'format_fichier': 'PDF',
            # Pas de mandat spécifié
        })

        self.assertIn(response.status_code, [200, 302])


class RapportListViewTestCase(BaseAnalyticsTestCase):
    """Tests pour la liste des rapports."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Créer quelques rapports de test
        cls.rapport1 = Rapport.objects.create(
            nom='Rapport Test 1',
            type_rapport='BILAN',
            date_debut=date(2025, 1, 1),
            date_fin=date(2025, 12, 31),
            format_fichier='PDF',
            statut='TERMINE',
            genere_par=cls.user,
            mandat=cls.mandat,
        )
        cls.rapport2 = Rapport.objects.create(
            nom='Rapport Test 2',
            type_rapport='TVA',
            date_debut=date(2025, 1, 1),
            date_fin=date(2025, 3, 31),
            format_fichier='EXCEL',
            statut='TERMINE',
            genere_par=cls.user,
        )

    def test_rapport_list_view(self):
        """Test d'accès à la liste des rapports."""
        url = reverse('analytics:rapport-list')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/rapport_list.html')
        self.assertIn('rapports', response.context)

    def test_rapport_list_filter_by_type(self):
        """Test du filtrage par type de rapport."""
        url = reverse('analytics:rapport-list')
        response = self.test_client.get(url, {'type': 'BILAN'})

        self.assertEqual(response.status_code, 200)
        rapports = response.context['rapports']
        for rapport in rapports:
            self.assertEqual(rapport.type_rapport, 'BILAN')

    def test_rapport_list_filter_by_mandat(self):
        """Test du filtrage par mandat."""
        url = reverse('analytics:rapport-list')
        response = self.test_client.get(url, {'mandat': str(self.mandat.id)})

        self.assertEqual(response.status_code, 200)


class RapportDetailViewTestCase(BaseAnalyticsTestCase):
    """Tests pour le détail d'un rapport."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.rapport = Rapport.objects.create(
            nom='Rapport Détail Test',
            type_rapport='COMPTE_RESULTATS',
            date_debut=date(2025, 1, 1),
            date_fin=date(2025, 6, 30),
            format_fichier='PDF',
            statut='TERMINE',
            genere_par=cls.user,
            mandat=cls.mandat,
        )

    def test_rapport_detail_view(self):
        """Test d'accès au détail d'un rapport."""
        url = reverse('analytics:rapport-detail', kwargs={'pk': self.rapport.pk})
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/rapport_detail.html')
        self.assertEqual(response.context['rapport'], self.rapport)

    def test_rapport_detail_not_found(self):
        """Test d'accès à un rapport inexistant."""
        url = reverse('analytics:rapport-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'})
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 404)


class RapportRegenerateTestCase(BaseAnalyticsTestCase):
    """Tests pour la régénération de rapports."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.rapport = Rapport.objects.create(
            nom='Rapport à Régénérer',
            type_rapport='TRESORERIE',
            date_debut=date(2025, 1, 1),
            date_fin=date(2025, 12, 31),
            format_fichier='PDF',
            statut='ERREUR',
            genere_par=cls.user,
        )

    def test_rapport_regenerer_post(self):
        """Test de régénération d'un rapport."""
        url = reverse('analytics:rapport-regenerer', kwargs={'pk': self.rapport.pk})
        response = self.test_client.post(url)

        # Doit retourner le fichier ou rediriger
        self.assertIn(response.status_code, [200, 302])

    def test_rapport_regenerer_get_not_allowed(self):
        """La régénération ne doit accepter que POST."""
        url = reverse('analytics:rapport-regenerer', kwargs={'pk': self.rapport.pk})
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 405)  # Method Not Allowed


class TableauBordTestCase(BaseAnalyticsTestCase):
    """Tests pour les tableaux de bord."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tableau = TableauBord.objects.create(
            nom='Tableau Test',
            description='Description test',
            proprietaire=cls.user,
            visibilite='PRIVE',
            configuration={'widgets': []},
        )

    def test_tableau_bord_list_view(self):
        """Test d'accès à la liste des tableaux de bord."""
        url = reverse('analytics:tableau-bord-list')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/tableau_bord_list.html')

    def test_tableau_bord_detail_view(self):
        """Test d'accès au détail d'un tableau de bord."""
        url = reverse('analytics:tableau-bord-detail', kwargs={'pk': self.tableau.pk})
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/tableau_bord_detail.html')

    def test_tableau_bord_create_view(self):
        """Test de création d'un tableau de bord."""
        url = reverse('analytics:tableau-bord-create')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_tableau_bord_visibility_prive(self):
        """Un tableau privé ne doit être visible que par son propriétaire."""
        # Créer un autre utilisateur (superuser pour passer BusinessPermissionMixin)
        other_user = User.objects.create_superuser(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )

        # Se connecter avec l'autre utilisateur
        self.test_client.logout()
        self.test_client.login(username='otheruser', password='otherpass123')

        # La liste ne doit pas contenir le tableau privé de testuser
        url = reverse('analytics:tableau-bord-list')
        response = self.test_client.get(url)

        tableaux = response.context['tableaux']
        self.assertNotIn(self.tableau, tableaux)


class DashboardExecutifTestCase(BaseAnalyticsTestCase):
    """Tests pour le dashboard exécutif."""

    def test_dashboard_executif_view(self):
        """Test d'accès au dashboard exécutif."""
        url = reverse('analytics:dashboard-executif')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/dashboard_executif.html')

    def test_dashboard_executif_with_year_filter(self):
        """Test du dashboard avec filtre année."""
        url = reverse('analytics:dashboard-executif')
        response = self.test_client.get(url, {'annee': '2025'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['annee_selectionnee'], 2025)

    def test_dashboard_executif_with_mandat_filter(self):
        """Test du dashboard avec filtre mandat."""
        url = reverse('analytics:dashboard-executif')
        response = self.test_client.get(url, {'mandat': str(self.mandat.id)})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mandat_selectionne'], self.mandat)

    def test_dashboard_api_refresh(self):
        """Test de l'API de rafraîchissement du dashboard."""
        url = reverse('analytics:dashboard-api-refresh')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Vérifier la structure des données
        self.assertIn('kpis', data)
        self.assertIn('evolution_ca', data)
        self.assertIn('alertes', data)


class PreviewDataIntegrityTestCase(BaseAnalyticsTestCase):
    """Tests pour vérifier l'intégrité des données de preview."""

    def test_preview_summary_keys_bilan(self):
        """Vérifier que le summary du bilan contient les clés attendues."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        data = response.json()
        # Si des données existent, vérifier les clés du summary
        if data.get('has_data'):
            summary = data.get('summary', {})
            self.assertIn('Total Actif', summary)
            self.assertIn('Total Passif', summary)

    def test_preview_chart_type_consistency(self):
        """Vérifier que les types de graphiques sont cohérents avec le type de rapport."""
        expected_chart_types = {
            'BILAN': 'donut',
            'COMPTE_RESULTATS': 'bar',
            'TRESORERIE': 'bar',
            'TVA': 'donut',
            'EVOLUTION_CA': 'area',
            'RENTABILITE': 'bar',
            'SALAIRES': 'bar',  # Graphique en barres pour les salaires
            'BALANCE': 'bar',
        }

        url = reverse('analytics:rapport-preview-api')

        for type_rapport, expected_chart in expected_chart_types.items():
            response = self.test_client.get(url, {
                'type_rapport': type_rapport,
                'date_debut': '2025-01-01',
                'date_fin': '2025-12-31',
            })
            data = response.json()
            self.assertEqual(
                data.get('chart_type'),
                expected_chart,
                f"Type de graphique incorrect pour {type_rapport}"
            )

    def test_preview_decimal_serialization(self):
        """Vérifier que les Decimals sont correctement sérialisés en JSON."""
        url = reverse('analytics:rapport-preview-api')
        response = self.test_client.get(url, {
            'type_rapport': 'BILAN',
            'date_debut': '2025-01-01',
            'date_fin': '2025-12-31',
        })

        # Si la réponse est OK, les Decimals ont été correctement sérialisés
        self.assertEqual(response.status_code, 200)

        # Vérifier que le JSON est valide
        try:
            data = response.json()
            self.assertIsInstance(data, dict)
        except json.JSONDecodeError:
            self.fail("La réponse n'est pas un JSON valide")


class RapportEmailTestCase(BaseAnalyticsTestCase):
    """Tests pour l'envoi de rapports par email."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.rapport = Rapport.objects.create(
            nom='Rapport Email Test',
            type_rapport='BILAN',
            date_debut=date(2025, 1, 1),
            date_fin=date(2025, 12, 31),
            format_fichier='PDF',
            statut='TERMINE',
            genere_par=cls.user,
        )

    def test_rapport_envoyer_email_post_without_file(self):
        """L'envoi d'email doit échouer si le rapport n'a pas de fichier."""
        url = reverse('analytics:rapport-envoyer-email', kwargs={'pk': self.rapport.pk})
        response = self.test_client.post(url, {
            'emails': 'test@example.com',
        })

        # Doit rediriger avec un message d'erreur
        self.assertEqual(response.status_code, 302)

    def test_rapport_envoyer_email_get_not_allowed(self):
        """L'envoi d'email ne doit accepter que POST."""
        url = reverse('analytics:rapport-envoyer-email', kwargs={'pk': self.rapport.pk})
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 405)


class ExportDonneesTestCase(BaseAnalyticsTestCase):
    """Tests pour l'export de données."""

    def test_export_donnees_view(self):
        """Test d'accès à la page d'export de données."""
        url = reverse('analytics:export-donnees')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/export_form.html')

    def test_export_list_view(self):
        """Test d'accès à la liste des exports."""
        url = reverse('analytics:export-list')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/export_list.html')


class ComparaisonPeriodeTestCase(BaseAnalyticsTestCase):
    """Tests pour la comparaison de périodes."""

    def test_comparaison_periodes_view(self):
        """Test d'accès à la page de comparaison de périodes."""
        url = reverse('analytics:comparaison-create')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/comparaison_form.html')


class AlerteMetriqueTestCase(BaseAnalyticsTestCase):
    """Tests pour les alertes métriques."""

    def setUp(self):
        """Initialiser avec un superuser pour avoir toutes les permissions."""
        super().setUp()
        # Créer un superuser pour les tests d'alertes qui nécessitent des permissions
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        self.test_client.login(username='adminuser', password='adminpass123')

    def test_alerte_list_view(self):
        """Test d'accès à la liste des alertes."""
        url = reverse('analytics:alerte-list')
        response = self.test_client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/alerte_list.html')

    def test_alerte_list_filter_by_statut(self):
        """Test du filtrage des alertes par statut."""
        url = reverse('analytics:alerte-list')
        response = self.test_client.get(url, {'statut': 'ACTIVE'})

        self.assertEqual(response.status_code, 200)
