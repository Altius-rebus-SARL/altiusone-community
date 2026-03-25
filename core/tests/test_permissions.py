# core/tests/test_permissions.py
"""
Tests complets pour le systeme de permissions AltiusOne.

Couvre:
- Hierarchie des roles et methodes User (is_admin, is_manager, etc.)
- Permissions API (TacheViewSet, endpoints proteges)
- Acces mandat pour les utilisateurs CLIENT
- Isolation des donnees entre mandats
"""
import uuid
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient

from core.models import (
    Role, User, Client, Mandat, Tache, Adresse, Devise,
    AccesMandat,
)
from core.permissions import (
    has_business_permission,
    get_user_permissions,
    ROLE_PERMISSIONS,
)


# =============================================================================
# HELPERS
# =============================================================================

def _make_role(code, nom, niveau, **kwargs):
    return Role.objects.create(code=code, nom=nom, niveau=niveau, **kwargs)


def _make_user(email, role, type_utilisateur='STAFF', **kwargs):
    uid = uuid.uuid4().hex[:6]
    return User.objects.create_user(
        username=kwargs.pop('username', f'user_{uid}'),
        email=email,
        password='testpass123',
        role=role,
        type_utilisateur=type_utilisateur,
        first_name=kwargs.pop('first_name', 'Test'),
        last_name=kwargs.pop('last_name', f'User_{uid}'),
        **kwargs,
    )


def _make_adresse(**kwargs):
    defaults = {
        'rue': 'Rue de Test 1',
        'code_postal': '1201',
        'localite': 'Geneve',
        'canton': 'GE',
        'pays': 'CH',
    }
    defaults.update(kwargs)
    return Adresse.objects.create(**defaults)


def _make_regime_fiscal():
    from tva.models import RegimeFiscal
    devise = Devise.objects.get_or_create(
        code='CHF',
        defaults={'nom': 'Franc suisse', 'symbole': 'Fr.', 'decimales': 2},
    )[0]
    obj, _ = RegimeFiscal.objects.get_or_create(
        code='CH',
        defaults={
            'nom': 'Suisse',
            'pays': 'CH',
            'devise_defaut': devise,
            'taux_normal': Decimal('8.1'),
        },
    )
    return obj


def _make_client(responsable=None, **kwargs):
    uid = uuid.uuid4().hex[:6]
    if responsable is None:
        role = Role.objects.filter(code='ADMIN').first()
        if not role:
            role = _make_role('ADMIN', 'Admin', 100)
        responsable = _make_user(f'resp_{uid}@test.ch', role)
    adresse = _make_adresse()
    defaults = {
        'raison_sociale': f'Test SA {uid}',
        'forme_juridique': 'SA',
        'adresse_siege': adresse,
        'email': f'info_{uid}@test.ch',
        'telephone': '+41 22 000 00 00',
        'date_debut_exercice': date(2025, 1, 1),
        'date_fin_exercice': date(2025, 12, 31),
        'responsable': responsable,
        'statut': 'ACTIF',
    }
    defaults.update(kwargs)
    return Client.objects.create(**defaults)


def _make_mandat(client=None, responsable=None, **kwargs):
    uid = uuid.uuid4().hex[:6]
    if responsable is None:
        role = Role.objects.filter(code='ADMIN').first()
        if not role:
            role = _make_role('ADMIN', 'Admin', 100)
        responsable = _make_user(f'mresp_{uid}@test.ch', role)
    if client is None:
        client = _make_client(responsable=responsable)
    regime = _make_regime_fiscal()
    devise = Devise.objects.get_or_create(
        code='CHF',
        defaults={'nom': 'Franc suisse', 'symbole': 'Fr.', 'decimales': 2},
    )[0]
    defaults = {
        'client': client,
        'numero': f'MAN-TEST-{uid}',
        'type_mandat': 'COMPTA',
        'date_debut': date(2025, 1, 1),
        'responsable': responsable,
        'statut': 'ACTIF',
        'regime_fiscal': regime,
        'devise': devise,
    }
    defaults.update(kwargs)
    return Mandat.objects.create(**defaults)


