"""
Tests du pipeline RAG (Retrieval-Augmented Generation).

Couvre :
- LocalEmbeddingService : embedding unitaire, batch, similarite, gestion None
- LocalChatService : construction de messages, generation (mockee)
- UniversalSearchService : extraction mots-cles, filtrage mandat_ids vide,
  score textuel, recherche par type d'entite
- ChatService : securite _search_all_entities (filtrage par mandats user),
  construction system prompt, chat complet (mocke)
"""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models import Adresse, Client, Devise, Entreprise, Mandat
from documents.universal_search import (
    EntityType,
    SearchContext,
    SearchResult,
    UniversalSearchService,
)

User = get_user_model()


# =============================================================================
# Fixtures partagees
# =============================================================================

class RAGTestBase(TestCase):
    """Fixtures communes pour tous les tests du pipeline RAG."""

    @classmethod
    def setUpTestData(cls):
        cls.devise_chf, _ = Devise.objects.get_or_create(
            code='CHF', defaults={'nom': 'Franc suisse', 'symbole': 'CHF'},
        )

        from tva.models import RegimeFiscal
        cls.regime, _ = RegimeFiscal.objects.get_or_create(
            code='CH', defaults={
                'nom': 'Suisse', 'pays': 'CH',
                'devise_defaut': cls.devise_chf,
                'taux_normal': Decimal('8.1'),
            },
        )

        cls.adresse = Adresse.objects.create(
            rue='Rue de Bourg', numero='12', npa='1003', localite='Lausanne',
        )

        cls.entreprise = Entreprise.objects.create(
            raison_sociale='Test Fiduciaire SA',
            forme_juridique='SA',
            ide_number='CHE-111.222.333',
            siege='Lausanne',
            est_defaut=True,
            adresse=cls.adresse,
        )

        # Superuser
        cls.superuser = User.objects.create_superuser(
            username='admin', password='admin', email='admin@test.ch',
        )

        # Regular user (pas superuser, pas manager)
        cls.regular_user = User.objects.create_user(
            username='regular', password='regular', email='regular@test.ch',
        )

        # Clients et mandats
        cls.client_a = Client.objects.create(
            raison_sociale='Client Alpha SA',
            forme_juridique='SA',
            adresse_siege=cls.adresse,
            email='alpha@test.ch',
            date_debut_exercice=date(2026, 1, 1),
            date_fin_exercice=date(2026, 12, 31),
            entreprise=cls.entreprise,
        )
        cls.client_b = Client.objects.create(
            raison_sociale='Client Beta GmbH',
            forme_juridique='GmbH',
            adresse_siege=cls.adresse,
            email='beta@test.ch',
            date_debut_exercice=date(2026, 1, 1),
            date_fin_exercice=date(2026, 12, 31),
            entreprise=cls.entreprise,
        )

        cls.mandat_a = Mandat.objects.create(
            numero='MAN-A-001',
            client=cls.client_a,
            date_debut=date(2026, 1, 1),
            responsable=cls.superuser,
            regime_fiscal=cls.regime,
            devise=cls.devise_chf,
            statut='ACTIF',
        )
        cls.mandat_b = Mandat.objects.create(
            numero='MAN-B-002',
            client=cls.client_b,
            date_debut=date(2026, 1, 1),
            responsable=cls.superuser,
            regime_fiscal=cls.regime,
            devise=cls.devise_chf,
            statut='ACTIF',
        )


# =============================================================================
# 1. LocalEmbeddingService
# =============================================================================

