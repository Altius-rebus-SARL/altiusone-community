# documents/management/commands/generate_test_documents.py
"""
Commande Django pour generer des documents de test.

Utilise faker-file pour creer des fichiers PDF, DOCX, XLSX
avec du contenu realiste pour tester l'application.

Usage:
    python manage.py generate_test_documents --count 50
    python manage.py generate_test_documents --count 100 --mandat <uuid>
    python manage.py generate_test_documents --clean  # Supprime les documents de test
"""
import os
import uuid
import random
import hashlib
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings
from faker import Faker

fake = Faker('fr_CH')


class Command(BaseCommand):
    help = 'Genere des documents de test avec faker-file'

    # Types de documents fiduciaire
    DOCUMENT_TYPES = [
        ('facture', 'Facture'),
        ('decompte_tva', 'Decompte TVA'),
        ('bilan', 'Bilan'),
        ('compte_resultat', 'Compte de resultat'),
        ('fiche_salaire', 'Fiche de salaire'),
        ('contrat', 'Contrat'),
        ('declaration_impots', 'Declaration impots'),
        ('extrait_bancaire', 'Extrait bancaire'),
        ('quittance', 'Quittance'),
        ('correspondance', 'Correspondance'),
    ]

    # Structure de dossiers fiduciaire
    FOLDER_STRUCTURE = {
        'Comptabilite': ['Factures fournisseurs', 'Factures clients', 'Banque', 'Caisse', 'Amortissements'],
        'Fiscalite': ['TVA', 'Impots', 'Declarations'],
        'Salaires': ['Fiches de paie', 'AVS', 'Assurances'],
        'Administration': ['Contrats', 'Correspondance', 'PV Assemblees'],
        'Clients': ['Documents recus', 'Documents envoyes'],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Nombre de documents a generer (default: 50)'
        )
        parser.add_argument(
            '--mandat',
            type=str,
            help='UUID du mandat cible (si non specifie, utilise tous les mandats)'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Supprime les documents de test existants'
        )
        parser.add_argument(
            '--with-ocr',
            action='store_true',
            help='Genere aussi le texte OCR pour chaque document'
        )
        parser.add_argument(
            '--create-folders',
            action='store_true',
            help='Cree la structure de dossiers standard'
        )

    def handle(self, *args, **options):
        from documents.models import Document, Dossier, TypeDocument, CategorieDocument
        from core.models import Mandat, Client
        from django.contrib.auth import get_user_model

        User = get_user_model()

        if options['clean']:
            self.clean_test_documents()
            return

        # Verifier qu'il y a au moins un mandat
        if options['mandat']:
            try:
                mandats = [Mandat.objects.get(id=options['mandat'])]
            except Mandat.DoesNotExist:
                raise CommandError(f"Mandat {options['mandat']} non trouve")
        else:
            mandats = list(Mandat.objects.filter(is_active=True)[:5])
            if not mandats:
                self.stdout.write(self.style.WARNING('Aucun mandat trouve. Creation de mandats de test...'))
                mandats = self.create_test_mandats()

        # Recuperer ou creer un utilisateur
        user = User.objects.filter(is_active=True).first()
        if not user:
            raise CommandError("Aucun utilisateur actif trouve")

        # Creer la structure de dossiers si demande
        if options['create_folders']:
            self.create_folder_structure(mandats, user)

        # Recuperer les dossiers existants
        dossiers = list(Dossier.objects.filter(
            mandat__in=mandats,
            is_active=True
        ))

        # Recuperer ou creer les types de documents
        types_documents = self.get_or_create_document_types()

        count = options['count']
        with_ocr = options['with_ocr']

        self.stdout.write(f'Generation de {count} documents de test...')

        created = 0
        for i in range(count):
            try:
                doc = self.create_fake_document(
                    mandats=mandats,
                    dossiers=dossiers,
                    types_documents=types_documents,
                    with_ocr=with_ocr
                )
                created += 1
                if created % 10 == 0:
                    self.stdout.write(f'  {created}/{count} documents crees...')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Erreur creation document: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Termine! {created} documents crees.'))

    def create_test_mandats(self):
        """Cree des mandats de test si necessaire."""
        from core.models import Mandat, Client
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.filter(is_active=True).first()

        mandats = []
        for i in range(3):
            # Creer client
            client = Client.objects.create(
                raison_sociale=fake.company(),
                forme_juridique=random.choice(['SA', 'SARL', 'RI']),
                adresse_ligne1=fake.street_address(),
                npa=fake.postcode(),
                localite=fake.city(),
                pays='CH',
                email=fake.company_email(),
                telephone=fake.phone_number(),
            )

            # Creer mandat
            mandat = Mandat.objects.create(
                client=client,
                numero=f"M{2024}{i+1:04d}",
                date_debut=timezone.now().date() - timedelta(days=random.randint(30, 365)),
                responsable=user,
                statut='ACTIF',
            )
            mandats.append(mandat)

        self.stdout.write(self.style.SUCCESS(f'{len(mandats)} mandats de test crees'))
        return mandats

    def create_folder_structure(self, mandats, user):
        """Cree la structure de dossiers standard pour chaque mandat."""
        from documents.models import Dossier

        total_created = 0
        for mandat in mandats:
            for parent_name, subfolders in self.FOLDER_STRUCTURE.items():
                # Creer dossier parent
                parent, created = Dossier.objects.get_or_create(
                    mandat=mandat,
                    nom=parent_name,
                    parent=None,
                    defaults={
                        'type_dossier': 'EXERCICE',
                        'proprietaire': user,
                        'client': mandat.client,
                    }
                )
                if created:
                    total_created += 1

                # Creer sous-dossiers
                for subfolder_name in subfolders:
                    _, created = Dossier.objects.get_or_create(
                        mandat=mandat,
                        nom=subfolder_name,
                        parent=parent,
                        defaults={
                            'type_dossier': 'EXERCICE',
                            'proprietaire': user,
                            'client': mandat.client,
                        }
                    )
                    if created:
                        total_created += 1

        self.stdout.write(self.style.SUCCESS(f'{total_created} dossiers crees'))

    def get_or_create_document_types(self):
        """Recupere ou cree les types de documents."""
        from documents.models import TypeDocument, CategorieDocument

        # Creer une categorie par defaut si necessaire
        categorie, _ = CategorieDocument.objects.get_or_create(
            nom='Documents comptables',
            defaults={'description': 'Documents comptables et administratifs'}
        )

        types = {}
        for code, libelle in self.DOCUMENT_TYPES:
            type_doc, _ = TypeDocument.objects.get_or_create(
                code=code.upper(),
                defaults={
                    'libelle': libelle,
                    'categorie': categorie,
                    'type_document': 'comptabilite',
                }
            )
            types[code] = type_doc

        return types

    def create_fake_document(self, mandats, dossiers, types_documents, with_ocr=False):
        """Cree un document fictif."""
        from documents.models import Document

        mandat = random.choice(mandats)
        dossier = random.choice(dossiers) if dossiers else None

        # Type de document
        doc_type_key = random.choice(list(types_documents.keys()))
        type_doc = types_documents[doc_type_key]

        # Extension
        extension = random.choice(['.pdf', '.pdf', '.pdf', '.docx', '.xlsx', '.jpg'])

        # Nom de fichier realiste
        filename = self.generate_filename(doc_type_key, extension)

        # Contenu fictif (taille)
        taille = random.randint(50000, 5000000)  # 50KB - 5MB

        # Date du document
        date_document = fake.date_between(start_date='-2y', end_date='today')
        date_upload = fake.date_time_between(start_date=date_document, end_date='now', tzinfo=timezone.get_current_timezone())

        # Hash fictif
        hash_fichier = hashlib.sha256(f"{filename}{taille}{random.random()}".encode()).hexdigest()

        # Texte OCR si demande
        ocr_text = None
        if with_ocr:
            ocr_text = self.generate_ocr_text(doc_type_key)

        # Creer le document
        doc = Document.objects.create(
            mandat=mandat,
            dossier=dossier,
            type_document=type_doc,
            nom_fichier=filename,
            nom_original=filename,
            extension=extension,
            mime_type=self.get_mime_type(extension),
            taille=taille,
            hash_fichier=hash_fichier,
            date_document=date_document,
            date_upload=date_upload,
            statut_traitement='OCR_TERMINE' if with_ocr else 'UPLOAD',
            ocr_text=ocr_text,
            ocr_confidence=random.uniform(0.85, 0.99) if with_ocr else None,
            prediction_type=type_doc.libelle if with_ocr else None,
            prediction_confidence=random.uniform(0.80, 0.95) if with_ocr else None,
            description=f"Document de test genere automatiquement - {type_doc.libelle}",
        )

        return doc

    def generate_filename(self, doc_type, extension):
        """Genere un nom de fichier realiste."""
        date_str = fake.date_this_year().strftime('%Y%m%d')

        prefixes = {
            'facture': ['FA', 'FACT', 'INV'],
            'decompte_tva': ['TVA', 'DTVA'],
            'bilan': ['BIL', 'BILAN'],
            'compte_resultat': ['CR', 'PP'],
            'fiche_salaire': ['SAL', 'PAIE'],
            'contrat': ['CTR', 'CONTRAT'],
            'declaration_impots': ['IMP', 'FISC'],
            'extrait_bancaire': ['BQ', 'EXTRAIT'],
            'quittance': ['QUI', 'REC'],
            'correspondance': ['CORR', 'LTR'],
        }

        prefix = random.choice(prefixes.get(doc_type, ['DOC']))
        numero = random.randint(1000, 9999)

        return f"{prefix}_{date_str}_{numero}{extension}"

    def generate_ocr_text(self, doc_type):
        """Genere du texte OCR realiste selon le type de document."""
        texts = {
            'facture': lambda: f"""
FACTURE N {random.randint(1000, 9999)}

{fake.company()}
{fake.street_address()}
{fake.postcode()} {fake.city()}

Date: {fake.date_this_year().strftime('%d.%m.%Y')}
Echeance: {fake.date_between(start_date='today', end_date='+30d').strftime('%d.%m.%Y')}

Description                          Quantite    Prix unit.    Total
{fake.sentence(nb_words=3)}              {random.randint(1, 10)}         {random.randint(50, 500)}.00     {random.randint(100, 5000)}.00
{fake.sentence(nb_words=4)}              {random.randint(1, 5)}         {random.randint(100, 1000)}.00    {random.randint(500, 10000)}.00

Sous-total:                                                    CHF {random.randint(1000, 15000)}.00
TVA 8.1%:                                                      CHF {random.randint(80, 1200)}.00
Total:                                                         CHF {random.randint(1100, 16000)}.00

Paiement sous 30 jours
IBAN: CH{random.randint(10, 99)} {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(1000, 9999)} {random.randint(0, 9)}
""",
            'fiche_salaire': lambda: f"""
FICHE DE SALAIRE - {fake.date_this_month().strftime('%B %Y').upper()}

Employe: {fake.name()}
AVS: 756.{random.randint(1000, 9999)}.{random.randint(1000, 9999)}.{random.randint(10, 99)}
Date entree: {fake.date_between(start_date='-5y', end_date='-1y').strftime('%d.%m.%Y')}

GAINS                                              DEDUCTIONS
Salaire de base:        CHF {random.randint(4000, 12000)}.00    AVS/AI/APG:     CHF {random.randint(300, 800)}.00
Allocation familiales:  CHF {random.randint(0, 400)}.00         AC:             CHF {random.randint(50, 150)}.00
                                                  LPP:            CHF {random.randint(200, 600)}.00
                                                  Impot source:   CHF {random.randint(100, 1500)}.00

Total brut:             CHF {random.randint(5000, 13000)}.00    Total deductions: CHF {random.randint(800, 3000)}.00

SALAIRE NET:            CHF {random.randint(4000, 10000)}.00

Versement sur compte: IBAN CH{random.randint(10, 99)} {random.randint(1000, 9999)} {random.randint(1000, 9999)}
""",
            'extrait_bancaire': lambda: f"""
EXTRAIT DE COMPTE

{fake.company()} Banque
Compte: {random.randint(100000, 999999)}-{random.randint(10, 99)}

Periode du {fake.date_this_month().strftime('%d.%m.%Y')} au {fake.date_this_month().strftime('%d.%m.%Y')}

Date        Libelle                                  Debit       Credit      Solde
{fake.date_this_month().strftime('%d.%m')}      Virement {fake.company()[:20]}                           {random.randint(1000, 10000)}.00   {random.randint(10000, 50000)}.00
{fake.date_this_month().strftime('%d.%m')}      Paiement facture                 {random.randint(500, 3000)}.00                  {random.randint(8000, 45000)}.00
{fake.date_this_month().strftime('%d.%m')}      Salaires                         {random.randint(5000, 20000)}.00                 {random.randint(3000, 40000)}.00
{fake.date_this_month().strftime('%d.%m')}      Loyer                            {random.randint(1500, 5000)}.00                  {random.randint(1000, 35000)}.00

Solde final:                                                                 CHF {random.randint(5000, 50000)}.00
""",
        }

        generator = texts.get(doc_type, lambda: fake.text(max_nb_chars=500))
        return generator()

    def get_mime_type(self, extension):
        """Retourne le type MIME pour une extension."""
        mime_types = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
        }
        return mime_types.get(extension, 'application/octet-stream')

    def clean_test_documents(self):
        """Supprime les documents de test."""
        from documents.models import Document

        deleted, _ = Document.objects.filter(
            description__contains='Document de test genere automatiquement'
        ).delete()

        self.stdout.write(self.style.SUCCESS(f'{deleted} documents de test supprimes'))
