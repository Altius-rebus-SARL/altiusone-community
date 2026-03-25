# support/management/commands/seed_support.py
"""
Seed les catégories et articles de base pour le centre d'aide.
Usage: python manage.py seed_support [--reset]
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from support.models import CategorieSupport, ArticleSupport, VideoTutoriel


CATEGORIES = [
    {'code': 'premiers_pas', 'nom': 'Premiers pas', 'icone': 'ti ti-rocket', 'couleur': 'primary', 'ordre': 1},
    {'code': 'gestion', 'nom': 'Gestion de base', 'icone': 'ti ti-briefcase', 'couleur': 'success', 'ordre': 2},
    {'code': 'comptabilite', 'nom': 'Comptabilité', 'icone': 'ti ti-calculator', 'couleur': 'info', 'ordre': 3},
    {'code': 'facturation', 'nom': 'Facturation', 'icone': 'ti ti-file-invoice', 'couleur': 'warning', 'ordre': 4},
    {'code': 'tva', 'nom': 'TVA', 'icone': 'ti ti-receipt-tax', 'couleur': 'danger', 'ordre': 5},
    {'code': 'salaires', 'nom': 'Salaires & RH', 'icone': 'ti ti-users', 'couleur': 'primary', 'ordre': 6},
    {'code': 'fiscalite', 'nom': 'Fiscalité', 'icone': 'ti ti-report-money', 'couleur': 'info', 'ordre': 7},
    {'code': 'documents', 'nom': 'Documents & GED', 'icone': 'ti ti-folders', 'couleur': 'success', 'ordre': 8},
    {'code': 'projets', 'nom': 'Projets & Budget', 'icone': 'ti ti-chart-gantt', 'couleur': 'warning', 'ordre': 9},
    {'code': 'analytics', 'nom': 'Analytics', 'icone': 'ti ti-chart-infographic', 'couleur': 'danger', 'ordre': 10},
    {'code': 'chat_ia', 'nom': 'Assistant IA', 'icone': 'ti ti-robot', 'couleur': 'primary', 'ordre': 11},
    {'code': 'nextcloud', 'nom': 'Nextcloud & OnlyOffice', 'icone': 'ti ti-cloud', 'couleur': 'info', 'ordre': 12},
    {'code': 'minio', 'nom': 'Stockage S3 (MinIO)', 'icone': 'ti ti-database', 'couleur': 'success', 'ordre': 13},
    {'code': 'mobile', 'nom': 'Application mobile', 'icone': 'ti ti-device-mobile', 'couleur': 'warning', 'ordre': 14},
]


ARTICLES = [
    # — Premiers pas —
    {'categorie': 'premiers_pas', 'module': 'core', 'titre': 'Connexion et premier accès',
     'resume': "Comment se connecter à AltiusOne pour la première fois et configurer votre profil.",
     'contenu': """## Première connexion

1. Ouvrez votre navigateur et accédez à l'URL de votre instance (ex: `demo.altiusone.ch`)
2. Entrez votre email et votre mot de passe
3. Vous arrivez sur le **tableau de bord**

## Configurer votre profil

Cliquez sur votre avatar en haut à gauche puis **Profil** pour :
- Modifier vos informations personnelles
- Changer votre mot de passe
- Configurer l'authentification à deux facteurs (2FA)
- Choisir votre langue préférée
"""},

    {'categorie': 'premiers_pas', 'module': 'core', 'titre': 'Navigation et interface',
     'resume': "Comprendre la sidebar, la barre de recherche et la navigation.",
     'contenu': """## La sidebar

La sidebar à gauche contient tous les modules :
- **Dashboard** — vue d'ensemble
- **Gestion de base** — clients, mandats, exercices, tâches, contrats
- **Comptabilité** — plans, écritures, journaux, immobilisations, analytique
- **Facturation** — factures, prestations, time tracking
- **Salaires** — employés, fiches de salaire, certificats
- Et plus encore...

## La recherche globale

La barre de recherche en haut permet de chercher dans **tous les modules** :
clients, factures, écritures, documents, contrats, etc.

## L'assistant IA

Accessible depuis le menu, l'assistant IA peut répondre à vos questions sur vos données.
"""},

    # — Gestion —
    {'categorie': 'gestion', 'module': 'core', 'titre': 'Gérer les clients',
     'resume': "Créer, modifier et gérer vos clients avec leurs informations IDE et TVA.",
     'contenu': """## Créer un client

1. Allez dans **Gestion de base > Clients**
2. Cliquez sur **Nouveau client**
3. Remplissez les informations : raison sociale, forme juridique, N° IDE, TVA
4. Ajoutez les contacts et adresses

## Informations IDE/TVA

Pour les clients suisses :
- **N° IDE** : CHE-123.456.789 (Identification des entreprises)
- **N° TVA** : CHE-123.456.789 TVA

## Mandats du client

Chaque client peut avoir un ou plusieurs **mandats** qui définissent le périmètre de travail.
"""},

    {'categorie': 'gestion', 'module': 'core', 'titre': 'Gérer les contrats',
     'resume': "Créer des contrats, utiliser des modèles, suivre les échéances.",
     'contenu': """## Types de contrats