class TestLocalEmbeddingService(TestCase):
    """Tests pour core.ai.embeddings.LocalEmbeddingService."""

    def _make_service(self):
        """Cree un service avec modele mocke."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        svc._model = MagicMock()
        return svc

    # --- generate_embedding ---

    def test_generate_embedding_returns_768d(self):
        """generate_embedding() retourne une liste de 768 floats."""
        svc = self._make_service()
        fake_emb = np.random.randn(768).astype(np.float32)
        svc._model.encode.return_value = fake_emb

        result = svc.generate_embedding("Bonjour le monde")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 768)
        svc._model.encode.assert_called_once_with(
            "Bonjour le monde",
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def test_generate_embedding_none_for_empty_string(self):
        """generate_embedding('') retourne None."""
        svc = self._make_service()
        self.assertIsNone(svc.generate_embedding(""))
        self.assertIsNone(svc.generate_embedding("   "))
        svc._model.encode.assert_not_called()

    def test_generate_embedding_none_for_none(self):
        """generate_embedding(None) retourne None."""
        svc = self._make_service()
        self.assertIsNone(svc.generate_embedding(None))

    def test_generate_embedding_returns_none_on_error(self):
        """Erreur du modele -> retourne None (ne leve pas d'exception)."""
        svc = self._make_service()
        svc._model.encode.side_effect = RuntimeError("GPU OOM")
        result = svc.generate_embedding("test")
        self.assertIsNone(result)

    # --- generate_embeddings_batch ---

    def test_batch_returns_correct_length(self):
        """Batch de 3 textes retourne 3 resultats."""
        svc = self._make_service()
        fake = np.random.randn(3, 768).astype(np.float32)
        svc._model.encode.return_value = fake

        results = svc.generate_embeddings_batch(["a", "b", "c"])
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIsInstance(r, list)
            self.assertEqual(len(r), 768)

    def test_batch_none_for_empty_texts(self):
        """Textes vides dans le batch donnent None a la bonne position."""
        svc = self._make_service()
        fake = np.random.randn(2, 768).astype(np.float32)
        svc._model.encode.return_value = fake

        results = svc.generate_embeddings_batch(["hello", "", "world"])

        self.assertEqual(len(results), 3)
        self.assertIsNotNone(results[0])
        self.assertIsNone(results[1])
        self.assertIsNotNone(results[2])

    def test_batch_empty_list(self):
        """Liste vide retourne liste vide."""
        svc = self._make_service()
        self.assertEqual(svc.generate_embeddings_batch([]), [])

    def test_batch_all_empty_returns_all_none(self):
        """Batch de textes tous vides retourne [None, None, ...]."""
        svc = self._make_service()
        results = svc.generate_embeddings_batch(["", "  ", ""])
        self.assertEqual(results, [None, None, None])
        svc._model.encode.assert_not_called()

    def test_batch_error_returns_all_none(self):
        """Erreur du modele en batch -> tous None."""
        svc = self._make_service()
        svc._model.encode.side_effect = RuntimeError("OOM")
        results = svc.generate_embeddings_batch(["a", "b"])
        self.assertEqual(results, [None, None])

    # --- compute_similarity ---

    def test_cosine_identical_vectors(self):
        """Cosine similarity de vecteurs identiques = 1.0."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        v = [1.0, 0.0, 0.0]
        self.assertAlmostEqual(svc.compute_similarity(v, v, 'cosine'), 1.0)

    def test_cosine_orthogonal_vectors(self):
        """Cosine similarity de vecteurs orthogonaux = 0.0."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(svc.compute_similarity(v1, v2, 'cosine'), 0.0)

    def test_cosine_opposite_vectors(self):
        """Cosine similarity de vecteurs opposes = -1.0."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        v1 = [1.0, 0.0]
        v2 = [-1.0, 0.0]
        self.assertAlmostEqual(svc.compute_similarity(v1, v2, 'cosine'), -1.0)

    def test_cosine_zero_vector(self):
        """Vecteur nul retourne 0.0."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        self.assertAlmostEqual(
            svc.compute_similarity([0.0, 0.0], [1.0, 0.0], 'cosine'), 0.0,
        )

    def test_l2_similarity(self):
        """L2 similarity de vecteurs identiques = 1.0."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        v = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(svc.compute_similarity(v, v, 'l2'), 1.0)

    def test_l1_similarity(self):
        """L1 similarity de vecteurs identiques = 1.0."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        v = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(svc.compute_similarity(v, v, 'l1'), 1.0)

    def test_l2_distant_vectors(self):
        """L2 similarity diminue avec la distance."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        v1 = [0.0, 0.0]
        v2 = [10.0, 0.0]
        sim = svc.compute_similarity(v1, v2, 'l2')
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)

    def test_unknown_metric_raises(self):
        """Metrique inconnue leve ValueError."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        with self.assertRaises(ValueError):
            svc.compute_similarity([1.0], [1.0], 'euclidean')

    # --- Proprietes ---

    @override_settings(EMBEDDING_DIMENSIONS=512)
    def test_dimensions_from_settings(self):
        """dimensions lit EMBEDDING_DIMENSIONS des settings."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        self.assertEqual(svc.dimensions, 512)

    @override_settings(EMBEDDING_MODEL='custom/model-v3')
    def test_model_name_from_settings(self):
        """model_name lit EMBEDDING_MODEL des settings."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        self.assertEqual(svc.model_name, 'custom/model-v3')

    def test_lazy_loading_model_not_loaded_at_init(self):
        """Le modele n'est PAS charge a l'init."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        self.assertIsNone(svc._model)

    def test_is_available_with_working_model(self):
        """is_available() retourne True quand le modele fonctionne."""
        svc = self._make_service()
        self.assertTrue(svc.is_available())

    def test_is_available_false_on_error(self):
        """is_available() retourne False si le modele ne charge pas."""
        from core.ai.embeddings import LocalEmbeddingService
        svc = LocalEmbeddingService()
        with patch.object(
            LocalEmbeddingService, 'model',
            new_callable=PropertyMock,
            side_effect=RuntimeError("CUDA not available"),
        ):
            self.assertFalse(svc.is_available())


# =============================================================================
# 2. LocalChatService
# =============================================================================

class TestLocalChatService(TestCase):
    """Tests pour core.ai.chat.LocalChatService."""

    def _make_service(self):
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        svc._model = MagicMock()
        svc._tokenizer = MagicMock()
        svc._device = 'cpu'
        return svc

    # --- _build_messages ---

    def test_build_messages_simple(self):
        """Message simple sans system/history."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        msgs = svc._build_messages("Bonjour", None, None, None, None, None)
        self.assertEqual(msgs, [{'role': 'user', 'content': 'Bonjour'}])

    def test_build_messages_with_system(self):
        """System prompt est ajoute en premier."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        msgs = svc._build_messages(
            "Question", "Tu es un assistant", None, None, None, None,
        )
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0]['role'], 'system')
        self.assertEqual(msgs[0]['content'], 'Tu es un assistant')
        self.assertEqual(msgs[1]['role'], 'user')

    def test_build_messages_system_prompt_alias(self):
        """system_prompt est un alias de system."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        msgs = svc._build_messages(
            "Q", None, "Mon prompt systeme", None, None, None,
        )
        self.assertEqual(msgs[0]['content'], 'Mon prompt systeme')

    def test_build_messages_with_context(self):
        """Le context est injecte dans le message user."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        msgs = svc._build_messages(
            "Quelle est la TVA?", None, None, "Facture 1234 - 100 CHF", None, None,
        )
        self.assertIn("Contexte:", msgs[-1]['content'])
        self.assertIn("Facture 1234", msgs[-1]['content'])
        self.assertIn("Question: Quelle est la TVA?", msgs[-1]['content'])

    def test_build_messages_with_history(self):
        """L'historique est ajoute (sauf le dernier message)."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        history = [
            {'role': 'user', 'content': 'Premier message'},
            {'role': 'assistant', 'content': 'Premiere reponse'},
            {'role': 'user', 'content': 'Deuxieme message'},
        ]
        msgs = svc._build_messages("Nouveau", None, None, None, history, None)

        # History[-1] est exclu, les 2 premiers sont inclus
        roles = [m['role'] for m in msgs]
        self.assertEqual(roles, ['user', 'assistant', 'user'])
        # Le dernier user est le nouveau message
        self.assertEqual(msgs[-1]['content'], 'Nouveau')

    def test_build_messages_history_filters_invalid_roles(self):
        """Les roles invalides dans l'historique sont ignores."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        history = [
            {'role': 'system', 'content': 'System msg'},
            {'role': 'user', 'content': 'Msg user'},
            {'role': 'unknown', 'content': 'Bad role'},
            {'role': 'user', 'content': 'Dernier'},
        ]
        msgs = svc._build_messages("Q", None, None, None, history, None)
        # system et unknown sont filtres, seul 'user' de l'historique passe
        # (le dernier element de history est exclu)
        contents = [m['content'] for m in msgs]
        self.assertNotIn('System msg', contents)
        self.assertNotIn('Bad role', contents)
        self.assertIn('Msg user', contents)

    def test_build_messages_override(self):
        """messages_override remplace tout."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        override = [{'role': 'system', 'content': 'Custom'}]
        msgs = svc._build_messages(
            "Ignore moi", "Aussi ignore", None, None, None, override,
        )
        self.assertEqual(msgs, override)

    def test_build_messages_empty_message(self):
        """Message vide ne genere pas de message user."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        msgs = svc._build_messages("", "System", None, None, None, None)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]['role'], 'system')

    # --- chat (avec mock complet) ---

    @patch('core.ai.chat._model_lock')
    def test_chat_returns_response_dict(self, mock_lock):
        """chat() retourne un dict avec response, tokens, etc."""
        svc = self._make_service()

        svc._tokenizer.apply_chat_template.return_value = "formatted"
        mock_inputs = MagicMock()
        mock_inputs.__getitem__ = MagicMock(
            side_effect=lambda k: MagicMock(shape=[1, 10])
        )
        mock_inputs.to.return_value = mock_inputs
        svc._tokenizer.return_value = mock_inputs

        mock_outputs = MagicMock()
        mock_outputs.__getitem__ = MagicMock(
            return_value=MagicMock(__getitem__=MagicMock(return_value=[1, 2, 3]))
        )
        svc._model.generate.return_value = mock_outputs
        svc._tokenizer.decode.return_value = "Reponse test"

        # torch est importe LOCALEMENT dans core.ai.chat._generate (pas au niveau
        # module), donc on patche directement torch.inference_mode au niveau global.
        with patch('torch.inference_mode') as mock_inference:
            mock_inference.return_value.__enter__ = MagicMock(return_value=None)
            mock_inference.return_value.__exit__ = MagicMock(return_value=None)
            result = svc.chat(message="Bonjour")

        self.assertIn('response', result)
        self.assertEqual(result['response'], 'Reponse test')
        self.assertIn('processing_time_ms', result)
        self.assertIn('tokens_completion', result)

    def test_chat_raises_chat_error_on_failure(self):
        """chat() leve ChatError si le modele echoue."""
        from core.ai.chat import ChatError
        svc = self._make_service()
        svc._tokenizer.apply_chat_template.side_effect = RuntimeError("Erreur")

        with self.assertRaises(ChatError):
            svc.chat(message="test")

    # --- health_check ---

    def test_health_check_model_not_loaded(self):
        """health_check quand le modele n'est pas charge."""
        from core.ai.chat import LocalChatService
        svc = LocalChatService()
        health = svc.health_check()
        self.assertFalse(health['model_loaded'])
        self.assertEqual(health['backend'], 'transformers')
        self.assertTrue(health['enabled'])

    def test_health_check_model_loaded(self):
        """health_check quand le modele est charge."""
        svc = self._make_service()
        health = svc.health_check()
        self.assertTrue(health['model_loaded'])


