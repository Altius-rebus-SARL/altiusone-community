# comptabilite/management/commands/load_swiss_chart_of_accounts.py

from django.core.management.base import BaseCommand
from django.db import transaction
from comptabilite.models import PlanComptable, Compte


class Command(BaseCommand):
    help = 'Charge le plan comptable suisse standard (cantonal)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plan-id',
            type=int,
            help='ID du plan comptable à utiliser (créé si non spécifié)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Chargement du plan comptable suisse...'))
        
        # Données du plan comptable cantonal suisse
        accounts_data = self.get_swiss_accounts_data()
        
        with transaction.atomic():
            # Créer ou récupérer le plan comptable
            if options['plan_id']:
                plan = PlanComptable.objects.get(pk=options['plan_id'])
                self.stdout.write(f'Utilisation du plan existant: {plan.nom}')
            else:
                plan, created = PlanComptable.objects.get_or_create(
                    nom="Plan Comptable PME Suisse (Standard Cantonal)",
                    type_plan='PME',
                    is_template=True,
                    defaults={
                        'description': 'Plan comptable standard pour PME selon les normes cantonales suisses'
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Plan comptable créé: {plan.nom}'))
                else:
                    self.stdout.write(f'Plan comptable existant: {plan.nom}')
            
            # Créer les comptes
            created_count = self.create_accounts(plan, accounts_data)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ {created_count} comptes créés avec succès pour le plan "{plan.nom}"'
                )
            )

    def get_swiss_accounts_data(self):
        """Retourne les données du plan comptable suisse"""
        return [
            {"pk": 1, "fields": {"code": "1", "label_fr": "Actifs", "parent": None}},
            {"pk": 2, "fields": {"code": "10", "label_fr": "Actifs circulants", "parent": 1}},
            {"pk": 3, "fields": {"code": "100", "label_fr": "Liquidités", "parent": 2}},
            {"pk": 4, "fields": {"code": "1000", "label_fr": "Caisse", "parent": 3}},
            {"pk": 5, "fields": {"code": "1020", "label_fr": "Banque (avoir)", "parent": 3}},
            {"pk": 6, "fields": {"code": "106", "label_fr": "Avoirs à court terme cotés en bourse", "parent": 2}},
            {"pk": 7, "fields": {"code": "1060", "label_fr": "Titres", "parent": 6}},
            {"pk": 8, "fields": {"code": "1069", "label_fr": "Ajustement de la valeur des titres", "parent": 6}},
            {"pk": 9, "fields": {"code": "110", "label_fr": "Créances résultant de livraisons et prestations", "parent": 2}},
            {"pk": 10, "fields": {"code": "1100", "label_fr": "Créances provenant de livraisons et prestations (Débiteurs)", "parent": 9}},
            {"pk": 11, "fields": {"code": "1109", "label_fr": "Ducroire", "parent": 9}},
            {"pk": 12, "fields": {"code": "1110", "label_fr": "Créances envers sociétés du groupe", "parent": 9}},
            {"pk": 13, "fields": {"code": "114", "label_fr": "Autres créances à court terme", "parent": 2}},
            {"pk": 14, "fields": {"code": "1140", "label_fr": "Avances et prêts", "parent": 13}},
            {"pk": 15, "fields": {"code": "1149", "label_fr": "Ajustement avances et prêts", "parent": 13}},
            {"pk": 16, "fields": {"code": "1170", "label_fr": "Impôt préalable TVA sur matériel, marchandises, prestations et énergie", "parent": 13}},
            {"pk": 17, "fields": {"code": "1171", "label_fr": "Impôt préalable TVA sur investissements et autres charges d'exploitation", "parent": 13}},
            {"pk": 18, "fields": {"code": "1176", "label_fr": "Impôt anticipé", "parent": 13}},
            {"pk": 19, "fields": {"code": "1180", "label_fr": "Créances envers assurances sociales et prévoyance", "parent": 13}},
            {"pk": 20, "fields": {"code": "1189", "label_fr": "Impôt à la source", "parent": 13}},
            {"pk": 21, "fields": {"code": "1190", "label_fr": "Autres créances à court terme", "parent": 13}},
            {"pk": 22, "fields": {"code": "1199", "label_fr": "Ajustement créances à court terme", "parent": 13}},
            {"pk": 23, "fields": {"code": "120", "label_fr": "Stocks et prestations non facturées", "parent": 2}},
            {"pk": 24, "fields": {"code": "1200", "label_fr": "Marchandises commerciales", "parent": 23}},
            {"pk": 25, "fields": {"code": "1210", "label_fr": "Matières premières", "parent": 23}},
            {"pk": 26, "fields": {"code": "1220", "label_fr": "Matières auxiliaires", "parent": 23}},
            {"pk": 27, "fields": {"code": "1230", "label_fr": "Matières consommables", "parent": 23}},
            {"pk": 28, "fields": {"code": "1250", "label_fr": "Marchandises en consignation", "parent": 23}},
            {"pk": 29, "fields": {"code": "1260", "label_fr": "Stocks de produits finis", "parent": 23}},
            {"pk": 30, "fields": {"code": "1280", "label_fr": "Travaux en cours", "parent": 23}},
            {"pk": 31, "fields": {"code": "130", "label_fr": "Compte de régularisation actif", "parent": 2}},
            {"pk": 32, "fields": {"code": "1300", "label_fr": "Charges payées d'avance", "parent": 31}},
            {"pk": 33, "fields": {"code": "1301", "label_fr": "Produits à recevoir", "parent": 31}},
            {"pk": 34, "fields": {"code": "14", "label_fr": "Actifs immobilisés", "parent": 1}},
            {"pk": 35, "fields": {"code": "140", "label_fr": "Immobilisations financières", "parent": 34}},
            {"pk": 36, "fields": {"code": "1400", "label_fr": "Titres à long terme", "parent": 35}},
            {"pk": 37, "fields": {"code": "1409", "label_fr": "Ajustement titres à long terme", "parent": 35}},
            {"pk": 38, "fields": {"code": "1440", "label_fr": "Prêts", "parent": 35}},
            {"pk": 39, "fields": {"code": "1441", "label_fr": "Hypothèques", "parent": 35}},
            {"pk": 40, "fields": {"code": "1449", "label_fr": "Ajustement créances à long terme", "parent": 35}},
            {"pk": 41, "fields": {"code": "148", "label_fr": "Participations", "parent": 34}},
            {"pk": 42, "fields": {"code": "1480", "label_fr": "Participations", "parent": 41}},
            {"pk": 43, "fields": {"code": "1489", "label_fr": "Ajustement participations", "parent": 41}},
            {"pk": 44, "fields": {"code": "150", "label_fr": "Immobilisations corporelles meubles", "parent": 34}},
            {"pk": 45, "fields": {"code": "1500", "label_fr": "Machines et appareils", "parent": 44}},
            {"pk": 46, "fields": {"code": "1509", "label_fr": "Ajustement machines et appareils", "parent": 44}},
            {"pk": 47, "fields": {"code": "1510", "label_fr": "Mobilier et installations", "parent": 44}},
            {"pk": 48, "fields": {"code": "1519", "label_fr": "Ajustement mobilier et installations", "parent": 44}},
            {"pk": 49, "fields": {"code": "1520", "label_fr": "Machines de bureau, informatique, systèmes de communication", "parent": 44}},
            {"pk": 50, "fields": {"code": "1529", "label_fr": "Ajustement machines de bureau et systèmes", "parent": 44}},
            {"pk": 51, "fields": {"code": "1530", "label_fr": "Véhicules", "parent": 44}},
            {"pk": 52, "fields": {"code": "1539", "label_fr": "Ajustement véhicules", "parent": 44}},
            {"pk": 53, "fields": {"code": "1540", "label_fr": "Outillages et appareils", "parent": 44}},
            {"pk": 54, "fields": {"code": "1549", "label_fr": "Ajustement outillages et appareils", "parent": 44}},
            {"pk": 55, "fields": {"code": "160", "label_fr": "Immobilisations corporelles immeubles", "parent": 34}},
            {"pk": 56, "fields": {"code": "1600", "label_fr": "Immeubles d'exploitation", "parent": 55}},
            {"pk": 57, "fields": {"code": "1609", "label_fr": "Ajustement immeubles d'exploitation", "parent": 55}},
            {"pk": 58, "fields": {"code": "170", "label_fr": "Immobilisations incorporelles", "parent": 34}},
            {"pk": 59, "fields": {"code": "1700", "label_fr": "Brevets, know-how, licences, droits, développement", "parent": 58}},
            {"pk": 60, "fields": {"code": "1709", "label_fr": "Ajustement brevets, know-how, licences", "parent": 58}},
            {"pk": 61, "fields": {"code": "1770", "label_fr": "Goodwill", "parent": 58}},
            {"pk": 62, "fields": {"code": "1779", "label_fr": "Ajustement goodwill", "parent": 58}},
            {"pk": 63, "fields": {"code": "180", "label_fr": "Capital non versé", "parent": 34}},
            {"pk": 64, "fields": {"code": "1850", "label_fr": "Capital actions, capital social, droits de participations non versés", "parent": 63}},
            # PASSIF
            {"pk": 65, "fields": {"code": "2", "label_fr": "Passif", "parent": None}},
            {"pk": 66, "fields": {"code": "20", "label_fr": "Dettes à court terme", "parent": 65}},
            {"pk": 67, "fields": {"code": "200", "label_fr": "Dettes à court terme résultant d'achats et de prestations de services", "parent": 66}},
            {"pk": 68, "fields": {"code": "2000", "label_fr": "Dettes résultant d'achats et de prestations de services (créanciers)", "parent": 67}},
            {"pk": 69, "fields": {"code": "2030", "label_fr": "Acomptes de clients", "parent": 67}},
            {"pk": 70, "fields": {"code": "2050", "label_fr": "Dettes envers des sociétés du groupe", "parent": 67}},
            {"pk": 71, "fields": {"code": "210", "label_fr": "Dettes à court terme rémunérées", "parent": 66}},
            {"pk": 72, "fields": {"code": "2100", "label_fr": "Dettes bancaires", "parent": 71}},
            {"pk": 73, "fields": {"code": "2120", "label_fr": "Engagements de financement par leasing", "parent": 71}},
            {"pk": 74, "fields": {"code": "2140", "label_fr": "Autres dettes à court terme rémunérées", "parent": 71}},
            {"pk": 75, "fields": {"code": "220", "label_fr": "Autres dettes à court terme", "parent": 66}},
            {"pk": 76, "fields": {"code": "2200", "label_fr": "TVA due", "parent": 75}},
            {"pk": 77, "fields": {"code": "2201", "label_fr": "Décompte TVA", "parent": 75}},
            {"pk": 78, "fields": {"code": "2206", "label_fr": "Impôt anticipé dû", "parent": 75}},
            {"pk": 79, "fields": {"code": "2208", "label_fr": "Impôts directs", "parent": 75}},
            {"pk": 80, "fields": {"code": "2210", "label_fr": "Autres dettes à court terme", "parent": 75}},
            {"pk": 81, "fields": {"code": "2261", "label_fr": "Dividendes", "parent": 75}},
            {"pk": 82, "fields": {"code": "2270", "label_fr": "Assurances sociales et institutions de prévoyance", "parent": 75}},
            {"pk": 83, "fields": {"code": "2279", "label_fr": "Impôt à la source", "parent": 75}},
            {"pk": 84, "fields": {"code": "230", "label_fr": "Passifs de régularisation et provisions à court terme", "parent": 66}},
            {"pk": 85, "fields": {"code": "2300", "label_fr": "Charges à payer", "parent": 84}},
            {"pk": 86, "fields": {"code": "2301", "label_fr": "Produits encaissés d'avance", "parent": 84}},
            {"pk": 87, "fields": {"code": "2330", "label_fr": "Provisions à court terme", "parent": 84}},
            {"pk": 88, "fields": {"code": "24", "label_fr": "Dettes à long terme", "parent": 65}},
            {"pk": 89, "fields": {"code": "240", "label_fr": "Dettes à long terme rémunérées", "parent": 88}},
            {"pk": 90, "fields": {"code": "2400", "label_fr": "Dettes bancaires", "parent": 89}},
            {"pk": 91, "fields": {"code": "2420", "label_fr": "Engagements de financement par leasing", "parent": 89}},
            {"pk": 92, "fields": {"code": "2430", "label_fr": "Emprunts obligataires", "parent": 89}},
            {"pk": 93, "fields": {"code": "2450", "label_fr": "Emprunts", "parent": 89}},
            {"pk": 94, "fields": {"code": "2451", "label_fr": "Hypothèques", "parent": 89}},
            {"pk": 95, "fields": {"code": "250", "label_fr": "Autres dettes à long terme", "parent": 88}},
            {"pk": 96, "fields": {"code": "2500", "label_fr": "Autres dettes à long terme", "parent": 95}},
            {"pk": 97, "fields": {"code": "260", "label_fr": "Provisions à long terme et provisions légales", "parent": 88}},
            {"pk": 98, "fields": {"code": "2600", "label_fr": "Provisions", "parent": 97}},
            {"pk": 99, "fields": {"code": "28", "label_fr": "Fonds propres (personnes morales)", "parent": 65}},
            {"pk": 100, "fields": {"code": "280", "label_fr": "Capital social ou capital de fondation", "parent": 99}},
            {"pk": 101, "fields": {"code": "2800", "label_fr": "Capital-actions, capital social, capital de fondation", "parent": 100}},
            {"pk": 102, "fields": {"code": "290", "label_fr": "Réserves / bénéfices et pertes", "parent": 99}},
            {"pk": 103, "fields": {"code": "2900", "label_fr": "Réserves légales issues du capital", "parent": 102}},
            {"pk": 104, "fields": {"code": "2930", "label_fr": "Réserves sur participations propres au capital", "parent": 102}},
            {"pk": 105, "fields": {"code": "2940", "label_fr": "Réserves d'évaluation", "parent": 102}},
            {"pk": 106, "fields": {"code": "2950", "label_fr": "Réserves légales issues du bénéfice", "parent": 102}},
            {"pk": 107, "fields": {"code": "2960", "label_fr": "Réserves libres", "parent": 102}},
            {"pk": 108, "fields": {"code": "2970", "label_fr": "Bénéfice / perte reporté", "parent": 102}},
            {"pk": 109, "fields": {"code": "2979", "label_fr": "Bénéfice / perte de l'exercice", "parent": 102}},
            {"pk": 110, "fields": {"code": "2980", "label_fr": "Propres actions, parts sociales, droits de participations", "parent": 102}},
            # PRODUITS
            {"pk": 111, "fields": {"code": "3", "label_fr": "Chiffre d'affaires résultant des ventes et prestations de services", "parent": None}},
            {"pk": 112, "fields": {"code": "3000", "label_fr": "Ventes de produits fabriqués", "parent": 111}},
            {"pk": 113, "fields": {"code": "3200", "label_fr": "Ventes de marchandises", "parent": 111}},
            {"pk": 114, "fields": {"code": "3400", "label_fr": "Ventes de prestations", "parent": 111}},
            {"pk": 115, "fields": {"code": "3600", "label_fr": "Autres ventes et prestations de services", "parent": 111}},
            {"pk": 116, "fields": {"code": "3700", "label_fr": "Prestations propres", "parent": 111}},
            {"pk": 117, "fields": {"code": "3710", "label_fr": "Consommations propres", "parent": 111}},
            {"pk": 118, "fields": {"code": "3800", "label_fr": "Déductions sur ventes", "parent": 111}},
            {"pk": 119, "fields": {"code": "3805", "label_fr": "Pertes sur clients, variation du ducroire", "parent": 111}},
            {"pk": 120, "fields": {"code": "3900", "label_fr": "Variation des stocks de produits semi-finis", "parent": 111}},
            {"pk": 121, "fields": {"code": "3901", "label_fr": "Variation des stocks de produits finis", "parent": 111}},
            {"pk": 122, "fields": {"code": "3940", "label_fr": "Variation de la valeur des prestations non facturées", "parent": 111}},
            # CHARGES
            {"pk": 123, "fields": {"code": "4", "label_fr": "Charges de matériel, marchandises et prestations de tiers", "parent": None}},
            {"pk": 124, "fields": {"code": "4000", "label_fr": "Charges de matériel de l'atelier", "parent": 123}},
            {"pk": 125, "fields": {"code": "4200", "label_fr": "Achats de marchandises destinées à la revente", "parent": 123}},
            {"pk": 126, "fields": {"code": "4400", "label_fr": "Prestations / travaux de tiers", "parent": 123}},
            {"pk": 127, "fields": {"code": "4500", "label_fr": "Charges d'énergie pour l'exploitation", "parent": 123}},
            {"pk": 128, "fields": {"code": "4900", "label_fr": "Déductions sur les charges", "parent": 123}},
            {"pk": 129, "fields": {"code": "5", "label_fr": "Charges de personnel", "parent": None}},
            {"pk": 130, "fields": {"code": "5000", "label_fr": "Salaires", "parent": 129}},
            {"pk": 131, "fields": {"code": "5700", "label_fr": "Charges sociales", "parent": 129}},
            {"pk": 132, "fields": {"code": "5800", "label_fr": "Autres charges du personnel", "parent": 129}},
            {"pk": 133, "fields": {"code": "5900", "label_fr": "Charges de personnels temporaires", "parent": 129}},
            {"pk": 134, "fields": {"code": "6", "label_fr": "Autres charges d'exploitation, Amortissements et ajustement de valeur, Résultat financier", "parent": None}},
            {"pk": 135, "fields": {"code": "6000", "label_fr": "Charges de locaux", "parent": 134}},
            {"pk": 136, "fields": {"code": "6100", "label_fr": "Entretien, réparations et remplacement des installations", "parent": 134}},
            {"pk": 137, "fields": {"code": "6105", "label_fr": "Leasing immobilisations corporelles meubles", "parent": 134}},
            {"pk": 138, "fields": {"code": "6200", "label_fr": "Charges de véhicules et de transport", "parent": 134}},
            {"pk": 139, "fields": {"code": "6260", "label_fr": "Leasing et location de véhicules", "parent": 134}},
            {"pk": 140, "fields": {"code": "6300", "label_fr": "Assurances-choses, droits, taxes, autorisations", "parent": 134}},
            {"pk": 141, "fields": {"code": "6400", "label_fr": "Charges d'énergie et évacuation des déchets", "parent": 134}},
            {"pk": 142, "fields": {"code": "6500", "label_fr": "Charges d'administration", "parent": 134}},
            {"pk": 143, "fields": {"code": "6570", "label_fr": "Charges et leasing d'informatique", "parent": 134}},
            {"pk": 144, "fields": {"code": "6600", "label_fr": "Publicité", "parent": 134}},
            {"pk": 145, "fields": {"code": "6700", "label_fr": "Autres charges d'exploitation", "parent": 134}},
            {"pk": 146, "fields": {"code": "6800", "label_fr": "Amortissement et ajustement de valeur des immobilisations corporelles", "parent": 134}},
            {"pk": 147, "fields": {"code": "6900", "label_fr": "Charges financières", "parent": 134}},
            {"pk": 148, "fields": {"code": "6950", "label_fr": "Produits financiers", "parent": 134}},
            {"pk": 149, "fields": {"code": "7", "label_fr": "Résultat des activités annexes d'exploitation", "parent": None}},
            {"pk": 150, "fields": {"code": "7000", "label_fr": "Produits accessoires", "parent": 149}},
            {"pk": 151, "fields": {"code": "7010", "label_fr": "Charges accessoires", "parent": 149}},
            {"pk": 152, "fields": {"code": "7500", "label_fr": "Produits des immeubles d'exploitation", "parent": 149}},
            {"pk": 153, "fields": {"code": "7510", "label_fr": "Charges des immeubles d'exploitation", "parent": 149}},
            {"pk": 154, "fields": {"code": "8", "label_fr": "Résultats extraordinaires et hors exploitation", "parent": None}},
            {"pk": 155, "fields": {"code": "8000", "label_fr": "Charges hors exploitation", "parent": 154}},
            {"pk": 156, "fields": {"code": "8100", "label_fr": "Produits hors exploitation", "parent": 154}},
            {"pk": 157, "fields": {"code": "8500", "label_fr": "Charges extraordinaires, exceptionnelles ou hors période", "parent": 154}},
            {"pk": 158, "fields": {"code": "8510", "label_fr": "Produits extraordinaires, exceptionnels ou hors période", "parent": 154}},
            {"pk": 159, "fields": {"code": "8900", "label_fr": "Impôts directs", "parent": 154}},
            {"pk": 160, "fields": {"code": "9", "label_fr": "Clôture", "parent": None}},
            {"pk": 161, "fields": {"code": "9200", "label_fr": "Bénéfice / perte de l'exercice", "parent": 160}},
        ]

    def create_accounts(self, plan, accounts_data):
        """Crée les comptes en respectant la hiérarchie"""
        
        # Mapping pk -> parent pk
        pk_to_parent = {}
        for item in accounts_data:
            pk_to_parent[item['pk']] = item['fields']['parent']
        
        # Créer les comptes par passes successives
        created_accounts = {}  # pk -> Compte object
        accounts_to_create = accounts_data.copy()
        max_iterations = len(accounts_to_create) * 2
        iteration = 0
        
        while accounts_to_create and iteration < max_iterations:
            iteration += 1
            created_in_this_iteration = []
            
            for account_data in accounts_to_create:
                pk = account_data['pk']
                fields = account_data['fields']
                parent_pk = fields['parent']
                
                # Peut créer si pas de parent ou parent déjà créé
                if parent_pk is None or parent_pk in created_accounts:
                    parent_account = created_accounts.get(parent_pk) if parent_pk else None
                    
                    code = fields['code']
                    libelle = fields['label_fr']
                    
                    # Déterminer le type et la classe
                    type_compte, classe = self.determine_type_and_class(code)
                    
                    # Créer le compte
                    account, created = Compte.objects.get_or_create(
                        plan_comptable=plan,
                        numero=code,
                        defaults={
                            'libelle': libelle,
                            'libelle_court': libelle[:100],
                            'type_compte': type_compte,
                            'classe': classe,
                            'niveau': len(code),
                            'compte_parent': parent_account,
                            'est_collectif': len(code) <= 2,
                            'imputable': len(code) >= 4,
                            'lettrable': code in ['1100', '2000'],  # Débiteurs, Créanciers
                            'soumis_tva': code in ['1170', '1171', '2200', '2201'],
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'  ✓ {code} - {libelle}')
                    
                    created_accounts[pk] = account
                    created_in_this_iteration.append(account_data)
            
            # Retirer les comptes créés
            for account_data in created_in_this_iteration:
                accounts_to_create.remove(account_data)
            
            # Si aucun compte créé, sortir
            if not created_in_this_iteration:
                break
        
        if accounts_to_create:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠ {len(accounts_to_create)} comptes non créés (parents manquants)'
                )
            )
        
        return len(created_accounts)

    def determine_type_and_class(self, code):
        """Détermine le type de compte et la classe selon le code"""
        
        if not code:
            return 'ACTIF', 1
        
        first_digit = int(code[0])
        
        # Classes 1 = Actifs
        if first_digit == 1:
            return 'ACTIF', 1
        
        # Classes 2 = Passifs
        elif first_digit == 2:
            return 'PASSIF', 2
        
        # Classes 3 = Produits
        elif first_digit == 3:
            return 'PRODUIT', 4
        
        # Classes 4, 5, 6 = Charges
        elif first_digit in [4, 5, 6]:
            return 'CHARGE', 6
        
        # Classes 7 = Produits
        elif first_digit == 7:
            return 'PRODUIT', 7
        
        # Classes 8 = Charges/Produits extraordinaires
        elif first_digit == 8:
            return 'CHARGE', 8
        
        # Classes 9 = Clôture
        elif first_digit == 9:
            return 'CHARGE', 9
        
        return 'ACTIF', 1