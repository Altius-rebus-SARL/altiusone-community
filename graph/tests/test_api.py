# graph/tests/test_api.py
"""Tests des API endpoints du graphe relationnel."""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status
from graph.models import OntologieType, Entite, Anomalie
from .factories import (
    make_ontologie_type, make_entite, make_relation, make_anomalie,
)


class GraphAPITestMixin:
    """Mixin pour les tests API avec authentification."""

    def setUp(self):
        from core.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


@override_settings(SECURE_SSL_REDIRECT=False)
class OntologieTypeAPITestCase(GraphAPITestMixin, TestCase):
    def test_list_types(self):
        make_ontologie_type(nom='Personne')
        make_ontologie_type(nom='Entreprise')

        response = self.client.get('/api/v1/graph-types/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_create_type(self):
        data = {
            'categorie': 'entity',
            'nom': 'TestType',
            'icone': 'ph-user',
            'couleur': '#ff0000',
        }
        response = self.client.post('/api/v1/graph-types/', data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertEqual(response.data['nom'], 'TestType')

    def test_update_type(self):
        t = make_ontologie_type(nom='Old')
        response = self.client.patch(
            f'/api/v1/graph-types/{t.pk}/',
            {'nom': 'New'},
            format='json',
        )
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        t.refresh_from_db()
        self.assertEqual(t.nom, 'New')


@override_settings(SECURE_SSL_REDIRECT=False)
class EntiteAPITestCase(GraphAPITestMixin, TestCase):
    def test_list_entites(self):
        make_entite(nom='E1')
        make_entite(nom='E2')

        response = self.client.get('/api/v1/graph-entites/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_create_entite(self):
        t = make_ontologie_type(categorie='entity')
        data = {
            'type': str(t.pk),
            'nom': 'Nouvelle Entité',
            'source': 'manuelle',
            'confiance': 0.9,
        }
        response = self.client.post('/api/v1/graph-entites/', data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)

    def test_detail_entite(self):
        e = make_entite(nom='Detail Test')
        response = self.client.get(f'/api/v1/graph-entites/{e.pk}/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['nom'], 'Detail Test')

    def test_search_entites(self):
        make_entite(nom='Acme Corp')
        response = self.client.get('/api/v1/graph-entites/?search=Acme')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_filter_by_type(self):
        t1 = make_ontologie_type(categorie='entity', nom='TypeA')
        t2 = make_ontologie_type(categorie='entity', nom='TypeB')
        make_entite(nom='E1', type_obj=t1)
        make_entite(nom='E2', type_obj=t2)

        response = self.client.get(f'/api/v1/graph-entites/?type={t1.pk}')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        for r in response.data['results']:
            self.assertEqual(str(r['type']), str(t1.pk))


@override_settings(SECURE_SSL_REDIRECT=False)
class RelationAPITestCase(GraphAPITestMixin, TestCase):
    def test_list_relations(self):
        make_relation()
        response = self.client.get('/api/v1/graph-relations/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

    def test_create_relation(self):
        rel_type = make_ontologie_type(categorie='relation')
        source = make_entite()
        cible = make_entite(type_obj=source.type)

        data = {
            'type': str(rel_type.pk),
            'source': str(source.pk),
            'cible': str(cible.pk),
            'poids': 1.0,
            'confiance': 0.8,
        }
        response = self.client.post('/api/v1/graph-relations/', data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)


@override_settings(SECURE_SSL_REDIRECT=False)
class AnomalieAPITestCase(GraphAPITestMixin, TestCase):
    def test_list_anomalies(self):
        make_anomalie()
        response = self.client.get('/api/v1/graph-anomalies/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

    def test_traiter_anomalie(self):
        a = make_anomalie()
        response = self.client.post(
            f'/api/v1/graph-anomalies/{a.pk}/traiter/',
            {'statut': 'confirme', 'commentaire': 'Confirmed'},
            format='json',
        )
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        a.refresh_from_db()
        self.assertEqual(a.statut, 'confirme')

    def test_cannot_create_anomalie_via_api(self):
        """AnomalieViewSet is ReadOnly."""
        data = {'type': 'doublon', 'titre': 'Test'}
        response = self.client.post('/api/v1/graph-anomalies/', data, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_405_METHOD_NOT_ALLOWED)


@override_settings(SECURE_SSL_REDIRECT=False)
class GraphStatsAPITestCase(GraphAPITestMixin, TestCase):
    def test_stats(self):
        make_entite()
        make_relation()

        response = self.client.get('/api/v1/graph-analytics/stats/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertIn('entites', response.data)
        self.assertIn('relations', response.data)
        self.assertIn('anomalies_ouvertes', response.data)


@override_settings(SECURE_SSL_REDIRECT=False)
class UnauthenticatedAPITestCase(TestCase):
    def test_unauthenticated_access_denied(self):
        client = APIClient()
        response = client.get('/api/v1/graph-entites/')
        self.assertIn(
            response.status_code,
            [http_status.HTTP_401_UNAUTHORIZED, http_status.HTTP_403_FORBIDDEN],
        )