# =============================================================================
# 1. TESTS HIERARCHIE DES ROLES
# =============================================================================

class TestRoleHierarchy(TestCase):
    """Verifie que les methodes de role sur User fonctionnent correctement."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_role = _make_role('ADMIN', 'Administrateur', 100)
        cls.manager_role = _make_role('MANAGER', 'Manager', 80)
        cls.comptable_role = _make_role('COMPTABLE', 'Comptable', 60)
        cls.assistant_role = _make_role('ASSISTANT', 'Assistant', 10)
        cls.client_role = _make_role('CLIENT', 'Client', 10)

        cls.admin = _make_user('admin@test.ch', cls.admin_role)
        cls.manager = _make_user('manager@test.ch', cls.manager_role)
        cls.comptable = _make_user('comptable@test.ch', cls.comptable_role)
        cls.assistant = _make_user('assistant@test.ch', cls.assistant_role)
        cls.client_user = _make_user(
            'client@test.ch', cls.client_role, type_utilisateur='CLIENT'
        )

    def test_admin_is_admin(self):
        self.assertTrue(self.admin.is_admin())

    def test_admin_is_manager(self):
        """ADMIN (niveau 100) >= 80, therefore is_manager() = True."""
        self.assertTrue(self.admin.is_manager())

    def test_admin_is_comptable(self):
        """ADMIN (niveau 100) >= 60, therefore is_comptable() = True."""
        self.assertTrue(self.admin.is_comptable())

    def test_manager_is_manager(self):
        self.assertTrue(self.manager.is_manager())

    def test_manager_is_not_admin(self):
        self.assertFalse(self.manager.is_admin())

    def test_manager_is_comptable(self):
        """MANAGER (niveau 80) >= 60, therefore is_comptable() = True."""
        self.assertTrue(self.manager.is_comptable())

    def test_comptable_is_comptable(self):
        self.assertTrue(self.comptable.is_comptable())

    def test_comptable_is_not_manager(self):
        self.assertFalse(self.comptable.is_manager())

    def test_assistant_is_not_comptable(self):
        self.assertFalse(self.assistant.is_comptable())

    def test_client_is_client(self):
        self.assertTrue(self.client_user.is_client())

    def test_client_is_not_manager(self):
        self.assertFalse(self.client_user.is_manager())

    def test_client_is_not_comptable(self):
        self.assertFalse(self.client_user.is_comptable())

    def test_client_is_not_admin(self):
        self.assertFalse(self.client_user.is_admin())

    def test_admin_is_staff_user(self):
        self.assertTrue(self.admin.is_staff_user())

    def test_client_is_not_staff_user(self):
        self.assertFalse(self.client_user.is_staff_user())

    def test_client_is_client_user(self):
        self.assertTrue(self.client_user.is_client_user())

    def test_staff_is_not_client_user(self):
        self.assertFalse(self.admin.is_client_user())
        self.assertFalse(self.manager.is_client_user())
        self.assertFalse(self.comptable.is_client_user())


# =============================================================================
# 2. TESTS PERMISSIONS METIER (has_business_permission)
# =============================================================================

class TestBusinessPermissions(TestCase):
    """Verifie le mapping role -> permissions metier."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_role = _make_role('ADMIN', 'Administrateur', 100)
        cls.manager_role = _make_role('MANAGER', 'Manager', 80)
        cls.comptable_role = _make_role('COMPTABLE', 'Comptable', 60)
        cls.assistant_role = _make_role('ASSISTANT', 'Assistant', 10)
        cls.client_role = _make_role('CLIENT', 'Client', 10)

        cls.admin = _make_user('admin@test.ch', cls.admin_role)
        cls.manager = _make_user('manager@test.ch', cls.manager_role)
        cls.comptable = _make_user('comptable@test.ch', cls.comptable_role)
        cls.assistant = _make_user('assistant@test.ch', cls.assistant_role)
        cls.client_user = _make_user(
            'client@test.ch', cls.client_role, type_utilisateur='CLIENT'
        )

    # --- ADMIN (wildcard '*') has all permissions ---
    def test_admin_has_all_permissions(self):
        self.assertTrue(has_business_permission(self.admin, 'comptabilite.add_ecriture'))
        self.assertTrue(has_business_permission(self.admin, 'core.admin_settings'))
        self.assertTrue(has_business_permission(self.admin, 'salaires.validate_fiche'))

    # --- MANAGER has broad permissions ---
    def test_manager_can_add_ecriture(self):
        self.assertTrue(has_business_permission(self.manager, 'comptabilite.add_ecriture'))

    def test_manager_can_validate_facture(self):
        self.assertTrue(has_business_permission(self.manager, 'facturation.validate_facture'))

    def test_manager_can_view_graph(self):
        self.assertTrue(has_business_permission(self.manager, 'graph.view_graph'))

    def test_manager_cannot_cloture_exercice(self):
        """cloture_exercice is NOT in MANAGER permissions."""
        self.assertFalse(has_business_permission(self.manager, 'comptabilite.cloture_exercice'))

    # --- COMPTABLE ---
    def test_comptable_can_add_ecriture(self):
        self.assertTrue(has_business_permission(self.comptable, 'comptabilite.add_ecriture'))

    def test_comptable_can_validate_tva(self):
        self.assertTrue(has_business_permission(self.comptable, 'tva.validate_declaration'))

    def test_comptable_cannot_validate_facture(self):
        """COMPTABLE does not have validate_facture."""
        self.assertFalse(has_business_permission(self.comptable, 'facturation.validate_facture'))

    def test_comptable_cannot_delete_client(self):
        self.assertFalse(has_business_permission(self.comptable, 'core.delete_client'))

    # --- ASSISTANT ---
    def test_assistant_can_add_timetracking(self):
        self.assertTrue(has_business_permission(self.assistant, 'facturation.add_timetracking'))

    def test_assistant_cannot_validate_ecriture(self):
        self.assertFalse(has_business_permission(self.assistant, 'comptabilite.validate_ecriture'))

    def test_assistant_cannot_add_paiement(self):
        self.assertFalse(has_business_permission(self.assistant, 'facturation.add_paiement'))

    # --- CLIENT ---
    def test_client_can_view_factures(self):
        self.assertTrue(has_business_permission(self.client_user, 'facturation.view_factures'))

    def test_client_can_view_documents(self):
        self.assertTrue(has_business_permission(self.client_user, 'documents.view_documents'))

    def test_client_cannot_add_ecriture(self):
        self.assertFalse(has_business_permission(self.client_user, 'comptabilite.add_ecriture'))

    def test_client_cannot_add_facture(self):
        self.assertFalse(has_business_permission(self.client_user, 'facturation.add_facture'))

    def test_client_cannot_view_ecritures(self):
        self.assertFalse(has_business_permission(self.client_user, 'comptabilite.view_ecritures'))

    def test_client_cannot_view_salaires(self):
        self.assertFalse(has_business_permission(self.client_user, 'salaires.view_fiches_salaire'))

    def test_client_cannot_admin_settings(self):
        self.assertFalse(has_business_permission(self.client_user, 'core.admin_settings'))

    # --- get_user_permissions ---
    def test_get_user_permissions_client(self):
        perms = get_user_permissions(self.client_user)
        self.assertIn('facturation.view_factures', perms)
        self.assertIn('documents.view_documents', perms)
        self.assertNotIn('comptabilite.add_ecriture', perms)

    def test_get_user_permissions_admin_has_all(self):
        perms = get_user_permissions(self.admin)
        # ADMIN ('*') should get every permission from PERMISSIONS_METIER
        self.assertIn('comptabilite.add_ecriture', perms)
        self.assertIn('core.admin_settings', perms)
        self.assertIn('graph.view_graph', perms)


