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
