# graph/tests/test_services.py
"""Tests des services du graphe relationnel."""
from unittest.mock import patch, MagicMock
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from graph.models import Anomalie, Entite, Relation
from .factories import (
    make_ontologie_type, make_entite, make_relation, make_anomalie,
    make_user, make_client, make_mandat,
)


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


class SyncServiceTestCase(TestCase):
    """Tests du service de synchronisation modèles Django → graphe."""

    def setUp(self):
        from graph.services.sync import invalidate_type_cache
        invalidate_type_cache()
        # Créer les types d'ontologie nécessaires
        self.type_entreprise = make_ontologie_type(
            categorie='entity', nom='Entreprise',
        )
        self.type_personne = make_ontologie_type(
            categorie='entity', nom='Personne',
        )
        self.type_mandat = make_ontologie_type(
            categorie='entity', nom='Mandat',
        )
        self.rel_client_de = make_ontologie_type(
            categorie='relation', nom='Client de',
            verbe='est client de', verbe_inverse='a pour client',
        )
        self.rel_responsable_de = make_ontologie_type(
            categorie='relation', nom='Responsable de',
            verbe='est responsable de', verbe_inverse='a pour responsable',
        )

    def tearDown(self):
        from graph.services.sync import invalidate_type_cache
        invalidate_type_cache()

    def test_sync_instance_creates_entite(self):
        """Crée un Client, vérifie qu'une Entite est créée."""
        from graph.services.sync import sync_instance

        client = make_client()
        entite = sync_instance(client)

        self.assertIsNotNone(entite)
        self.assertEqual(entite.nom, client.raison_sociale)
        self.assertEqual(entite.type, self.type_entreprise)
        self.assertEqual(entite.source, 'systeme')
        self.assertEqual(entite.confiance, 1.0)
        # Vérifie le GenericFK
        ct = ContentType.objects.get_for_model(client)
        self.assertEqual(entite.content_type, ct)
        self.assertEqual(entite.object_id, client.pk)
        # Vérifie les attributs
        self.assertIn('ide_number', entite.attributs)
        self.assertEqual(entite.attributs['ide_number'], client.ide_number)

    def test_sync_instance_updates_entite(self):
        """Modifie le Client, vérifie que l'Entite est mise à jour."""
        from graph.services.sync import sync_instance

        client = make_client()
        entite1 = sync_instance(client)
        pk1 = entite1.pk

        # Modifier le client
        client.raison_sociale = 'Nouveau Nom SA'
        client.save()
        entite2 = sync_instance(client)

        self.assertEqual(entite2.pk, pk1)  # Même entité
        self.assertEqual(entite2.nom, 'Nouveau Nom SA')

    def test_sync_instance_returns_none_for_unmapped_model(self):
        """Un modèle non mappé retourne None."""
        from graph.services.sync import sync_instance

        # OntologieType n'est pas dans MODEL_GRAPH_CONFIG
        entite = sync_instance(self.type_entreprise)
        self.assertIsNone(entite)

    def test_sync_relations_creates_relation(self):
        """Crée un Mandat (FK→Client), vérifie Relation créée."""
        from graph.services.sync import sync_instance, sync_relations

        responsable = make_user()
        client = make_client(responsable=responsable)
        mandat = make_mandat(client=client, responsable=responsable)

        # Syncer les entités d'abord
        sync_instance(responsable)
        sync_instance(client)
        sync_instance(mandat)

        # Syncer les relations du mandat
        sync_relations(mandat)

        # Vérifier la relation Mandat → Client (Client de)
        ct_mandat = ContentType.objects.get_for_model(mandat)
        ct_client = ContentType.objects.get_for_model(client)
        mandat_entite = Entite.objects.get(content_type=ct_mandat, object_id=mandat.pk)
        client_entite = Entite.objects.get(content_type=ct_client, object_id=client.pk)

        self.assertTrue(
            Relation.objects.filter(
                source=mandat_entite,
                cible=client_entite,
                type=self.rel_client_de,
            ).exists()
        )

        # Vérifier la relation Mandat → User (Responsable de)
        ct_user = ContentType.objects.get_for_model(responsable)
        user_entite = Entite.objects.get(content_type=ct_user, object_id=responsable.pk)

        self.assertTrue(
            Relation.objects.filter(
                source=mandat_entite,
                cible=user_entite,
                type=self.rel_responsable_de,
            ).exists()
        )

    def test_delete_instance_deactivates(self):
        """Supprime, vérifie is_active=False."""
        from graph.services.sync import sync_instance, delete_instance

        client = make_client()
        entite = sync_instance(client)
        self.assertTrue(entite.is_active)

        delete_instance(client)

        entite.refresh_from_db()
        self.assertFalse(entite.is_active)