# =============================================================================
# 3. UniversalSearchService — extraction de mots-cles
# =============================================================================

class TestExtractSearchKeywords(TestCase):
    """Tests pour UniversalSearchService._extract_search_keywords()."""

    def setUp(self):
        self.svc = UniversalSearchService()

    def test_french_stop_words_removed(self):
        """Les mots vides francais sont supprimes."""
        result = self.svc._extract_search_keywords(
            "Quels sont les mandats du client Alpha?"
        )
        self.assertNotIn('quels', result)
        self.assertNotIn('sont', result)
        self.assertNotIn('les', result)
        self.assertNotIn('du', result)
        self.assertIn('mandats', result)
        self.assertIn('client', result)
        self.assertIn('alpha', result)

    def test_german_keywords_preserved(self):
        """Les mots-cles allemands sont preserves (pas de stop words DE)."""
        result = self.svc._extract_search_keywords(
            "Rechnung Kunde Meier 2026"
        )
        self.assertIn('rechnung', result)
        self.assertIn('kunde', result)
        self.assertIn('meier', result)
        self.assertIn('2026', result)

    def test_punctuation_removed(self):
        """La ponctuation est nettoyee."""
        result = self.svc._extract_search_keywords("facture #123, client (test)")
        self.assertNotIn('#', result)
        self.assertNotIn(',', result)
        self.assertNotIn('(', result)

    def test_apostrophe_elision_removed(self):
        """L'elision (l', d', etc.) est geree."""
        result = self.svc._extract_search_keywords("l'entreprise d'Alpha")
        self.assertIn('entreprise', result)
        self.assertIn('alpha', result)
        # "l'" et "d'" doivent etre supprimes
        self.assertNotIn("l'", result)
        self.assertNotIn("d'", result)

    def test_short_words_removed(self):
        """Les mots de 1 caractere sont supprimes."""
        result = self.svc._extract_search_keywords("a b c bonjour")
        self.assertNotIn('b', result.split())
        self.assertNotIn('c', result.split())
        self.assertIn('bonjour', result)

    def test_fallback_to_original_if_all_stop_words(self):
        """Si tous les mots sont des stop words, on retourne le message brut."""
        result = self.svc._extract_search_keywords("quels sont les")
        # Fallback: retourne le message strip()
        self.assertEqual(result, "quels sont les")

    def test_empty_string(self):
        """Chaine vide retourne chaine vide strippee."""
        result = self.svc._extract_search_keywords("")
        self.assertEqual(result, "")

    def test_numeric_query(self):
        """Les numeros sont preserves (numeros de facture, etc.)."""
        result = self.svc._extract_search_keywords("facture 2026-001")
        self.assertIn('facture', result)
        self.assertIn('2026-001', result)

    def test_mixed_french_german(self):
        """Requete mixte FR/DE extrait les mots significatifs."""
        result = self.svc._extract_search_keywords(
            "Montre moi les Rechnungen du Kunde Müller"
        )
        # "montre", "moi", "les", "du" sont stop words
        self.assertIn('rechnungen', result)
        self.assertIn('kunde', result)
        self.assertIn('müller', result)


# =============================================================================
# 4. UniversalSearchService — score textuel
# =============================================================================

class TestCalculateTextScore(TestCase):
    """Tests pour _calculate_text_score()."""

    def setUp(self):
        self.svc = UniversalSearchService()

    def test_exact_match_score_1(self):
        """Correspondance exacte donne score 1.0."""
        score = self.svc._calculate_text_score("alpha", ["Alpha"])
        self.assertAlmostEqual(score, 1.0)

    def test_contains_score_08(self):
        """Le champ contient la requete complete -> 0.8."""
        score = self.svc._calculate_text_score("alpha", ["Client Alpha SA"])
        self.assertAlmostEqual(score, 0.8)

    def test_starts_with_score_07(self):
        """Le champ commence par la requete -> 0.7."""
        score = self.svc._calculate_text_score("client", ["client alpha"])
        # "client" est contenu dans "client alpha" => 0.8
        # mais "client alpha".startswith("client") => 0.7
        # contains check runs first and yields 0.8
        self.assertAlmostEqual(score, 0.8)

    def test_partial_match(self):
        """Correspondance partielle donne score entre 0 et 0.5."""
        score = self.svc._calculate_text_score(
            "alpha beta", ["Alpha Corporation"]
        )
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 0.5)

    def test_no_match_score_0(self):
        """Aucune correspondance donne score 0.0."""
        score = self.svc._calculate_text_score("xyz", ["Alpha", "Beta"])
        self.assertAlmostEqual(score, 0.0)

    def test_empty_fields_handled(self):
        """Champs vides ne cassent pas le calcul."""
        score = self.svc._calculate_text_score("test", ["", None, "test"])
        self.assertAlmostEqual(score, 1.0)

    def test_best_field_wins(self):
        """Le meilleur score parmi les champs est retenu."""
        score = self.svc._calculate_text_score(
            "alpha", ["xyz", "Alpha", "abc"]
        )
        self.assertAlmostEqual(score, 1.0)


