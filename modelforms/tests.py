# apps/modelforms/tests.py
"""
Tests pour le module Model-Driven Forms.

Supporte les formulaires multi-modèles avec champs provenant de différentes apps.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from .models import FormConfiguration, FormTemplate, FormSubmission, ModelFieldMapping
from .services.introspector import ModelIntrospector, EXCLUDED_MODELS


User = get_user_model()


class ModelIntrospectorTests(TestCase):
    """Tests pour le service d'introspection."""

    def test_get_all_models(self):
        """Vérifie que la liste des modèles est retournée groupée par app."""
        models = ModelIntrospector.get_all_models()
        self.assertIsInstance(models, list)
        # Vérifier que c'est bien groupé par app
        self.assertTrue(all('app_label' in m and 'models' in m for m in models))

    def test_get_allowed_models(self):
        """Vérifie que la liste des modèles autorisés est retournée (format flat)."""
        models = ModelIntrospector.get_allowed_models()
        self.assertIsInstance(models, list)
        # Au minimum core.Client devrait exister
        model_paths = [m['path'] for m in models]
        self.assertIn('core.Client', model_paths)

    def test_search_models(self):
        """Vérifie la recherche de modèles."""
        results = ModelIntrospector.search_models('client')
        self.assertIsInstance(results, list)
        # Devrait trouver core.Client
        model_paths = [m['path'] for m in results]
        self.assertIn('core.Client', model_paths)

    def test_introspect_client_model(self):
        """Vérifie l'introspection du modèle Client."""
        introspector = ModelIntrospector('core.Client')
        schema = introspector.get_schema()

        self.assertEqual(schema['model'], 'core.Client')
        self.assertIn('fields', schema)
        self.assertIsInstance(schema['fields'], list)

        # Vérifier quelques champs attendus
        field_names = [f['name'] for f in schema['fields']]
        self.assertIn('raison_sociale', field_names)
        self.assertIn('email', field_names)

    def test_introspect_excluded_model(self):
        """Vérifie qu'un modèle système exclu lève une erreur."""
        with self.assertRaises(ValueError) as context:
            ModelIntrospector('auth.Permission')

        self.assertIn('non autorisé', str(context.exception).lower())

    def test_introspect_any_model_without_validation(self):
        """Vérifie qu'on peut introspecter n'importe quel modèle sans validation."""
        # Avec validate=False, on peut introspecter même les modèles "système"
        # tant qu'ils existent
        introspector = ModelIntrospector('core.User', validate=False)
        schema = introspector.get_schema()
        self.assertEqual(schema['model'], 'core.User')

    def test_search_fields(self):
        """Vérifie la recherche de champs dans un modèle."""
        introspector = ModelIntrospector('core.Client')
        results = introspector.search_fields('email')
        self.assertIsInstance(results, list)
        field_names = [f['name'] for f in results]
        self.assertIn('email', field_names)

    def test_json_schema_generation(self):
        """Vérifie la génération du JSON Schema."""
        introspector = ModelIntrospector('core.Client')
        json_schema = introspector.get_json_schema()

        self.assertEqual(json_schema['type'], 'object')
        self.assertIn('properties', json_schema)
        self.assertIn('required', json_schema)


class FormConfigurationModelTests(TestCase):
    """Tests pour le modèle FormConfiguration."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser_config',
            email='test_config@example.com',
            password='testpass123'
        )

    def test_create_configuration(self):
        """Vérifie la création d'une configuration."""
        config = FormConfiguration.objects.create(
            code='TEST_FORM',
            name='Test Form',
            target_model='core.Client',
            status=FormConfiguration.Status.DRAFT,
            created_by=self.user,
        )

        self.assertEqual(config.code, 'TEST_FORM')
        self.assertEqual(config.status, FormConfiguration.Status.DRAFT)
        self.assertIsNotNone(config.id)

    def test_create_multi_model_configuration(self):
        """Vérifie la création d'une configuration multi-modèles."""
        config = FormConfiguration.objects.create(
            code='MULTI_MODEL_FORM',
            name='Multi Model Form',
            is_multi_model=True,
            source_models=['core.Client', 'core.Contact', 'core.Adresse'],
            status=FormConfiguration.Status.DRAFT,
            created_by=self.user,
        )

        self.assertEqual(config.code, 'MULTI_MODEL_FORM')
        self.assertTrue(config.is_multi_model)
        self.assertEqual(len(config.source_models), 3)

    def test_get_target_model_class(self):
        """Vérifie la récupération de la classe du modèle cible."""
        from core.models import Client

        config = FormConfiguration.objects.create(
            code='TEST_FORM_CLASS',
            name='Test Form',
            target_model='core.Client',
            created_by=self.user,
        )

        model_class = config.get_target_model_class()
        self.assertEqual(model_class, Client)

    def test_code_unique_constraint(self):
        """Vérifie la contrainte d'unicité sur le code."""
        FormConfiguration.objects.create(
            code='UNIQUE_CODE',
            name='First Form',
            target_model='core.Client',
            created_by=self.user,
        )

        with self.assertRaises(Exception):
            FormConfiguration.objects.create(
                code='UNIQUE_CODE',
                name='Second Form',
                target_model='core.Client',
                created_by=self.user,
            )


