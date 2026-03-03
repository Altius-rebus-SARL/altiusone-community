"""
Commande de gestion pour initialiser les rôles par défaut et leurs permissions.

Crée les rôles ADMIN, MANAGER, COMPTABLE, ASSISTANT, CLIENT s'ils n'existent pas,
puis synchronise les permissions Django depuis ROLE_PERMISSIONS.
Idempotente : peut être relancée sans risque.
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from core.models import Role
from core.permissions import PERMISSIONS_METIER, ROLE_PERMISSIONS


ROLES_DEFAUT = [
    {"code": "ADMIN", "nom": "Administrateur", "niveau": 100, "description": "Accès complet", "est_role_defaut": False},
    {"code": "MANAGER", "nom": "Chef de bureau", "niveau": 80, "description": "Gestion des mandats", "est_role_defaut": False},
    {"code": "COMPTABLE", "nom": "Comptable", "niveau": 60, "description": "Comptabilité", "est_role_defaut": False},
    {"code": "ASSISTANT", "nom": "Assistant", "niveau": 40, "description": "Tâches administratives", "est_role_defaut": True},
    {"code": "CLIENT", "nom": "Client", "niveau": 10, "description": "Portail client", "est_role_defaut": False},
]


class Command(BaseCommand):
    help = "Initialise les rôles par défaut et synchronise les permissions métier"

    def handle(self, *args, **options):
        # 1. Créer les permissions métier dans Django
        perms_created = self._create_business_permissions()

        # 2. Créer les rôles
        roles_created = 0
        for role_data in ROLES_DEFAUT:
            _, created = Role.objects.get_or_create(
                code=role_data["code"],
                defaults={
                    "nom": role_data["nom"],
                    "niveau": role_data["niveau"],
                    "description": role_data["description"],
                    "est_role_defaut": role_data["est_role_defaut"],
                    "actif": True,
                },
            )
            if created:
                self.stdout.write(f"  ✓ Rôle créé : {role_data['code']} - {role_data['nom']}")
                roles_created += 1
            else:
                self.stdout.write(f"  · Rôle existant : {role_data['code']}")

        # 3. Synchroniser les permissions Django vers les rôles
        perms_synced = self._sync_role_permissions()

        self.stdout.write(self.style.SUCCESS(
            f"{roles_created} rôle(s) créé(s), {perms_created} permission(s) créée(s), "
            f"{perms_synced} attribution(s) synchronisée(s)."
        ))

    def _create_business_permissions(self):
        """Crée les permissions métier dans la table auth_permission."""
        created_count = 0
        for app_label, permissions in PERMISSIONS_METIER.items():
            content_type = ContentType.objects.filter(app_label=app_label).first()
            if not content_type:
                continue

            for codename, name in permissions.items():
                _, created = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=content_type,
                    defaults={"name": str(name)[:255]},
                )
                if created:
                    created_count += 1

        return created_count

    def _sync_role_permissions(self):
        """Synchronise ROLE_PERMISSIONS vers les M2M permissions des rôles."""
        synced = 0
        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            try:
                role = Role.objects.get(code=role_code)
            except Role.DoesNotExist:
                continue

            if "*" in perm_codes:
                # ADMIN : toutes les permissions métier
                all_perms = []
                for app_label in PERMISSIONS_METIER:
                    ct = ContentType.objects.filter(app_label=app_label).first()
                    if ct:
                        all_perms.extend(
                            Permission.objects.filter(content_type=ct).values_list("id", flat=True)
                        )
                current = set(role.permissions.values_list("id", flat=True))
                target = set(all_perms)
                if current != target:
                    role.permissions.set(all_perms)
                    synced += len(target - current)
            else:
                perm_ids = []
                for perm_code in perm_codes:
                    if "." not in perm_code:
                        continue
                    app_label, codename = perm_code.split(".", 1)
                    ct = ContentType.objects.filter(app_label=app_label).first()
                    if ct:
                        perm = Permission.objects.filter(codename=codename, content_type=ct).first()
                        if perm:
                            perm_ids.append(perm.id)

                current = set(role.permissions.values_list("id", flat=True))
                target = set(perm_ids)
                if current != target:
                    role.permissions.set(perm_ids)
                    synced += len(target - current)

        return synced