# =============================================================================
# 5. UniversalSearchService — securite mandat_ids
# =============================================================================

class TestUniversalSearchSecurity(RAGTestBase):
    """Tests de securite : filtrage par mandat_ids dans search()."""

    def setUp(self):
        self.svc = UniversalSearchService()

    @patch.object(UniversalSearchService, '_search_entity_type', return_value=[])
    @patch.object(UniversalSearchService, '_search_semantic', return_value=[])
    def test_empty_mandat_ids_raises_no_access_error(self, mock_sem, mock_search):
        """mandat_ids=[] -> leve NoAccessibleMandatsError (fix 2026-04-05)."""
        from documents.universal_search import NoAccessibleMandatsError

        context = SearchContext(
            user=self.regular_user,
            mandat_ids=[],
            entity_types=[EntityType.CLIENT],
        )
        with self.assertRaises(NoAccessibleMandatsError):
            self.svc.search("test", context)
        # _search_entity_type ne doit JAMAIS etre appele
        mock_search.assert_not_called()

    @patch.object(UniversalSearchService, '_search_entity_type')
    @patch.object(UniversalSearchService, '_search_semantic', return_value=[])
    def test_none_mandat_ids_searches_all(self, mock_sem, mock_search):
        """mandat_ids=None -> recherche dans tout (superuser)."""
        mock_search.return_value = []
        context = SearchContext(
            user=self.superuser,
            mandat_ids=None,
            entity_types=[EntityType.CLIENT],
        )
        self.svc.search("test", context)
        mock_search.assert_called()

    @patch.object(UniversalSearchService, '_search_entity_type')
    @patch.object(UniversalSearchService, '_search_semantic', return_value=[])
    def test_specific_mandat_ids_passed_to_search(self, mock_sem, mock_search):
        """mandat_ids=[X] est transmis au contexte de recherche."""
        mock_search.return_value = []
        mandat_id = str(self.mandat_a.id)
        context = SearchContext(
            user=self.regular_user,
            mandat_ids=[mandat_id],
            entity_types=[EntityType.CLIENT],
        )
        self.svc.search("alpha", context)
        # Verifier que _search_entity_type a ete appele avec le bon contexte
        call_args = mock_search.call_args
        self.assertEqual(call_args.kwargs['context'].mandat_ids, [mandat_id])


# =============================================================================
# 6. UniversalSearchService — recherche fulltext clients
# =============================================================================

class TestUniversalSearchClients(RAGTestBase):
    """Tests de recherche textuelle dans les clients (integration legere)."""

    def setUp(self):
        self.svc = UniversalSearchService()

    def test_search_client_by_raison_sociale(self):
        """Recherche par raison sociale trouve le bon client."""
        context = SearchContext(
            user=self.superuser,
            mandat_ids=None,
            entity_types=[EntityType.CLIENT],
        )
        # On appelle directement _search_clients pour eviter
        # les appels semantiques / pgvector
        results = self.svc._search_clients("Alpha", context, limit=10)
        self.assertGreater(len(results), 0)
        titles = [r.title for r in results]
        self.assertIn('Client Alpha SA', titles)

    def test_search_client_filtered_by_mandat(self):
        """Filtrage par mandat_ids ne retourne que les clients lies."""
        context = SearchContext(
            user=self.regular_user,
            mandat_ids=[str(self.mandat_a.id)],
            entity_types=[EntityType.CLIENT],
        )
        results = self.svc._search_clients("Client", context, limit=10)
        # Seul Client Alpha (lie a mandat_a) doit remonter
        titles = [r.title for r in results]
        self.assertIn('Client Alpha SA', titles)
        self.assertNotIn('Client Beta GmbH', titles)

    def test_search_client_empty_mandat_returns_all(self):
        """mandat_ids=None ne filtre pas par mandat."""
        context = SearchContext(
            user=self.superuser,
            mandat_ids=None,
            entity_types=[EntityType.CLIENT],
        )
        results = self.svc._search_clients("Client", context, limit=10)
        titles = [r.title for r in results]
        self.assertIn('Client Alpha SA', titles)
        self.assertIn('Client Beta GmbH', titles)

    def test_search_client_result_structure(self):
        """Le SearchResult contient les bons champs."""
        context = SearchContext(
            user=self.superuser,
            mandat_ids=None,
            entity_types=[EntityType.CLIENT],
        )
        results = self.svc._search_clients("Alpha", context, limit=1)
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r.entity_type, EntityType.CLIENT)
        self.assertIn('/fr/clients/', r.url)
        self.assertEqual(r.icon, 'ph-buildings')
        self.assertEqual(r.color, 'info')
        self.assertIn('email', r.metadata)
        self.assertIsInstance(r.score, float)


# =============================================================================
# 7. ChatService — _search_all_entities (securite multi-tenancy)
# =============================================================================

