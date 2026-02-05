# apps/modelforms/tests.py
"""
Tests pour le module Model-Driven Forms.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from .models import FormConfiguration, FormTemplate, FormSubmission, ModelFieldMapping
from .services.introspector import ModelIntrospector, ALLOWED_MODELS


User = get_user_model()


class ModelIntrospectorTests(TestCase):
    """Tests pour le service d'introspection."""

    def test_get_allowed_models(self):
        """Vérifie que la liste des modèles autorisés est retournée."""
        models = ModelIntrospector.get_allowed_models()
        self.assertIsInstance(models, list)
        # Au minimum core.Client devrait exister
        model_paths = [m['path'] for m in models]
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

    def test_introspect_disallowed_model(self):
        """Vérifie qu'un modèle non autorisé lève une erreur."""
        with self.assertRaises(ValueError) as context:
            ModelIntrospector('auth.User')

        self.assertIn('non autorisé', str(context.exception))

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
            username='testuser',
            email='test@example.com',
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

    def test_get_target_model_class(self):
        """Vérifie la récupération de la classe du modèle cible."""
        from core.models import Client

        config = FormConfiguration.objects.create(
            code='TEST_FORM',
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

    def test_create_configuration_invalid_model(self):
        """Vérifie le rejet d'un modèle non autorisé."""
        data = {
            'code': 'INVALID_MODEL',
            'name': 'Invalid Model Form',
            'target_model': 'auth.User',
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
        self.view_schema = IntrospectionViewSet.as_view({'get': 'schema'})
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

    def test_get_model_schema(self):
        """Vérifie le schéma d'un modèle."""
        request = self.factory.get('/introspection/schema/core.Client/')
        self.force_authenticate(request, user=self.user)
        response = self.view_schema(request, model_path='core.Client')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['model'], 'core.Client')
        self.assertIn('fields', response.data)