class ModelFieldMappingTests(TestCase):
    """Tests pour le modèle ModelFieldMapping."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser_mapping',
            email='test_mapping@example.com',
            password='testpass123'
        )
        self.config = FormConfiguration.objects.create(
            code='MAPPING_TEST',
            name='Mapping Test Form',
            is_multi_model=True,
            source_models=['core.Client', 'core.Adresse'],
            created_by=self.user,
        )

    def test_create_field_mapping(self):
        """Vérifie la création d'un mapping de champ."""
        mapping = ModelFieldMapping.objects.create(
            form_config=self.config,
            source_model='core.Client',
            field_name='raison_sociale',
            widget_type='text',
            label='Nom de l\'entreprise',
            order=10,
        )

        self.assertEqual(mapping.source_model, 'core.Client')
        self.assertEqual(mapping.field_name, 'raison_sociale')
        self.assertEqual(mapping.widget_type, 'text')

    def test_create_multiple_model_mappings(self):
        """Vérifie la création de mappings pour plusieurs modèles."""
        ModelFieldMapping.objects.create(
            form_config=self.config,
            source_model='core.Client',
            field_name='raison_sociale',
            order=10,
        )
        ModelFieldMapping.objects.create(
            form_config=self.config,
            source_model='core.Adresse',
            field_name='rue',
            order=20,
        )

        self.assertEqual(self.config.field_mappings.count(), 2)
        source_models = set(m.source_model for m in self.config.field_mappings.all())
        self.assertEqual(source_models, {'core.Client', 'core.Adresse'})


class FormTemplateTests(TestCase):
    """Tests pour les templates de formulaires."""

    def test_create_template(self):
        """Vérifie la création d'un template."""
        template = FormTemplate.objects.create(
            code='TEST_TEMPLATE',
            name='Test Template',
            category=FormTemplate.Category.CLIENT,
            template_config={
                'target_model': 'core.Client',
                'form_schema': {},
            },
            is_system=False,
        )

        self.assertEqual(template.code, 'TEST_TEMPLATE')
        self.assertFalse(template.is_system)

    def test_create_multi_model_template(self):
        """Vérifie la création d'un template multi-modèles."""
        template = FormTemplate.objects.create(
            code='MULTI_TEMPLATE',
            name='Multi Model Template',
            category=FormTemplate.Category.CLIENT,
            template_config={
                'is_multi_model': True,
                'source_models': ['core.Client', 'core.Contact'],
                'form_schema': {},
            },
            is_system=False,
        )

        self.assertTrue(template.template_config.get('is_multi_model'))