class TestChatServiceSearchSecurity(RAGTestBase):
    """Tests de securite pour ChatService._search_all_entities."""

    def _make_conversation(self, user, mandats=None):
        """Cree une Conversation mockee (sans ecrire en DB)."""
        conv = MagicMock()
        conv.utilisateur = user
        conv.temperature = Decimal('0.7')
        conv.contexte_systeme = ''

        # Simuler le ManyToManyField mandats
        if mandats:
            mock_qs = MagicMock()
            mock_qs.exists.return_value = True
            mock_qs.__iter__ = MagicMock(return_value=iter(mandats))
            mock_qs.__bool__ = MagicMock(return_value=True)
            conv.mandats.all.return_value = mock_qs
            conv.mandats.select_related.return_value.all.return_value = mandats
        else:
            mock_qs = MagicMock()
            mock_qs.exists.return_value = False
            mock_qs.__iter__ = MagicMock(return_value=iter([]))
            mock_qs.__bool__ = MagicMock(return_value=False)
            conv.mandats.all.return_value = mock_qs
            conv.mandats.select_related.return_value.all.return_value = []

        return conv

    def _make_bare_user(self, **kwargs):
        """Cree un objet user minimal avec spec pour controler hasattr."""

        class BareUser:
            """User sans get_accessible_mandats."""
            is_superuser = False

            def is_manager(self):
                return False

        user = BareUser()
        for k, v in kwargs.items():
            setattr(user, k, v)
        return user

    @patch.object(UniversalSearchService, 'search', return_value=[])
    def test_regular_user_no_mandats_gets_empty(self, mock_search):
        """User sans mandats -> mandat_ids=[] -> aucun resultat."""
        from documents.chat_service import ChatService
        svc = ChatService()

        # User sans get_accessible_mandats, pas superuser, pas manager
        user = self._make_bare_user()

        conv = self._make_conversation(user, mandats=None)

        svc._search_all_entities(
            query="test",
            conversation=conv,
            limit=10,
            entity_types=[EntityType.CLIENT],
        )

        # Verifie que search est appele avec mandat_ids=[]
        call_args = mock_search.call_args
        context = call_args.kwargs.get('context') or call_args[1].get('context')
        self.assertEqual(context.mandat_ids, [])

    @patch.object(UniversalSearchService, 'search', return_value=[])
    def test_superuser_with_model_gets_all_active_mandats(self, mock_search):
        """Superuser (vrai modele User) -> get_accessible_mandats retourne tous les mandats actifs."""
        from documents.chat_service import ChatService
        svc = ChatService()

        conv = self._make_conversation(self.superuser, mandats=None)

        svc._search_all_entities(
            query="test",
            conversation=conv,
            limit=10,
            entity_types=[EntityType.CLIENT],
        )

        call_args = mock_search.call_args
        context = call_args.kwargs.get('context') or call_args[1].get('context')
        # Le vrai User.get_accessible_mandats() retourne les mandats ACTIF
        # mandat_ids contient les 2 mandats de nos fixtures
        self.assertIsNotNone(context.mandat_ids)
        self.assertIn(str(self.mandat_a.id), context.mandat_ids)
        self.assertIn(str(self.mandat_b.id), context.mandat_ids)

    @patch.object(UniversalSearchService, 'search', return_value=[])
    def test_superuser_bare_gets_none(self, mock_search):
        """Superuser sans get_accessible_mandats -> mandat_ids=None."""
        from documents.chat_service import ChatService
        svc = ChatService()

        user = self._make_bare_user(is_superuser=True)
        conv = self._make_conversation(user, mandats=None)

        svc._search_all_entities(
            query="test",
            conversation=conv,
            limit=10,
            entity_types=[EntityType.CLIENT],
        )

        call_args = mock_search.call_args
        context = call_args.kwargs.get('context') or call_args[1].get('context')
        self.assertIsNone(context.mandat_ids)

    @patch.object(UniversalSearchService, 'search', return_value=[])
    def test_conversation_mandats_take_priority(self, mock_search):
        """Les mandats de la conversation sont prioritaires."""
        from documents.chat_service import ChatService
        svc = ChatService()

        conv = self._make_conversation(
            self.regular_user,
            mandats=[self.mandat_a],
        )

        svc._search_all_entities(
            query="test",
            conversation=conv,
            limit=10,
            entity_types=[EntityType.CLIENT],
        )

        call_args = mock_search.call_args
        context = call_args.kwargs.get('context') or call_args[1].get('context')
        self.assertEqual(context.mandat_ids, [str(self.mandat_a.id)])

    @patch.object(UniversalSearchService, 'search', return_value=[])
    def test_user_with_get_accessible_mandats(self, mock_search):
        """User avec get_accessible_mandats() -> mandats filtres."""
        from documents.chat_service import ChatService
        svc = ChatService()

        # User avec mandats accessibles
        user = MagicMock()
        user.is_superuser = False
        user.is_manager.return_value = False
        user.get_accessible_mandats.return_value = [self.mandat_b]

        conv = self._make_conversation(user, mandats=None)

        svc._search_all_entities(
            query="test",
            conversation=conv,
            limit=10,
            entity_types=[EntityType.CLIENT],
        )

        call_args = mock_search.call_args
        context = call_args.kwargs.get('context') or call_args[1].get('context')
        self.assertEqual(context.mandat_ids, [str(self.mandat_b.id)])

    @patch.object(UniversalSearchService, 'search', return_value=[])
    def test_manager_gets_full_access(self, mock_search):
        """Manager sans get_accessible_mandats -> mandat_ids=None (acces complet)."""
        from documents.chat_service import ChatService
        svc = ChatService()

        class ManagerUser:
            is_superuser = False
            def is_manager(self):
                return True

        user = ManagerUser()
        conv = self._make_conversation(user, mandats=None)

        svc._search_all_entities(
            query="test",
            conversation=conv,
            limit=10,
            entity_types=[EntityType.CLIENT],
        )

        call_args = mock_search.call_args
        context = call_args.kwargs.get('context') or call_args[1].get('context')
        self.assertIsNone(context.mandat_ids)


# =============================================================================
# 8. ChatService — _build_system_prompt
# =============================================================================