- **Émis** — contrats envoyés au client (lettre de mission, conditions générales)
- **Reçus** — contrats reçus du client (sous-traitance, accords)

## Créer un contrat

1. Allez dans **Gestion de base > Contrats**
2. Cliquez sur **Nouveau contrat**
3. Sélectionnez le client et le mandat
4. Choisissez un modèle (Confédération, fiduciaire, ou personnalisé)
5. Le document est créé dans la GED et éditable via OnlyOffice

## Suivi des échéances

Les contrats avec tacite reconduction sont suivis automatiquement avec les dates d'échéance.
"""},

    # — Comptabilité —
    {'categorie': 'comptabilite', 'module': 'comptabilite', 'titre': 'Plan comptable suisse PME',
     'resume': "Comprendre la structure du plan comptable PME suisse et créer des comptes.",
     'contenu': """## Structure du plan PME

Le plan comptable suisse PME est structuré en classes :
- **1** — Actifs (liquidités, créances, stocks, immobilisations)
- **2** — Passifs (dettes, provisions, capitaux propres)
- **3** — Produits (chiffre d'affaires)
- **4** — Charges matières et marchandises
- **5** — Charges de personnel
- **6** — Autres charges d'exploitation
- **7** — Produits/charges hors exploitation
- **8** — Produits/charges extraordinaires
- **9** — Clôture

## Créer un compte

1. Allez dans **Comptabilité > Comptes**
2. Cliquez **Nouveau compte**
3. Entrez le numéro (ex: 1020), le libellé et le type
"""},

    {'categorie': 'comptabilite', 'module': 'comptabilite', 'titre': 'Comptabilité analytique',
     'resume': "Configurer les axes et sections analytiques pour le suivi par centre de coût.",
     'contenu': """## Concept

La comptabilité analytique permet de ventiler les charges et produits par :
- **Centre de coût** (départements, sites)
- **Projet**
- **Type d'activité**

## Configuration

1. Allez dans **Comptabilité > Analytique**
2. Créez un **axe** (ex: "Département")
3. Ajoutez des **sections** (ex: "Marketing", "R&D", "Direction")
4. Définissez un budget annuel par section

## Ventilation des écritures

Chaque écriture comptable peut être ventilée sur une ou plusieurs sections avec un pourcentage.
"""},

    {'categorie': 'comptabilite', 'module': 'comptabilite', 'titre': 'Immobilisations et amortissements',
     'resume': "Gérer le registre des actifs immobilisés et calculer les amortissements.",
     'contenu': """## Créer une immobilisation

1. Allez dans **Comptabilité > Immobilisations**
2. Cliquez **Nouvelle immobilisation**
3. Remplissez : désignation, valeur d'acquisition, date, comptes (actif + charge)
4. Choisissez la méthode : linéaire ou dégressive

## Méthodes d'amortissement

- **Linéaire** — montant constant chaque année (valeur / durée)
- **Dégressive** — pourcentage fixe sur la valeur résiduelle

## Suivi

La valeur nette comptable (VNC) est calculée automatiquement.
"""},

    # — Facturation —
    {'categorie': 'facturation', 'module': 'facturation', 'titre': 'Créer une QR-facture suisse',
     'resume': "Générer des factures avec QR-code conforme aux normes suisses.",
     'contenu': """## QR-facture

Depuis 2022, la QR-facture remplace le BVR en Suisse. AltiusOne génère automatiquement :
- La **référence QR** structurée
- Le **QR code** conforme SIX
- Le **bulletin de versement** intégré au PDF

## Créer une facture

1. Allez dans **Facturation > Factures**
2. Cliquez **Nouvelle facture**
3. Sélectionnez le client et le mandat
4. Ajoutez les lignes (prestations, quantités, prix)
5. Validez et générez le PDF

## Relances

Le système de relance suisse en 4 niveaux est intégré avec frais et délais progressifs.
"""},

    # — Salaires —
    {'categorie': 'salaires', 'module': 'salaires', 'titre': "L'impôt à la source",
     'resume': "Configurer et calculer l'impôt à la source pour les employés étrangers.",
     'contenu': """## Principe

L'impôt à la source (IS) est prélevé directement sur le salaire des employés qui n'ont pas de permis C ou la nationalité suisse.

## Configuration sur l'employé

- **Canton d'imposition** — canton du lieu de travail
- **Barème IS** — A (célibataire), B (marié un revenu), C (marié deux revenus), etc.
- **Église** — certains cantons ajoutent un supplément ecclésiastique
- **Nombre d'enfants** — affecte le barème

## Calcul

Le montant IS est calculé à partir du barème cantonal officiel appliqué au revenu brut mensuel.
"""},

    # — Documents —
    {'categorie': 'documents', 'module': 'documents', 'titre': 'Scanner des documents depuis le mobile',
     'resume': "Utiliser l'app mobile pour scanner et classer automatiquement vos documents.",
     'contenu': """## Scanner un document

1. Ouvrez l'app mobile AltiusOne
2. Allez dans **Documents > Scanner**
3. Prenez une photo ou sélectionnez depuis la galerie
4. Choisissez le dossier de destination et le type de document
5. Envoyez — le document est uploadé dans la GED

## Traitement automatique

- **OCR** — le texte est extrait automatiquement (Tesseract)
- **Vectorisation** — le document est indexé pour la recherche sémantique
- **Classification** — suggestion automatique du type de document
"""},

    # — Chat IA —
    {'categorie': 'chat_ia', 'module': 'chat', 'titre': "Utiliser l'assistant IA",
     'resume': "Poser des questions sur vos données comptables, factures et documents.",
     'contenu': """## Comment ça marche

L'assistant IA recherche dans **toutes vos données vectorisées** :
- Clients, mandats, factures, écritures
- Documents (texte OCR)
- Contrats, immobilisations
- Et plus encore...

## Sélection de mandats

Vous pouvez sélectionner un ou plusieurs mandats pour cibler la recherche :
- **Aucun mandat** → recherche globale
- **1 mandat** → résultats filtrés sur ce client
- **Plusieurs mandats** → recherche multi-clients

## Exemples de questions

- "Quelles factures sont en retard ?"
- "Quel est le CA du mois pour le mandat MAN-2026-001 ?"
- "Résume les dernières écritures comptables"
"""},
]


# Vidéos Nextcloud et MinIO (IDs à compléter quand disponibles)
VIDEOS = [
    # Nextcloud
    {'categorie': 'nextcloud', 'titre': 'Nextcloud - Introduction et premiers pas',
     'description': "Découverte de Nextcloud : interface, fichiers, partage.",
     'youtube_id': 'PLACEHOLDER_NC_INTRO', 'module': '', 'duree_secondes': None},
    {'categorie': 'nextcloud', 'titre': 'OnlyOffice - Édition collaborative de documents',
     'description': "Comment éditer des documents Word/Excel directement dans le navigateur.",
     'youtube_id': 'PLACEHOLDER_NC_ONLYOFFICE', 'module': 'documents', 'duree_secondes': None},

    # MinIO
    {'categorie': 'minio', 'titre': 'MinIO - Introduction au stockage objet S3',
     'description': "Comprendre le stockage S3 et comment MinIO fonctionne.",
     'youtube_id': 'PLACEHOLDER_MINIO_INTRO', 'module': '', 'duree_secondes': None},
    {'categorie': 'minio', 'titre': 'MinIO - Console web et gestion des buckets',
     'description': "Utiliser la console MinIO pour gérer les buckets et les fichiers.",
     'youtube_id': 'PLACEHOLDER_MINIO_CONSOLE', 'module': 'documents', 'duree_secondes': None},
]


class Command(BaseCommand):
    help = "Seed les catégories et articles du centre d'aide"

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Supprimer et recréer tout')

    def handle(self, *args, **options):
        if options['reset']:
            CategorieSupport.objects.all().delete()
            self.stdout.write(self.style.WARNING("Données support supprimées"))

        # Catégories
        for cat_data in CATEGORIES:
            obj, created = CategorieSupport.objects.update_or_create(
                code=cat_data['code'],
                defaults=cat_data,
            )
            status = "créée" if created else "mise à jour"
            self.stdout.write(f"  Catégorie {obj.nom} — {status}")

        # Articles
        for art_data in ARTICLES:
            cat_code = art_data.pop('categorie')
            cat = CategorieSupport.objects.get(code=cat_code)
            slug = slugify(art_data['titre'])[:250]
            # Ensure unique slug
            base_slug = slug
            counter = 1
            while ArticleSupport.objects.filter(slug=slug).exclude(
                categorie=cat, titre=art_data['titre']
            ).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            obj, created = ArticleSupport.objects.update_or_create(
                categorie=cat,
                titre=art_data['titre'],
                defaults={**art_data, 'slug': slug},
            )
            status = "créé" if created else "mis à jour"
            self.stdout.write(f"  Article [{cat_code}] {obj.titre} — {status}")
            art_data['categorie'] = cat_code  # restore for next run

        # Vidéos (seulement celles avec de vrais IDs, pas les placeholders)
        for vid_data in VIDEOS:
            if vid_data['youtube_id'].startswith('PLACEHOLDER'):
                continue
            cat_code = vid_data.pop('categorie')
            cat = CategorieSupport.objects.get(code=cat_code)
            obj, created = VideoTutoriel.objects.update_or_create(
                categorie=cat,
                youtube_id=vid_data['youtube_id'],
                defaults=vid_data,
            )
            status = "créée" if created else "mise à jour"
            self.stdout.write(f"  Vidéo [{cat_code}] {obj.titre} — {status}")
            vid_data['categorie'] = cat_code

        total_cats = CategorieSupport.objects.count()
        total_arts = ArticleSupport.objects.count()
        total_vids = VideoTutoriel.objects.filter(
            publie=True
        ).exclude(youtube_id__startswith='PLACEHOLDER').count()
        self.stdout.write(self.style.SUCCESS(
            f"\nSupport seed terminé : {total_cats} catégories, {total_arts} articles, {total_vids} vidéos"
        ))