class FormConfigurationAPITests(TestCase):
    """Tests API pour les configurations (utilise APIRequestFactory)."""

    def setUp(self):
        from core.models import Role
        from rest_framework.test import APIRequestFactory, force_authenticate
        from .viewset import FormConfigurationViewSet

        self.factory = APIRequestFactory()
        self.view_list = FormConfigurationViewSet.as_view({'get': 'list', 'post': 'create'})
        self.force_authenticate = force_authenticate

        # Récupérer ou créer un rôle manager
        self.manager_role, _ = Role.objects.get_or_create(
            code='MANAGER',
            defaults={'nom': 'Manager', 'niveau': 80}
        )

        self.user, _ = User.objects.get_or_create(
            username='manager_test_config',
            defaults={
                'email': 'manager_config@example.com',
                'role': self.manager_role,
            }
        )

    def test_list_configurations(self):
        """Vérifie la liste des configurations."""
        FormConfiguration.objects.create(
            code='TEST_FORM_LIST',
            name='Test Form',
            target_model='core.Client',
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.user,
        )

        request = self.factory.get('/configurations/')
        self.force_authenticate(request, user=self.user)
        response = self.view_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_configuration(self):
        """Vérifie la création via API."""
        data = {
            'code': 'API_TEST',
            'name': 'API Test Form',
            'target_model': 'core.Client',
            'category': 'CLIENT',
            'status': 'DRAFT',
        }

        request = self.factory.post('/configurations/', data, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 'API_TEST')

    def test_create_multi_model_configuration_api(self):
        """Vérifie la création d'une configuration multi-modèles via API."""
        data = {
            'code': 'API_MULTI_TEST',
            'name': 'API Multi Model Test',
            'is_multi_model': True,
            'source_models': ['core.Client', 'core.Contact'],
            'category': 'CLIENT',
            'status': 'DRAFT',
        }

        request = self.factory.post('/configurations/', data, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view_list(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_multi_model'])

    def test_create_configuration_excluded_model(self):
        """Vérifie le rejet d'un modèle système exclu."""
        data = {
            'code': 'EXCLUDED_MODEL',
            'name': 'Excluded Model Form',
            'target_model': 'auth.Permission',
            'category': 'CLIENT',
        }

        request = self.factory.post('/configurations/', data, format='json')
        self.force_authenticate(request, user=self.user)
        response = self.view_list(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class IntrospectionAPITests(TestCase):
    """Tests API pour l'introspection (utilise APIRequestFactory)."""

    def setUp(self):
        from core.models import Role
        from rest_framework.test import APIRequestFactory, force_authenticate
        from .viewset import IntrospectionViewSet

        self.factory = APIRequestFactory()
        self.view_models = IntrospectionViewSet.as_view({'get': 'models'})
        self.view_schema = IntrospectionViewSet.as_view({'get': 'model_schema'})
        self.view_fields = IntrospectionViewSet.as_view({'get': 'fields'})
        self.force_authenticate = force_authenticate

        # Récupérer ou créer un rôle manager
        self.manager_role, _ = Role.objects.get_or_create(
            code='MANAGER',
            defaults={'nom': 'Manager', 'niveau': 80}
        )

        self.user, _ = User.objects.get_or_create(
            username='manager_test_intro',
            defaults={
                'email': 'manager_intro@example.com',
                'role': self.manager_role,
            }
        )

    def test_list_models(self):
        """Vérifie la liste des modèles disponibles."""
        request = self.factory.get('/introspection/models/')
        self.force_authenticate(request, user=self.user)
        response = self.view_models(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_list_models_grouped(self):
        """Vérifie la liste des modèles groupés par application."""
        request = self.factory.get('/introspection/models/?grouped=true')
        self.force_authenticate(request, user=self.user)
        response = self.view_models(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        # Vérifier que c'est bien groupé
        self.assertTrue(all('app_label' in m and 'models' in m for m in response.data))

    def test_search_models(self):
        """Vérifie la recherche de modèles (format Select2)."""
        request = self.factory.get('/introspection/models/?q=client')
        self.force_authenticate(request, user=self.user)
        response = self.view_models(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_get_model_schema(self):
        """Vérifie le schéma d'un modèle."""
        request = self.factory.get('/introspection/schema/core.Client/')
        self.force_authenticate(request, user=self.user)
        response = self.view_schema(request, model_path='core.Client')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['model'], 'core.Client')
        self.assertIn('fields', response.data)

    def test_get_model_fields(self):
        """Vérifie les champs d'un modèle (format Select2)."""
        request = self.factory.get('/introspection/fields/core.Client/')
        self.force_authenticate(request, user=self.user)
        response = self.view_fields(request, model_path='core.Client')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['model'], 'core.Client')

    def test_search_model_fields(self):
        """Vérifie la recherche de champs dans un modèle."""
        request = self.factory.get('/introspection/fields/core.Client/?q=email')
        self.force_authenticate(request, user=self.user)
        response = self.view_fields(request, model_path='core.Client')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        field_names = [f['name'] for f in response.data['results']]
        self.assertIn('email', field_names)


# =============================================================================
# Tests PR1 (2026-04-05): mandat-scoping + post_actions
# =============================================================================

class ModelFormsPermissionsBase(TestCase):
    """Fixtures communes pour les tests de permissions et post_actions."""

    @classmethod
    def setUpTestData(cls):
        from datetime import date
        from decimal import Decimal
        from core.models import (
            Adresse, Client, Devise, Entreprise, Mandat,
        )
        from tva.models import RegimeFiscal

        # Devise + regime minimum
        cls.devise_chf, _created = Devise.objects.get_or_create(
            code='CHF',
            defaults={'nom': 'Franc suisse', 'symbole': 'CHF'},
        )
        cls.regime, _created = RegimeFiscal.objects.get_or_create(
            code='CH',
            defaults={
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

        # Users
        cls.superuser = User.objects.create_superuser(
            username='pr1_admin', password='admin', email='admin@pr1.ch',
        )
        cls.user_a = User.objects.create_user(
            username='pr1_user_a', password='a', email='a@pr1.ch',
        )
        cls.user_b = User.objects.create_user(
            username='pr1_user_b', password='b', email='b@pr1.ch',
        )
        cls.orphan = User.objects.create_user(
            username='pr1_orphan', password='o', email='orphan@pr1.ch',
        )

        # Clients + Mandats
        cls.client_alpha = Client.objects.create(
            raison_sociale='Alpha SA',
            forme_juridique='SA',
            adresse_siege=cls.adresse,
            email='alpha@test.ch',
            date_debut_exercice=date(2026, 1, 1),
            date_fin_exercice=date(2026, 12, 31),
            entreprise=cls.entreprise,
        )
        cls.client_beta = Client.objects.create(
            raison_sociale='Beta GmbH',
            forme_juridique='GmbH',
            adresse_siege=cls.adresse,
            email='beta@test.ch',
            date_debut_exercice=date(2026, 1, 1),
            date_fin_exercice=date(2026, 12, 31),
            entreprise=cls.entreprise,
        )
        cls.mandat_a = Mandat.objects.create(
            numero='PR1-MAN-A',
            client=cls.client_alpha,
            date_debut=date(2026, 1, 1),
            responsable=cls.user_a,
            regime_fiscal=cls.regime,
            devise=cls.devise_chf,
            statut='ACTIF',
        )
        cls.mandat_b = Mandat.objects.create(
            numero='PR1-MAN-B',
            client=cls.client_beta,
            date_debut=date(2026, 1, 1),
            responsable=cls.user_b,
            regime_fiscal=cls.regime,
            devise=cls.devise_chf,
            statut='ACTIF',
        )


class ScopeFormConfigsTests(ModelFormsPermissionsBase):
    """Tests pour scope_form_configs_by_user()."""

    def setUp(self):
        # Config globale (aucun mandat assigne)
        self.config_global = FormConfiguration.objects.create(
            code='PR1_GLOBAL',
            name='Global',
            category='AUTRE',
            target_model='core.Client',
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.superuser,
        )
        # Config liee a mandat_a uniquement
        self.config_a = FormConfiguration.objects.create(
            code='PR1_CONFIG_A',
            name='Config mandat A',
            category='AUTRE',
            target_model='core.Client',
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.superuser,
        )
        self.config_a.mandats.add(self.mandat_a)
        # Config liee a mandat_b uniquement
        self.config_b = FormConfiguration.objects.create(
            code='PR1_CONFIG_B',
            name='Config mandat B',
            category='AUTRE',
            target_model='core.Client',
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.superuser,
        )
        self.config_b.mandats.add(self.mandat_b)

    def test_superuser_sees_all(self):
        from modelforms.permissions import scope_form_configs_by_user
        qs = scope_form_configs_by_user(FormConfiguration.objects.all(), self.superuser)
        codes = set(qs.values_list('code', flat=True))
        self.assertIn('PR1_GLOBAL', codes)
        self.assertIn('PR1_CONFIG_A', codes)
        self.assertIn('PR1_CONFIG_B', codes)

    def test_user_a_sees_global_and_mandat_a_only(self):
        from modelforms.permissions import scope_form_configs_by_user
        qs = scope_form_configs_by_user(FormConfiguration.objects.all(), self.user_a)
        codes = set(qs.values_list('code', flat=True))
        self.assertIn('PR1_GLOBAL', codes)
        self.assertIn('PR1_CONFIG_A', codes)
        self.assertNotIn('PR1_CONFIG_B', codes)

    def test_orphan_user_sees_only_global_configs(self):
        from modelforms.permissions import scope_form_configs_by_user
        qs = scope_form_configs_by_user(FormConfiguration.objects.all(), self.orphan)
        codes = set(qs.values_list('code', flat=True))
        self.assertIn('PR1_GLOBAL', codes)
        self.assertNotIn('PR1_CONFIG_A', codes)
        self.assertNotIn('PR1_CONFIG_B', codes)


class ScopeFormSubmissionsTests(ModelFormsPermissionsBase):
    """Tests pour scope_form_submissions_by_user()."""

    def setUp(self):
        self.config = FormConfiguration.objects.create(
            code='PR1_SUB_CONFIG',
            name='Sub Config',
            category='AUTRE',
            target_model='core.Client',
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.superuser,
        )
        # user_a soumet sur mandat_a
        self.sub_a_own = FormSubmission.objects.create(
            form_config=self.config,
            submitted_data={'k': 'v'},
            submitted_by=self.user_a,
            mandat=self.mandat_a,
        )
        # user_b soumet sur mandat_b
        self.sub_b_own = FormSubmission.objects.create(
            form_config=self.config,
            submitted_data={'k': 'v'},
            submitted_by=self.user_b,
            mandat=self.mandat_b,
        )
        # user_b soumet sur mandat_a (mandat_a est partage car user_a en est responsable,
        # mais user_b n'a pas acces a mandat_a — on simule qu'il l'ait eu et soumis)
        self.sub_a_by_b = FormSubmission.objects.create(
            form_config=self.config,
            submitted_data={'k': 'v'},
            submitted_by=self.user_b,
            mandat=self.mandat_a,
        )

    def test_superuser_sees_all_submissions(self):
        from modelforms.permissions import scope_form_submissions_by_user
        qs = scope_form_submissions_by_user(FormSubmission.objects.all(), self.superuser)
        self.assertEqual(qs.count(), 3)

    def test_user_a_sees_own_and_mandat_a_submissions(self):
        from modelforms.permissions import scope_form_submissions_by_user
        qs = scope_form_submissions_by_user(FormSubmission.objects.all(), self.user_a)
        ids = set(str(s.id) for s in qs)
        # user_a voit sa propre soumission sur mandat_a
        self.assertIn(str(self.sub_a_own.id), ids)
        # ET voit la soumission de user_b sur mandat_a (mandat accessible)
        self.assertIn(str(self.sub_a_by_b.id), ids)
        # MAIS ne voit pas la soumission de user_b sur mandat_b (hors scope)
        self.assertNotIn(str(self.sub_b_own.id), ids)

    def test_orphan_user_sees_only_own_submissions(self):
        from modelforms.permissions import scope_form_submissions_by_user
        # Creer une soumission par orphan (sans mandat)
        sub_orphan = FormSubmission.objects.create(
            form_config=self.config,
            submitted_data={},
            submitted_by=self.orphan,
            mandat=None,
        )
        qs = scope_form_submissions_by_user(FormSubmission.objects.all(), self.orphan)
        ids = set(str(s.id) for s in qs)
        self.assertEqual(ids, {str(sub_orphan.id)})


class MandatIdLeakSecurityTests(ModelFormsPermissionsBase):
    """Tests pour verifier que la faille mandat_id non-valide est fermee."""

    def test_form_submission_create_serializer_rejects_foreign_mandat_id(self):
        from modelforms.serializers import FormSubmissionCreateSerializer
        from rest_framework.test import APIRequestFactory

        config = FormConfiguration.objects.create(
            code='PR1_SEC_CFG',
            name='Sec Cfg',
            category='AUTRE',
            target_model='core.Client',
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.superuser,
        )

        factory = APIRequestFactory()
        request = factory.post('/dummy/')
        request.user = self.user_a  # user_a a acces a mandat_a uniquement

        serializer = FormSubmissionCreateSerializer(
            data={
                'form_config_id': str(config.id),
                'data': {'x': 1},
                # user_a tente de soumettre avec mandat_b (auquel il n'a pas acces)
                'mandat_id': str(self.mandat_b.id),
            },
            context={'request': request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('mandat_id', serializer.errors)

    def test_form_submission_create_serializer_accepts_own_mandat(self):
        from modelforms.serializers import FormSubmissionCreateSerializer
        from rest_framework.test import APIRequestFactory

        config = FormConfiguration.objects.create(
            code='PR1_SEC_CFG_OK',
            name='Sec Cfg OK',
            category='AUTRE',
            target_model='core.Client',
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.superuser,
        )

        factory = APIRequestFactory()
        request = factory.post('/dummy/')
        request.user = self.user_a

        serializer = FormSubmissionCreateSerializer(
            data={
                'form_config_id': str(config.id),
                'data': {'x': 1},
                'mandat_id': str(self.mandat_a.id),  # user_a EST responsable de mandat_a
            },
            context={'request': request},
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)


class PostActionsExecutionTests(ModelFormsPermissionsBase):
    """Tests pour les post_actions du SubmissionHandler."""

    def _make_config(self, post_actions):
        return FormConfiguration.objects.create(
            code=f'PR1_PA_{id(post_actions)}',
            name='Post Actions Test',
            category='AUTRE',
            target_model='core.Client',
            post_actions=post_actions,
            status=FormConfiguration.Status.ACTIVE,
            created_by=self.superuser,
        )

    def test_record_variable_resolution(self):
        """{{record.id}} doit etre resolu vers l'ID du main record."""
        from modelforms.services.submission_handler import SubmissionHandler

        config = self._make_config([])
        handler = SubmissionHandler(
            form_config=config,
            submitted_data={},
            user=self.user_a,
            mandat=self.mandat_a,
        )

        resolved = handler._resolve_action_variables(
            '{{record.raison_sociale}}',
            record=self.client_alpha,
        )
        self.assertEqual(resolved, 'Alpha SA')

    def test_create_object_post_action_creates_secondary_record(self):
        """Un create_object post_action cree un nouvel objet et l'ajoute a created_records."""
        from modelforms.services.submission_handler import SubmissionHandler
        from core.models import Tache

        # Utiliser core.Tache comme objet secondaire
        post_actions = [
            {
                'type': 'create_object',
                'model': 'core.Tache',
                'field_mapping': {
                    'titre': 'Tache post-action pour {{record.raison_sociale}}',
                    'description': 'Auto',
                    'cree_par_id': '{{current_user}}',
                    'created_by_id': '{{current_user}}',
                    'priorite': 'NORMALE',
                },
            },
        ]
        config = self._make_config(post_actions)

        handler = SubmissionHandler(
            form_config=config,
            submitted_data={},
            user=self.user_a,
            mandat=self.mandat_a,
        )
        # Appeler directement _execute_post_actions avec un record existant
        handler._execute_post_actions(main_record=self.client_alpha)

        # Verifier qu'aucune erreur
        self.assertEqual(handler.post_action_errors, [])
        # Verifier que la tache a ete creee avec le titre resolu
        self.assertTrue(
            Tache.objects.filter(
                titre='Tache post-action pour Alpha SA',
            ).exists()
        )

    def test_unknown_post_action_type_is_logged_not_raising(self):
        """Un type d'action inconnu n'arrete pas les autres actions."""
        from modelforms.services.submission_handler import SubmissionHandler

        post_actions = [
            {'type': 'unknown_type_xyz', 'foo': 'bar'},
        ]
        config = self._make_config(post_actions)

        handler = SubmissionHandler(
            form_config=config,
            submitted_data={},
            user=self.user_a,
            mandat=self.mandat_a,
        )
        # Ne doit pas lever d'exception
        handler._execute_post_actions(main_record=self.client_alpha)

        # L'erreur est enregistree dans post_action_errors
        self.assertEqual(len(handler.post_action_errors), 1)
        self.assertEqual(
            handler.post_action_errors[0]['type'],
            'unknown_type_xyz',
        )

    def test_post_action_error_does_not_block_main_record(self):
        """Une erreur dans une post_action n'arrete pas le succes de process()."""
        from modelforms.services.submission_handler import SubmissionHandler

        # Action qui va echouer : modele invalide
        post_actions = [
            {
                'type': 'create_object',
                'model': 'nonexistent.Model',
                'field_mapping': {},
            },
        ]
        config = self._make_config(post_actions)

        handler = SubmissionHandler(
            form_config=config,
            submitted_data={},
            user=self.user_a,
            mandat=self.mandat_a,
        )
        handler._execute_post_actions(main_record=self.client_alpha)

        # L'erreur est enregistree mais process continue
        self.assertEqual(len(handler.post_action_errors), 1)
        self.assertIn('nonexistent.Model', handler.post_action_errors[0]['error'])