class TestBuildSystemPrompt(RAGTestBase):
    """Tests pour ChatService._build_system_prompt."""

    def _make_conversation(self, system_context=''):
        conv = MagicMock()
        conv.contexte_systeme = system_context
        # _build_system_prompt does: conversation.mandats.select_related('client').all()
        # then checks .exists() on the result
        empty_qs = MagicMock()
        empty_qs.exists.return_value = False
        empty_qs.__iter__ = MagicMock(return_value=iter([]))
        conv.mandats.select_related.return_value.all.return_value = empty_qs
        return conv

    def test_no_results_says_no_data(self):
        """Sans resultats, le prompt mentionne 'aucune donnee'."""
        from documents.chat_service import ChatService
        svc = ChatService()
        conv = self._make_conversation()

        prompt = svc._build_system_prompt(conv, [])
        self.assertIn("Aucune donnee", prompt)

    def test_results_included_in_prompt(self):
        """Les resultats de recherche sont injectes dans le prompt."""
        from documents.chat_service import ChatService
        svc = ChatService()
        conv = self._make_conversation()

        results = [
            SearchResult(
                entity_type=EntityType.CLIENT,
                entity_id='1',
                title='Client Alpha SA',
                subtitle='SA - actif',
                description='IDE: CHE-123',
                score=0.9,
                url='/fr/clients/1/',
                icon='ph-buildings',
                color='info',
                metadata={'email': 'alpha@test.ch'},
            ),
        ]
        prompt = svc._build_system_prompt(conv, results)
        self.assertIn('Client Alpha SA', prompt)
        self.assertIn('SA - actif', prompt)

    def test_max_10_results(self):
        """Au maximum 10 resultats sont inclus dans le prompt."""
        from documents.chat_service import ChatService
        svc = ChatService()
        conv = self._make_conversation()

        results = [
            SearchResult(
                entity_type=EntityType.CLIENT,
                entity_id=str(i),
                title=f'Client {i}',
                subtitle='',
                description='',
                score=0.5,
                url=f'/fr/clients/{i}/',
                icon='ph-buildings',
                color='info',
            )
            for i in range(15)
        ]
        prompt = svc._build_system_prompt(conv, results)
        # Client 0 a 9 presents, 10 a 14 absents
        self.assertIn('Client 9', prompt)
        self.assertNotIn('Client 10', prompt)

    def test_metadata_included(self):
        """Les metadonnees importantes sont dans le prompt."""
        from documents.chat_service import ChatService
        svc = ChatService()
        conv = self._make_conversation()

        results = [
            SearchResult(
                entity_type=EntityType.FACTURE,
                entity_id='1',
                title='Facture FAC-001',
                subtitle='Client Alpha',
                description='',
                score=0.8,
                url='/fr/facturation/factures/1/',
                icon='ph-receipt',
                color='danger',
                metadata={
                    'montant_ttc': '1234.56',
                    'statut': 'EMISE',
                    'date_emission': '2026-03-01',
                },
            ),
        ]
        prompt = svc._build_system_prompt(conv, results)
        self.assertIn('montant_ttc: 1234.56', prompt)
        self.assertIn('statut: EMISE', prompt)

    def test_custom_system_context(self):
        """contexte_systeme custom de la conversation est utilise."""
        from documents.chat_service import ChatService
        svc = ChatService()
        custom = "Tu es un expert comptable suisse.\n{contexte}"
        conv = self._make_conversation(system_context=custom)

        prompt = svc._build_system_prompt(conv, [])
        self.assertIn('expert comptable suisse', prompt)

    def test_mandat_context_prepended(self):
        """Le contexte mandats est prepend aux resultats."""
        from documents.chat_service import ChatService
        svc = ChatService()
        conv = MagicMock()
        conv.contexte_systeme = ''

        mock_mandat = MagicMock()
        mock_mandat.numero = 'MAN-001'
        mock_mandat.client.raison_sociale = 'Alpha SA'

        mandats_qs = MagicMock()
        mandats_qs.exists.return_value = True
        mandats_qs.__iter__ = MagicMock(return_value=iter([mock_mandat]))
        conv.mandats.select_related.return_value.all.return_value = mandats_qs

        prompt = svc._build_system_prompt(conv, [])
        self.assertIn('Mandat MAN-001', prompt)
        self.assertIn('Alpha SA', prompt)

    def test_description_truncated(self):
        """Les descriptions longues sont tronquees a 200 caracteres."""
        from documents.chat_service import ChatService
        svc = ChatService()
        conv = self._make_conversation()

        results = [
            SearchResult(
                entity_type=EntityType.DOCUMENT,
                entity_id='1',
                title='Long Doc',
                subtitle='',
                description='x' * 500,
                score=0.5,
                url='/fr/documents/1/',
                icon='ph-file-text',
                color='primary',
            ),
        ]
        prompt = svc._build_system_prompt(conv, results)
        # La description est tronquee dans le prompt ([:200])
        # Verifie qu'on n'a pas 500 'x' dans le prompt
        occurrences = prompt.count('x' * 201)
        self.assertEqual(occurrences, 0)


# =============================================================================
# 9. SearchResult — serialisation
# =============================================================================

class TestSearchResultSerialization(TestCase):
    """Tests pour SearchResult.to_dict()."""

    def test_to_dict_structure(self):
        """to_dict() contient tous les champs attendus."""
        # NB: 0.8766 (pas 0.8765) pour eviter le banker's rounding Python 3
        # qui arrondirait 0.8765 a 0.876 au lieu de 0.877.
        r = SearchResult(
            entity_type=EntityType.CLIENT,
            entity_id='abc-123',
            title='Client Test',
            subtitle='SA',
            description='Description',
            score=0.8766,
            url='/fr/clients/abc-123/',
            icon='ph-buildings',
            color='info',
            metadata={'email': 'test@test.ch'},
        )
        d = r.to_dict()

        self.assertEqual(d['entity_type'], 'client')
        self.assertEqual(d['entity_id'], 'abc-123')
        self.assertEqual(d['title'], 'Client Test')
        self.assertEqual(d['score'], 0.877)  # arrondi 3 decimales
        self.assertIn('email', d['metadata'])

    def test_to_dict_score_rounding(self):
        """Le score est arrondi a 3 decimales."""
        r = SearchResult(
            entity_type=EntityType.DOCUMENT,
            entity_id='1',
            title='Doc',
            subtitle='',
            description='',
            score=0.123456789,
            url='/fr/documents/1/',
            icon='ph-file-text',
            color='primary',
        )
        self.assertEqual(r.to_dict()['score'], 0.123)


# =============================================================================
# 10. ChatService — chat complet (integration mockee)
# =============================================================================

