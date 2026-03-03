"""
setup_desktop.py - Commande idempotente pour initialiser une instance desktop trial.

Crée le superuser, l'entreprise par défaut, un client de démo,
un mandat global et un exercice comptable pour l'année courante.

Utilise les env vars définies par le docker-compose desktop :
- ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_FIRST_NAME, ADMIN_LAST_NAME
- COMPANY_NAME
"""

import os
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Initialise une instance desktop trial (idempotent)'

    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL')
        password = os.environ.get('ADMIN_PASSWORD')
        first_name = os.environ.get('ADMIN_FIRST_NAME', '')
        last_name = os.environ.get('ADMIN_LAST_NAME', '')
        company_name = os.environ.get('COMPANY_NAME', 'Ma Fiduciaire SA')

        if not email or not password:
            self.stdout.write(self.style.WARNING(
                'ADMIN_EMAIL et ADMIN_PASSWORD requis. Setup desktop ignoré.'
            ))
            return

        from core.models import (
            User, Role, Entreprise, Adresse, Client,
            Contact, Mandat, ExerciceComptable, Devise,
        )
        from tva.models import RegimeFiscal

        with transaction.atomic():
            # 1. Superuser
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                    'doit_changer_mot_de_passe': False,
                }
            )
            if created:
                user.set_password(password)
                # Assign ADMIN role
                admin_role = Role.objects.filter(code='ADMIN').first()
                if admin_role:
                    user.role = admin_role
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Superuser créé: {email}'))
            else:
                self.stdout.write(f'Superuser existant: {email}')

            # 2. Entreprise par défaut (fiduciaire)
            entreprise = Entreprise.get_or_create_default()
            if entreprise.raison_sociale != company_name and company_name != 'Ma Fiduciaire SA':
                # Si le nom de l'entreprise portail diffère, mettre à jour
                entreprise.raison_sociale = company_name
                entreprise.save(update_fields=['raison_sociale'])
            self.stdout.write(f'Entreprise: {entreprise.raison_sociale}')

            # 3. Adresse pour le client de démo
            adresse, _ = Adresse.objects.get_or_create(
                rue='Rue de la Démo',
                code_postal='1000',
                localite='Lausanne',
                defaults={
                    'canton': 'VD',
                }
            )

            # 4. Régime fiscal et devise par défaut
            regime = RegimeFiscal.objects.filter(code='CH').first()
            devise = Devise.objects.filter(code='CHF').first()

            if not regime or not devise:
                self.stdout.write(self.style.WARNING(
                    'RegimeFiscal CH ou Devise CHF introuvable. '
                    'Assurez-vous que init_devises et les migrations TVA ont été exécutés.'
                ))
                return

            # 5. Client de démonstration
            today = date.today()
            client, client_created = Client.objects.get_or_create(
                ide_number='CHE-999.999.999',
                defaults={
                    'raison_sociale': f'{company_name} - Client Démo',
                    'forme_juridique': 'SA',
                    'entreprise': entreprise,
                    'adresse_siege': adresse,
                    'email': email,
                    'telephone': '+41 21 000 00 00',
                    'date_creation': today.replace(month=1, day=1),
                    'date_debut_exercice': today.replace(month=1, day=1),
                    'date_fin_exercice': today.replace(month=12, day=31),
                    'statut': 'ACTIF',
                    'responsable': user,
                    'regime_fiscal_defaut': regime,
                }
            )
            if client_created:
                self.stdout.write(self.style.SUCCESS(
                    f'Client démo créé: {client.raison_sociale}'
                ))
            else:
                self.stdout.write(f'Client démo existant: {client.raison_sociale}')

            # 6. Contact principal
            contact, _ = Contact.objects.get_or_create(
                client=client,
                principal=True,
                defaults={
                    'civilite': 'M',
                    'nom': last_name or 'Dupont',
                    'prenom': first_name or 'Jean',
                    'email': email,
                    'telephone': '+41 21 000 00 00',
                }
            )
            if not client.contact_principal:
                client.contact_principal = contact
                client.save(update_fields=['contact_principal'])

            # 7. Mandat global
            mandat, mandat_created = Mandat.objects.get_or_create(
                client=client,
                type_mandat='GLOBAL',
                statut='ACTIF',
                defaults={
                    'date_debut': today.replace(month=1, day=1),
                    'periodicite': 'MENSUEL',
                    'type_facturation': 'FORFAIT',
                    'budget_prevu': Decimal('0'),
                    'responsable': user,
                    'regime_fiscal': regime,
                    'devise': devise,
                    'description': 'Mandat global de démonstration',
                }
            )
            if mandat_created:
                self.stdout.write(self.style.SUCCESS(f'Mandat créé: {mandat.numero}'))
            else:
                self.stdout.write(f'Mandat existant: {mandat.numero}')

            # 8. Exercice comptable (année courante)
            exercice, ex_created = ExerciceComptable.objects.get_or_create(
                mandat=mandat,
                annee=today.year,
                defaults={
                    'date_debut': today.replace(month=1, day=1),
                    'date_fin': today.replace(month=12, day=31),
                    'statut': 'OUVERT',
                }
            )
            if ex_created:
                self.stdout.write(self.style.SUCCESS(
                    f'Exercice comptable {today.year} créé'
                ))
            else:
                self.stdout.write(f'Exercice comptable {today.year} existant')

        self.stdout.write(self.style.SUCCESS('\n=== Setup Desktop terminé ==='))
        self.stdout.write(f'  Email:    {email}')
        self.stdout.write(f'  Password: {password}')
        self.stdout.write(f'  URL:      http://localhost:8011')
