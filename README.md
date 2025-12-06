# AltiusOne - Plateforme de Gestion Fiduciaire Suisse

AltiusOne est une application SaaS complète de gestion fiduciaire spécialement conçue pour le marché suisse, offrant une architecture multi-tenant avec provisionnement automatique d'instances VPS dédiées.

## 🎯 Caractéristiques Principales

### Architecture Multi-Tenant
- Instances VPS dédiées par client (Hetzner Cloud)
- Base de données PostgreSQL isolée par tenant
- Storage suisse conforme (S3/MinIO)
- Provisionnement automatique via Terraform
- Orchestration Docker

### Modules Fonctionnels

#### 1. Core & Gestion
- Gestion multi-sociétés et multi-mandats
- Utilisateurs avec permissions granulaires
- Exercices comptables
- Multi-langue (FR, DE, IT, EN)

#### 2. Comptabilité
- Plans comptables personnalisables (Swiss GAAP, PCG)
- Saisie d'écritures avec validation
- Grand livre, balance, journaux
- Lettrage automatique
- Import/export comptable

#### 3. TVA
- Déclarations TVA trimestrielles/semestrielles
- Méthodes: effective, taux forfaitaire, taux de la dette fiscale nette
- Génération XML format AFC
- Suivi des opérations soumises à TVA
- Codes TVA Suisse (200, 205, 220, 230, 280, 289, 400, etc.)

#### 4. Facturation & Time Tracking
- Gestion des prestations
- Suivi du temps facturable
- Génération de factures
- QR-factures (Swiss QR-Bill)
- Relances automatiques
- Paiements et rapprochements

#### 5. Salaires & RH
- Fiches de salaire suisses
- Cotisations sociales (AVS, AC, LPP, etc.)
- Impôt à la source
- Certificats de salaire (formulaire 11)
- Déclarations aux caisses de compensation

#### 6. Documents & GED
- Stockage sécurisé Swiss-compliant
- OCR et extraction de données
- Classification automatique
- Versionning
- Recherche full-text
- Watermarking

#### 7. Fiscalité
- Déclarations fiscales entreprises
- Optimisations fiscales
- Reports de pertes
- Réclamations
- Taux d'imposition cantonaux

#### 8. Analytics & Reporting
- Tableaux de bord personnalisables
- KPIs financiers
- Rapports programmés
- Comparaisons de périodes
- Alertes intelligentes
- Exports de données

## 🏗️ Architecture Technique

### Stack Technologique
- **Backend**: Django 4.2 + PostgreSQL 15
- **API**: Django REST Framework
- **Task Queue**: Celery + Redis
- **Storage**: S3-compatible (MinIO)
- **Containerization**: Docker
- **IaC**: Terraform (Hetzner Cloud)
- **Frontend**: Bootstrap 5, Chart.js

### Structure du Projet
```
altiusone/
├── core/                   # Utilisateurs, mandats, clients
├── comptabilite/          # Comptabilité générale
├── tva/                   # Gestion TVA
├── facturation/           # Facturation et time tracking
├── salaires/              # Paie et RH
├── documents/             # GED
├── fiscalite/             # Déclarations fiscales
├── analytics/             # Reporting et analytics
├── templates/             # Templates Django
├── static/                # Assets statiques
├── locale/                # Traductions
└── terraform/             # Infrastructure as Code
```

## 🚀 Installation

### Prérequis
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optionnel)

### Installation locale

1. **Cloner le repository**
```bash
git clone https://github.com/altius/altiusone.git
cd altiusone
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configuration**
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

5. **Créer la base de données**
```bash
createdb altiusone
```

6. **Migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

7. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

8. **Charger les données initiales**
```bash
python manage.py loaddata fixtures/initial_data.json
```

9. **Compiler les traductions**
```bash
python manage.py compilemessages
```

10. **Lancer le serveur**
```bash
python manage.py runserver
```

### Installation avec Docker
```bash
docker-compose up -d
```

## 📊 Utilisation

### Accès à l'application
- Application: http://localhost:8000
- Admin Django: http://localhost:8000/admin
- API: http://localhost:8000/api/

### Créer un premier mandat

1. Se connecter en tant qu'admin
2. Créer un client
3. Créer un mandat pour ce client
4. Configurer le plan comptable
5. Commencer la saisie

## 🧪 Tests
```bash
# Lancer tous les tests
pytest

# Avec coverage
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest core/tests/
pytest comptabilite/tests/
```

## 📝 API Documentation

L'API REST est accessible à `/api/` avec les endpoints suivants:

- `/api/clients/` - Gestion des clients
- `/api/mandats/` - Gestion des mandats
- `/api/comptes/` - Plan comptable
- `/api/ecritures/` - Écritures comptables
- `/api/factures/` - Facturation
- `/api/documents/` - Documents
- etc.

Documentation complète: http://localhost:8000/api/docs/

## 🔒 Sécurité

- Authentification multi-facteurs (2FA)
- Chiffrement des données sensibles
- Isolation des tenants
- Audit logs complets
- Conformité RGPD
- Stockage en Suisse

## 🌍 Internationalisation

L'application supporte 4 langues:
- Français (par défaut)
- Allemand
- Italien
- Anglais

## 📦 Déploiement

### Provisionnement automatique

Le système crée automatiquement:
1. VPS Hetzner Cloud
2. Base PostgreSQL dédiée
3. Storage S3 (MinIO)
4. Configuration DNS
5. Certificats SSL
```bash
cd terraform/
terraform init
terraform plan
terraform apply
```

## 🤝 Contribution

Les contributions sont les bienvenues! Merci de:
1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 License

Copyright (c) 2024 Altius Academy SNC. Tous droits réservés.

## 👥 Contact

- **Email**: support@altiusone.ch
- **Website**: https://altiusone.ch
- **Documentation**: https://docs.altiusone.ch

## 🙏 Remerciements

- Administration Fédérale des Contributions (AFC) pour la documentation TVA
- Swissmedic pour l'API pharmaceutique
- Communauté Django