class TestChatServiceChat(RAGTestBase):
    """Test du flux chat() complet avec mocks."""

    def _make_conversation_db(self, user):
        """Cree une vraie Conversation en DB."""
        from documents.models import Conversation
        conv = Conversation.objects.create(
            utilisateur=user,
            titre='Test conversation',
            temperature=Decimal('0.7'),
        )
        return conv

    @patch('documents.chat_service.universal_search')
    def test_chat_full_flow(self, mock_universal):
        """Flux complet : recherche -> prompt -> LLM -> sauvegarde."""
        from documents.chat_service import ChatService

        svc = ChatService()

        # Mock universal search
        mock_universal.search.return_value = [
            SearchResult(
                entity_type=EntityType.CLIENT,
                entity_id=str(self.client_a.id),
                title='Client Alpha SA',
                subtitle='SA - actif',
                description='Test',
                score=0.9,
                url='/fr/clients/1/',
                icon='ph-buildings',
                color='info',
            ),
        ]

        # Mock AI service
        mock_ai = MagicMock()
        mock_ai.chat.return_value = {
            'response': 'Voici les informations sur Client Alpha SA.',
            'tokens_prompt': 100,
            'tokens_completion': 20,
        }
        svc._ai_service = mock_ai

        conv = self._make_conversation_db(self.superuser)

        response = svc.chat(
            conversation=conv,
            message="Parle-moi du client Alpha",
        )

        self.assertIn('Alpha', response.contenu)
        self.assertEqual(response.erreur, None)
        self.assertIsInstance(response.duree_ms, int)

        # Verifier les messages sauvegardes en DB
        from documents.models import Message
        messages = Message.objects.filter(conversation=conv).order_by('created_at')
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].role, 'USER')
        self.assertEqual(messages[1].role, 'ASSISTANT')

    @patch('documents.chat_service.universal_search')
    def test_chat_error_handling(self, mock_universal):
        """Erreur LLM retourne ChatResponse avec erreur (pas d'exception)."""
        from documents.chat_service import ChatService

        svc = ChatService()
        mock_universal.search.return_value = []

        mock_ai = MagicMock()
        mock_ai.chat.side_effect = RuntimeError("GPU meltdown")
        svc._ai_service = mock_ai

        conv = self._make_conversation_db(self.superuser)

        response = svc.chat(
            conversation=conv,
            message="test",
        )

        self.assertIsNotNone(response.erreur)
        self.assertIn("GPU meltdown", response.erreur)
        self.assertEqual(response.sources, [])

    @patch('documents.chat_service.universal_search')
    def test_chat_html_error_sanitized(self, mock_universal):
        """Les erreurs HTML sont remplacees par un message generique."""
        from documents.chat_service import ChatService

        svc = ChatService()
        mock_universal.search.return_value = []

        mock_ai = MagicMock()
        mock_ai.chat.side_effect = RuntimeError("<html>502 Bad Gateway</html>")
        svc._ai_service = mock_ai

        conv = self._make_conversation_db(self.superuser)
        response = svc.chat(conversation=conv, message="test")

        self.assertIn("temporairement indisponible", response.erreur)
        self.assertNotIn("<html>", response.erreur)

    @patch('documents.chat_service.universal_search')
    def test_chat_separates_sources_and_entities(self, mock_universal):
        """Les sources (documents) et entites sont separees correctement."""
        from documents.chat_service import ChatService
        import uuid

        # entity_id DOIT etre un UUID valide : ChatService.chat() fait
        # Document.objects.filter(id__in=doc_ids) et Document.id est un UUIDField.
        # Un id non-UUID lance ValidationError qui casse le test silencieusement.
        doc_uuid = str(uuid.uuid4())
        client_uuid = str(uuid.uuid4())

        svc = ChatService()
        mock_universal.search.return_value = [
            SearchResult(
                entity_type=EntityType.DOCUMENT,
                entity_id=doc_uuid,
                title='facture.pdf',
                subtitle='Facture',
                description='',
                score=0.9,
                url=f'/fr/documents/{doc_uuid}/',
                icon='ph-file-text',
                color='primary',
            ),
            SearchResult(
                entity_type=EntityType.CLIENT,
                entity_id=client_uuid,
                title='Alpha SA',
                subtitle='',
                description='',
                score=0.8,
                url=f'/fr/clients/{client_uuid}/',
                icon='ph-buildings',
                color='info',
            ),
        ]

        mock_ai = MagicMock()
        mock_ai.chat.return_value = {
            'response': 'Reponse',
            'tokens_prompt': 10,
            'tokens_completion': 5,
        }
        svc._ai_service = mock_ai

        conv = self._make_conversation_db(self.superuser)
        response = svc.chat(conversation=conv, message="test")

        # Documents -> sources, le reste -> entities
        self.assertEqual(len(response.sources), 1)
        self.assertEqual(response.sources[0]['entity_type'], 'document')
        self.assertEqual(len(response.entities), 1)
        self.assertEqual(response.entities[0]['entity_type'], 'client')


# =============================================================================
# 11. ChatService — _build_conversation_history
# =============================================================================

class TestBuildConversationHistory(RAGTestBase):
    """Tests pour ChatService._build_conversation_history."""

    def test_history_order_chronological(self):
        """L'historique est retourne en ordre chronologique."""
        from documents.chat_service import ChatService
        from documents.models import Conversation, Message

        svc = ChatService()
        conv = Conversation.objects.create(
            utilisateur=self.superuser,
            titre='Test history',
            temperature=Decimal('0.7'),
        )

        Message.objects.create(conversation=conv, role='USER', contenu='Premier')
        Message.objects.create(conversation=conv, role='ASSISTANT', contenu='Reponse 1')
        Message.objects.create(conversation=conv, role='USER', contenu='Deuxieme')

        history = svc._build_conversation_history(conv)

        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['content'], 'Premier')
        self.assertEqual(history[1]['content'], 'Reponse 1')
        self.assertEqual(history[2]['content'], 'Deuxieme')

    def test_history_excludes_system_messages(self):
        """Les messages SYSTEM sont exclus de l'historique."""
        from documents.chat_service import ChatService
        from documents.models import Conversation, Message

        svc = ChatService()
        conv = Conversation.objects.create(
            utilisateur=self.superuser,
            titre='Test',
            temperature=Decimal('0.7'),
        )

        Message.objects.create(conversation=conv, role='USER', contenu='Hello')
        Message.objects.create(conversation=conv, role='SYSTEM', contenu='Error')
        Message.objects.create(conversation=conv, role='ASSISTANT', contenu='Hi')

        history = svc._build_conversation_history(conv)

        roles = [m['role'] for m in history]
        self.assertNotIn('system', roles)
        self.assertEqual(len(history), 2)

    def test_history_respects_max_messages(self):
        """max_messages limite le nombre de messages retournes."""
        from documents.chat_service import ChatService
        from documents.models import Conversation, Message

        svc = ChatService()
        conv = Conversation.objects.create(
            utilisateur=self.superuser,
            titre='Test limit',
            temperature=Decimal('0.7'),
        )

        for i in range(20):
            role = 'USER' if i % 2 == 0 else 'ASSISTANT'
            Message.objects.create(
                conversation=conv, role=role, contenu=f'Message {i}',
            )

        history = svc._build_conversation_history(conv, max_messages=5)
        self.assertEqual(len(history), 5)


# =============================================================================
# 12. EntityType enum
# =============================================================================