# =============================================================================
# 3. TESTS API TACHE — Permissions create/update/delete
# =============================================================================

class TestTacheAPIPermissions(APITestCase):
    """
    Verifie que les utilisateurs CLIENT ne peuvent pas creer/modifier/supprimer
    des taches via l'API, mais peuvent les lister.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin_role = _make_role('ADMIN', 'Administrateur', 100)
        cls.comptable_role = _make_role('COMPTABLE', 'Comptable', 60)
        cls.assistant_role = _make_role('ASSISTANT', 'Assistant', 10)
        cls.client_role = _make_role('CLIENT', 'Client', 10)

        cls.admin = _make_user('admin@test.ch', cls.admin_role)
        cls.comptable = _make_user('comptable@test.ch', cls.comptable_role)
        cls.assistant = _make_user('assistant@test.ch', cls.assistant_role)
        cls.client_user = _make_user(
            'client@test.ch', cls.client_role, type_utilisateur='CLIENT'
        )

        # Create a mandat for tasks
        cls.mandat = _make_mandat(responsable=cls.admin)

        # Create a task assigned to the client
        cls.existing_tache = Tache.objects.create(
            titre='Tache existante',
            cree_par=cls.admin,
            mandat=cls.mandat,
            priorite='NORMALE',
            statut='A_FAIRE',
        )
        cls.existing_tache.assignes.add(cls.client_user)

    # --- LIST ---
    def test_client_can_list_taches(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get('/api/v1/taches/')
        self.assertEqual(response.status_code, 200)

    def test_staff_can_list_taches(self):
        self.client.force_authenticate(user=self.comptable)
        response = self.client.get('/api/v1/taches/')
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_cannot_list_taches(self):
        response = self.client.get('/api/v1/taches/')
        self.assertEqual(response.status_code, 401)

    # --- RETRIEVE ---
    def test_client_can_retrieve_assigned_tache(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(f'/api/v1/taches/{self.existing_tache.pk}/')
        self.assertEqual(response.status_code, 200)

    # --- CREATE ---
    def test_client_cannot_create_tache(self):
        self.client.force_authenticate(user=self.client_user)
        data = {
            'titre': 'Nouvelle tache client',
            'priorite': 'NORMALE',
            'statut': 'A_FAIRE',
        }
        response = self.client.post('/api/v1/taches/', data, format='json')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_tache(self):
        self.client.force_authenticate(user=self.admin)
        data = {
            'titre': 'Tache admin',
            'priorite': 'HAUTE',
            'statut': 'A_FAIRE',
        }
        response = self.client.post('/api/v1/taches/', data, format='json')
        self.assertIn(response.status_code, [200, 201])

    def test_comptable_can_create_tache(self):
        self.client.force_authenticate(user=self.comptable)
        data = {
            'titre': 'Tache comptable',
            'priorite': 'NORMALE',
            'statut': 'A_FAIRE',
        }
        response = self.client.post('/api/v1/taches/', data, format='json')
        self.assertIn(response.status_code, [200, 201])

    def test_assistant_can_create_tache(self):
        """Assistants are STAFF, they should be able to create tasks."""
        self.client.force_authenticate(user=self.assistant)
        data = {
            'titre': 'Tache assistant',
            'priorite': 'BASSE',
            'statut': 'A_FAIRE',
        }
        response = self.client.post('/api/v1/taches/', data, format='json')
        self.assertIn(response.status_code, [200, 201])

    # --- UPDATE ---
    def test_client_cannot_update_tache(self):
        self.client.force_authenticate(user=self.client_user)
        data = {'titre': 'Modifie par client'}
        response = self.client.patch(
            f'/api/v1/taches/{self.existing_tache.pk}/', data, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_update_tache(self):
        self.client.force_authenticate(user=self.comptable)
        data = {'titre': 'Modifie par comptable'}
        response = self.client.patch(
            f'/api/v1/taches/{self.existing_tache.pk}/', data, format='json'
        )
        self.assertEqual(response.status_code, 200)

    # --- DELETE ---
    def test_client_cannot_delete_tache(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.delete(
            f'/api/v1/taches/{self.existing_tache.pk}/'
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_delete_tache(self):
        tache = Tache.objects.create(
            titre='A supprimer',
            cree_par=self.admin,
            priorite='BASSE',
            statut='A_FAIRE',
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/v1/taches/{tache.pk}/')
        self.assertIn(response.status_code, [200, 204])

    # --- CHANGE STATUS ---
    def test_client_cannot_change_status(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.post(
            f'/api/v1/taches/{self.existing_tache.pk}/change_status/',
            {'statut': 'EN_COURS'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_change_status(self):
        self.client.force_authenticate(user=self.comptable)
        response = self.client.post(
            f'/api/v1/taches/{self.existing_tache.pk}/change_status/',
            {'statut': 'EN_COURS'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

    # --- MES TACHES (list action, should remain accessible) ---
    def test_client_can_access_mes_taches(self):
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get('/api/v1/taches/mes_taches/')
        self.assertEqual(response.status_code, 200)

    def test_staff_can_access_mes_taches(self):
        self.client.force_authenticate(user=self.assistant)
        response = self.client.get('/api/v1/taches/mes_taches/')
        self.assertEqual(response.status_code, 200)


# =============================================================================
# 4. TESTS ACCES MANDAT — Isolation des donnees CLIENT
# =============================================================================

class TestMandatAccessIsolation(APITestCase):
    """
    Verifie que les utilisateurs CLIENT ne voient que les donnees
    de leurs mandats via AccesMandat.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin_role = _make_role('ADMIN', 'Administrateur', 100)
        cls.client_role = _make_role('CLIENT', 'Client', 10)

        cls.admin = _make_user('admin@test.ch', cls.admin_role)
        cls.client_user = _make_user(
            'client@test.ch', cls.client_role, type_utilisateur='CLIENT'
        )
        cls.other_client = _make_user(
            'other@test.ch', cls.client_role, type_utilisateur='CLIENT'
        )

        # Create two mandats
        cls.mandat_a = _make_mandat(responsable=cls.admin)
        cls.mandat_b = _make_mandat(responsable=cls.admin)

        # Give client_user access to mandat_a only
        cls.acces_a = AccesMandat.objects.create(
            utilisateur=cls.client_user,
            mandat=cls.mandat_a,
            accorde_par=cls.admin,
        )

        # Give other_client access to mandat_b only
        cls.acces_b = AccesMandat.objects.create(
            utilisateur=cls.other_client,
            mandat=cls.mandat_b,
            accorde_par=cls.admin,
        )

        # Create tasks in each mandat
        cls.tache_a = Tache.objects.create(
            titre='Tache mandat A',
            cree_par=cls.admin,
            mandat=cls.mandat_a,
            priorite='NORMALE',
            statut='A_FAIRE',
        )
        cls.tache_a.assignes.add(cls.client_user)

        cls.tache_b = Tache.objects.create(
            titre='Tache mandat B',
            cree_par=cls.admin,
            mandat=cls.mandat_b,
            priorite='NORMALE',
            statut='A_FAIRE',
        )
        cls.tache_b.assignes.add(cls.other_client)

    def test_client_sees_only_assigned_taches(self):
        """CLIENT only sees tasks where they are assigned or creator."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get('/api/v1/taches/')
        self.assertEqual(response.status_code, 200)
        tache_ids = {t['id'] for t in response.data.get('results', response.data)}
        self.assertIn(str(self.tache_a.pk), tache_ids)
        self.assertNotIn(str(self.tache_b.pk), tache_ids)

    def test_other_client_sees_only_their_taches(self):
        self.client.force_authenticate(user=self.other_client)
        response = self.client.get('/api/v1/taches/')
        self.assertEqual(response.status_code, 200)
        tache_ids = {t['id'] for t in response.data.get('results', response.data)}
        self.assertIn(str(self.tache_b.pk), tache_ids)
        self.assertNotIn(str(self.tache_a.pk), tache_ids)

    def test_admin_sees_all_taches(self):
        """Staff (is_staff=True or admin) sees all tasks."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/taches/')
        self.assertEqual(response.status_code, 200)
        tache_ids = {t['id'] for t in response.data.get('results', response.data)}
        self.assertIn(str(self.tache_a.pk), tache_ids)
        self.assertIn(str(self.tache_b.pk), tache_ids)

    def test_acces_mandat_unique_together(self):
        """Cannot create duplicate AccesMandat for same user+mandat."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            AccesMandat.objects.create(
                utilisateur=self.client_user,
                mandat=self.mandat_a,
                accorde_par=self.admin,
            )

    def test_acces_mandat_est_acces_valide(self):
        self.assertTrue(self.acces_a.est_acces_valide())

    def test_acces_mandat_inactive_is_invalid(self):
        self.acces_a.is_active = False
        self.acces_a.save()
        self.assertFalse(self.acces_a.est_acces_valide())
        # Restore
        self.acces_a.is_active = True
        self.acces_a.save()


# =============================================================================
# 5. TESTS IsStaffOrAbove PERMISSION CLASS DIRECTE
# =============================================================================

class TestIsStaffOrAbovePermission(TestCase):
    """Test unitaire de la permission IsStaffOrAbove."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_role = _make_role('ADMIN', 'Administrateur', 100)
        cls.client_role = _make_role('CLIENT', 'Client', 10)
        cls.assistant_role = _make_role('ASSISTANT', 'Assistant', 10)

        cls.admin = _make_user('admin@test.ch', cls.admin_role)
        cls.assistant = _make_user('assistant@test.ch', cls.assistant_role)
        cls.client_user = _make_user(
            'client@test.ch', cls.client_role, type_utilisateur='CLIENT'
        )

    def _make_request(self, user):
        """Create a mock request with the given user."""
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = user
        return request

    def test_staff_has_permission(self):
        from core.permissions import IsStaffOrAbove
        perm = IsStaffOrAbove()
        request = self._make_request(self.admin)
        self.assertTrue(perm.has_permission(request, None))

    def test_assistant_has_permission(self):
        from core.permissions import IsStaffOrAbove
        perm = IsStaffOrAbove()
        request = self._make_request(self.assistant)
        self.assertTrue(perm.has_permission(request, None))

    def test_client_denied(self):
        from core.permissions import IsStaffOrAbove
        perm = IsStaffOrAbove()
        request = self._make_request(self.client_user)
        self.assertFalse(perm.has_permission(request, None))

    def test_superuser_always_allowed(self):
        from core.permissions import IsStaffOrAbove
        perm = IsStaffOrAbove()
        su = _make_user('su@test.ch', self.admin_role, is_superuser=True)
        request = self._make_request(su)
        self.assertTrue(perm.has_permission(request, None))


# =============================================================================
# 6. TESTS SUPERUSER
# =============================================================================

class TestSuperuserPermissions(TestCase):
    """Verifie que le superuser a acces a tout."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_role = _make_role('ADMIN', 'Administrateur', 100)
        cls.su = User.objects.create_superuser(
            username='superadmin',
            email='su@test.ch',
            password='testpass123',
        )

    def test_superuser_is_admin(self):
        self.assertTrue(self.su.is_admin())

    def test_superuser_is_manager(self):
        self.assertTrue(self.su.is_manager())

    def test_superuser_is_comptable(self):
        self.assertTrue(self.su.is_comptable())

    def test_superuser_has_any_business_permission(self):
        self.assertTrue(has_business_permission(self.su, 'core.admin_settings'))
        self.assertTrue(has_business_permission(self.su, 'comptabilite.cloture_exercice'))
        self.assertTrue(has_business_permission(self.su, 'facturation.validate_facture'))
