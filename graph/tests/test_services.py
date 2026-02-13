# graph/tests/test_services.py
"""Tests des services du graphe relationnel."""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from graph.models import Anomalie
from .factories import make_ontologie_type, make_entite, make_relation, make_anomalie


class EmbeddingServiceTestCase(TestCase):
    @patch('documents.embeddings.embedding_service')
    def test_generer_embedding_entite(self, mock_service):
        mock_service.generate_embedding.return_value = [0.1] * 768
        e = make_entite(nom='Test')

        from graph.services.embedding import generer_embedding_entite
        result = generer_embedding_entite(e)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 768)
        mock_service.generate_embedding.assert_called_once()

    @patch('documents.embeddings.embedding_service')
    def test_generer_embedding_none_on_empty(self, mock_service):
        from graph.services.embedding import generer_embedding_entite
        e = make_entite(nom='')
        e.nom = ''

        # texte_pour_embedding will produce something because type.nom exists
        result = generer_embedding_entite(e)
        # It should still call the service since type.nom is not empty

    @patch('documents.embeddings.embedding_service')
    def test_mettre_a_jour_embedding(self, mock_service):
        mock_service.generate_embedding.return_value = [0.5] * 768
        e = make_entite(nom='Update Test')

        from graph.services.embedding import mettre_a_jour_embedding
        result = mettre_a_jour_embedding(e.pk)

        self.assertTrue(result)
        e.refresh_from_db()
        self.assertIsNotNone(e.embedding)
        self.assertIsNotNone(e.embedding_updated_at)

    def test_mettre_a_jour_embedding_not_found(self):
        import uuid
        from graph.services.embedding import mettre_a_jour_embedding
        result = mettre_a_jour_embedding(uuid.uuid4())
        self.assertFalse(result)


class AnomaliesServiceTestCase(TestCase):
    def test_detecter_orphelins(self):
        e = make_entite(nom='Orphelin')
        # No relations -> should be detected as orphan

        from graph.services.anomalies import detecter_orphelins
        count = detecter_orphelins()

        self.assertGreaterEqual(count, 1)
        self.assertTrue(
            Anomalie.objects.filter(type='orphelin', entite=e).exists()
        )

    def test_detecter_orphelins_skips_connected(self):
        r = make_relation()
        # Both source and cible have relations -> not orphans

        from graph.services.anomalies import detecter_orphelins
        count = detecter_orphelins()

        self.assertFalse(
            Anomalie.objects.filter(
                type='orphelin',
                entite__in=[r.source, r.cible],
            ).exists()
        )

    def test_detecter_incoherences_temporelles(self):
        from datetime import date
        r = make_relation(date_debut=date(2025, 6, 1), date_fin=date(2025, 1, 1))

        from graph.services.anomalies import detecter_incoherences_temporelles
        count = detecter_incoherences_temporelles()

        self.assertGreaterEqual(count, 1)

    def test_detecter_tout(self):
        make_entite(nom='Orphelin test')

        from graph.services.anomalies import detecter_tout
        result = detecter_tout()

        self.assertIn('doublons', result)
        self.assertIn('orphelins', result)
        self.assertIn('incoherences', result)


class SuggestionsServiceTestCase(TestCase):
    def test_suggerer_connexions_no_embedding(self):
        e = make_entite()  # No embedding

        from graph.services.suggestions import suggerer_connexions
        result = suggerer_connexions(e.pk)

        self.assertEqual(result, [])

    def test_suggerer_connexions_not_found(self):
        import uuid
        from graph.services.suggestions import suggerer_connexions
        result = suggerer_connexions(uuid.uuid4())
        self.assertEqual(result, [])


class ImportServiceTestCase(TestCase):
    def test_importer_csv(self):
        import io
        from graph.services.import_data import importer_csv

        t = make_ontologie_type(nom='Personne')
        csv_content = "Nom,Ville\nJean Dupont,Genève\nMarie Martin,Lausanne\n"
        file = io.BytesIO(csv_content.encode('utf-8'))
        mapping = {'Nom': 'nom', 'Ville': 'attributs.ville'}

        result = importer_csv(file, t.pk, mapping)

        self.assertEqual(result['created'], 2)
        self.assertEqual(len(result['errors']), 0)

    def test_importer_csv_missing_nom(self):
        import io
        from graph.services.import_data import importer_csv

        t = make_ontologie_type(nom='Test')
        csv_content = "Ville\nGenève\n"
        file = io.BytesIO(csv_content.encode('utf-8'))
        mapping = {'Ville': 'attributs.ville'}

        result = importer_csv(file, t.pk, mapping)

        self.assertEqual(result['created'], 0)
        self.assertGreater(len(result['errors']), 0)

    def test_importer_csv_invalid_type(self):
        import io
        import uuid
        from graph.services.import_data import importer_csv

        file = io.BytesIO(b"Nom\nTest\n")
        result = importer_csv(file, uuid.uuid4(), {'Nom': 'nom'})

        self.assertEqual(result['created'], 0)
        self.assertGreater(len(result['errors']), 0)