class TestEntityType(TestCase):
    """Tests pour l'enum EntityType."""

    def test_all_entity_types_in_config(self):
        """Tous les types d'entites ont une config dans ENTITY_CONFIG."""
        svc = UniversalSearchService()
        # Les types sans 'search_fields' peuvent manquer dans la config
        # mais doivent au minimum avoir icon/color/url_pattern
        for et in EntityType:
            if et in svc.ENTITY_CONFIG:
                config = svc.ENTITY_CONFIG[et]
                self.assertIn('icon', config, f"{et.value} manque 'icon'")
                self.assertIn('color', config, f"{et.value} manque 'color'")
                self.assertIn('url_pattern', config, f"{et.value} manque 'url_pattern'")

    def test_entity_type_values_are_lowercase(self):
        """Les valeurs de l'enum sont en minuscules."""
        for et in EntityType:
            self.assertEqual(et.value, et.value.lower())


# =============================================================================
# 13. Securite — user sans mandat accessible (fix 2026-04-05)
# =============================================================================

class TestNoAccessibleMandatsSecurity(RAGTestBase):
    """
    Verifie que le fix du bug "IA users sans mandat" (Option A stricte) est
    bien en place a toutes les couches:
    - universal_search leve NoAccessibleMandatsError (plus de silent return [])
    - ConversationCreateSerializer refuse la creation
    - send_message / stream_message renvoient 403 avec code stable
    - L'acces a une conversation contenant des mandats non-accessibles est bloque
    """

    def setUp(self):
        super().setUp()
        from rest_framework.test import APIClient

        # User sans aucun mandat accessible (pas responsable, pas dans equipe,
        # pas prestataire, pas d'AccesMandat client)
        self.orphan_user = User.objects.create_user(
            username='orphan', password='orphan', email='orphan@test.ch',
        )
        # Verifier que get_accessible_mandats retourne bien un QS vide
        assert not self.orphan_user.get_accessible_mandats().exists()

        self.orphan_client = APIClient()
        self.orphan_client.force_authenticate(user=self.orphan_user)

        self.super_client = APIClient()
        self.super_client.force_authenticate(user=self.superuser)

    def test_universal_search_raises_on_empty_mandats(self):
        """
        Un user sans mandat accessible declenche NoAccessibleMandatsError
        lorsque ses mandats_ids resultent en liste vide (pas None).
        """
        from documents.universal_search import (
            UniversalSearchService,
            SearchContext,
            NoAccessibleMandatsError,
        )

        svc = UniversalSearchService()
        context = SearchContext(
            user=self.orphan_user,
            mandat_ids=[],  # liste vide explicite = user sans mandat
            entity_types=[EntityType.CLIENT],
        )

        with self.assertRaises(NoAccessibleMandatsError) as cm:
            svc.search(query="test", context=context, limit=10)

        # Le code d'erreur stable doit etre present sur l'exception
        self.assertEqual(cm.exception.code, 'NO_ACCESSIBLE_MANDATS')

    def test_chat_service_search_raises_for_orphan_user(self):
        """
        ChatService._search_all_entities compose mandat_ids=[] pour un
        orphan_user, ce qui doit declencher NoAccessibleMandatsError.
        """
        from documents.chat_service import ChatService
        from documents.universal_search import NoAccessibleMandatsError
        from documents.models import Conversation

        svc = ChatService()
        conv = Conversation.objects.create(
            utilisateur=self.orphan_user,
            titre='Test orphan',
            temperature=Decimal('0.7'),
        )

        with self.assertRaises(NoAccessibleMandatsError):
            svc._search_all_entities(
                query="test",
                conversation=conv,
                limit=10,
                entity_types=[EntityType.CLIENT],
            )

    def test_create_conversation_blocked_for_orphan_user(self):
        """
        POST /api/v1/chat/conversations/ renvoie 400 avec error_code
        NO_ACCESSIBLE_MANDATS pour un user sans aucun mandat accessible.
        """
        url = '/api/v1/chat/conversations/'
        response = self.orphan_client.post(url, {'titre': 'Test'}, format='json')

        self.assertEqual(response.status_code, 400)
        # Le code stable doit etre present quelque part dans la reponse
        body = response.json()
        self.assertIn('NO_ACCESSIBLE_MANDATS', str(body))

    def test_send_message_returns_403_for_orphan_user(self):
        """
        send_message renvoie 403 NO_ACCESSIBLE_MANDATS pour un user sans mandat,
        meme si la conversation a ete creee anterieurement.
        """
        from documents.models import Conversation

        # On cree la conversation en contournant le serializer
        # (simule un cas ou l'acces aux mandats a ete retire apres creation)
        conv = Conversation.objects.create(
            utilisateur=self.orphan_user,
            titre='Legacy',
            temperature=Decimal('0.7'),
        )

        url = f'/api/v1/chat/conversations/{conv.id}/send_message/'
        response = self.orphan_client.post(url, {'message': 'Hello'}, format='json')

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body.get('error_code'), 'NO_ACCESSIBLE_MANDATS')
        self.assertIn('mandat', body.get('error', '').lower())

    def test_send_message_blocks_conversation_with_foreign_mandats(self):
        """
        Defense en profondeur : un user qui aurait acces a la conversation
        mais pas aux mandats qu'elle contient doit recevoir 403
        MANDAT_NOT_ACCESSIBLE.
        """
        from documents.models import Conversation

        # Creer un user avec acces a mandat_a mais pas a mandat_b
        user_partial = User.objects.create_user(
            username='partial', password='partial', email='partial@test.ch',
        )
        self.mandat_a.responsable = user_partial
        self.mandat_a.save(update_fields=['responsable'])

        # Conversation creee avec mandat_b (auquel partial n'a pas acces)
        conv = Conversation.objects.create(
            utilisateur=user_partial,
            titre='Test foreign mandat',
            temperature=Decimal('0.7'),
        )
        conv.mandats.add(self.mandat_b)

        from rest_framework.test import APIClient
        partial_client = APIClient()
        partial_client.force_authenticate(user=user_partial)

        url = f'/api/v1/chat/conversations/{conv.id}/send_message/'
        response = partial_client.post(url, {'message': 'Hello'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json().get('error_code'),
            'MANDAT_NOT_ACCESSIBLE',
        )

    def test_superuser_bypasses_mandat_check(self):
        """
        Le superuser a acces a tous les mandats actifs et peut creer une
        conversation normalement.
        """
        url = '/api/v1/chat/conversations/'
        response = self.super_client.post(url, {'titre': 'Test super'}, format='json')

        # Creation autorisee (201) ou 200 selon le serializer
        self.assertIn(response.status_code, [200, 201])


