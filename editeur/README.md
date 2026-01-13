# Éditeur Collaboratif - AltiusOne

Intégration de **Docs** (La Suite Numérique - projet Franco-Allemand DINUM/ZenDiS) dans AltiusOne pour l'édition collaborative en temps réel.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AltiusOne Stack                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐ │
│  │   Django    │   │  Docs API   │   │Docs Frontend│   │  HocusPocus │ │
│  │  AltiusOne  │◄──┤   (DRF)     │◄──┤  (Next.js)  │◄──┤ (WebSocket) │ │
│  │  Port 8000  │   │  Port 8072  │   │  Port 3000  │   │  Port 4444  │ │
│  └──────┬──────┘   └──────┬──────┘   └─────────────┘   └─────────────┘ │
│         │                 │                                             │
│         │    JWT/SSO      │                                             │
│         └────────────────►│                                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    Services partagés                                ││
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                          ││
│  │  │PostgreSQL│  │  Redis   │  │  Minio   │                          ││
│  │  │ + pgvec  │  │  Cache   │  │    S3    │                          ││
│  │  └──────────┘  └──────────┘  └──────────┘                          ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

## Fonctionnalités

- **Édition collaborative temps réel** - Plusieurs utilisateurs peuvent éditer simultanément
- **Synchronisation automatique** - Via CRDT (Yjs) et WebSocket (HocusPocus)
- **Export multi-format** - PDF, Word (.docx), OpenDocument (.odt), Markdown
- **Modèles de documents** - Templates réutilisables par catégorie
- **Intégration GED** - Archivage dans la GED AltiusOne
- **Partage flexible** - Par utilisateur ou lien public avec permissions
- **Souveraineté totale** - Auto-hébergé, données en local

## Installation

### 1. Démarrer les services Docs

```bash
# Depuis le répertoire apps/
docker compose -f docker-compose.yml -f docker-compose.docs.yml up -d
```

### 2. Variables d'environnement

Ajouter dans `.env` :

```env
# Docs - La Suite Numérique
DOCS_API_URL=http://docs-api:8072
DOCS_FRONTEND_URL=http://localhost:3000
DOCS_API_KEY=your-secure-api-key
DOCS_WEBHOOK_SECRET=your-webhook-secret

# Minio (stockage S3)
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=minio123
```

### 3. Migrations Django

```bash
docker compose exec django python manage.py migrate editeur
```

### 4. Accéder à l'éditeur

- **Dashboard éditeur** : `http://localhost:8011/fr/editeur/`
- **API** : `http://localhost:8011/api/v1/editeur/`
- **Console Minio** : `http://localhost:9001`

## Structure de l'application

```
editeur/
├── models.py           # DocumentCollaboratif, PartageDocument, etc.
├── views.py            # Vues web (dashboard, édition, partage)
├── api_views.py        # API REST (ViewSets)
├── serializers.py      # Serializers DRF
├── docs_service.py     # Client API vers Docs
├── forms.py            # Formulaires Django
├── urls.py             # URLs web
├── api_urls.py         # URLs API
├── admin.py            # Configuration admin
├── signals.py          # Signaux de synchronisation
└── templates/editeur/  # Templates HTML
```

## Modèles de données

### DocumentCollaboratif
Document collaboratif lié à Docs avec métadonnées AltiusOne.

| Champ | Type | Description |
|-------|------|-------------|
| `docs_id` | CharField | ID du document dans Docs |
| `titre` | CharField | Titre du document |
| `type_document` | Choice | NOTE, RAPPORT, PV, COURRIER, etc. |
| `statut` | Choice | BROUILLON, EN_COURS, REVISION, VALIDE, ARCHIVE |
| `mandat` | ForeignKey | Mandat AltiusOne associé |
| `createur` | ForeignKey | Utilisateur créateur |

### PartageDocument
Partage d'un document avec un utilisateur.

| Champ | Type | Description |
|-------|------|-------------|
| `document` | ForeignKey | Document partagé |
| `utilisateur` | ForeignKey | Utilisateur destinataire |
| `niveau_acces` | Choice | LECTURE, COMMENTAIRE, EDITION, ADMIN |

### ModeleDocument
Modèle (template) réutilisable.

## API REST

### Documents

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/editeur/documents/` | Liste des documents |
| POST | `/api/v1/editeur/documents/` | Créer un document |
| GET | `/api/v1/editeur/documents/{id}/` | Détail |
| POST | `/api/v1/editeur/documents/{id}/share/` | Partager |
| POST | `/api/v1/editeur/documents/{id}/export/` | Exporter |
| POST | `/api/v1/editeur/documents/{id}/archive_ged/` | Archiver dans GED |

### Token d'édition

```bash
GET /api/v1/editeur/documents/{id}/token/
```

Retourne un token JWT pour l'édition dans l'iframe Docs.

## Intégration avec la GED

L'app `editeur` s'intègre avec l'app `documents` existante :

1. **Lien au dossier** - Un document collaboratif peut être lié à un dossier GED
2. **Archivage** - Export PDF et stockage dans la GED avec indexation IA
3. **Référence** - Le document GED garde une référence vers la source collaborative

## Webhook Docs → AltiusOne

Endpoint : `/editeur/webhook/docs/`

Événements gérés :
- `document.updated` - Mise à jour du document
- `session.started` - Début d'édition
- `session.ended` - Fin d'édition

## Sécurité

- **Authentification** - JWT partagé entre AltiusOne et Docs
- **Autorisation** - Vérification des permissions à chaque requête
- **Chiffrement** - HTTPS obligatoire en production
- **Sandbox iframe** - Restrictions CSP pour l'intégration

## Développement

### Lancer en développement

```bash
# Backend Django
python manage.py runserver

# Docs (séparé)
cd docs && make run
```

### Tests

```bash
python manage.py test editeur
```

## Références

- [Docs - La Suite Numérique](https://github.com/suitenumerique/docs)
- [BlockNote.js](https://www.blocknotejs.org/)
- [Yjs - CRDT](https://yjs.dev/)
- [HocusPocus](https://tiptap.dev/hocuspocus)

## Licence

MIT - Projet souverain auto-hébergé.
