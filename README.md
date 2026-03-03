# AltiusOne

Plateforme de gestion d'entreprise tout-en-un — comptabilite, facturation, salaires, documents, analytics, IA.

## Branches

Ce repo contient 3 branches paralleles. **Ne jamais merger entre elles.**

| Branche | Usage | Settings | Requirements |
|---|---|---|---|
| `main` | Version cloud (payante, provisionnee par portal/) | `AltiusOne.settings` | `requirements.txt` |
| `desktop` | Version bureau (Electron, PostgreSQL local) | `AltiusOne.settings_desktop` | `requirements_desktop.txt` |
| `community` | Version open-source (AGPL-3.0, repo public) | `AltiusOne.settings_community` | `requirements_community.txt` |

### Differences entre les branches

Chaque branche ne differe de `main` que par quelques fichiers specifiques :

**desktop** (3-4 fichiers) :
- `AltiusOne/settings_desktop.py` — PostgreSQL local, LocMemCache, Celery synchrone
- `requirements_desktop.txt` — Sans Redis, sans Gunicorn, sans GCS

**community** (6-7 fichiers) :
- `AltiusOne/settings_community.py` — Sans Docs, sans Nextcloud, licence AGPL
- `requirements_community.txt` — Sans altiusone-ai SDK, sans GCS
- `docker-compose.yml` — Sans Nextcloud, sans OnlyOffice
- `Dockerfile` — Utilise requirements_community.txt
- `LICENSE`, `CONTRIBUTING.md`, `README.md`, `.env.example`

Le code metier (15 apps Django) est **identique** sur les 3 branches.

## Workflow quotidien

```bash
# Verifier la branche courante AVANT tout commit
git branch --show-current

# Travailler sur la version cloud
git checkout main

# Travailler sur la version desktop
git checkout desktop

# Travailler sur la version community
git checkout community
```

### Propagation des changements metier

Si tu modifies du code metier (apps, templates, static, migrations), il faut le propager aux autres branches :

```bash
# Depuis main, propager un commit vers community
git checkout community
git cherry-pick <commit-hash>
git checkout main

# Depuis main, propager vers desktop
git checkout desktop
git cherry-pick <commit-hash>
git checkout main
```

### Sync vers le repo public community

```bash
# Pousser la branche community vers le repo public
git push community community:main
```

Le remote `community` pointe vers `https://github.com/Altius-rebus-SARL/altiusone-community.git`.

## Demarrage rapide (version cloud)

```bash
# Configurer l'environnement
cp .env.example .env  # ou utiliser le .env genere par portal/

# Lancer tous les services
docker compose up -d

# L'entrypoint gere automatiquement :
# - Extensions PostGIS + pgvector
# - Migrations
# - Collecte des fichiers statiques
# - Chargement des plans comptables (Swiss, OHADA)
# - Init des roles, devises, cotisations, ontologie, PDF templates
```

## Architecture

```
Repo prive (altiusone)          Repo public (altiusone-community)
  main ──── version cloud         main ──── miroir de community
  desktop ── version bureau
  community ─ version AGPL ──────── push ──────────────┘
```

## Repos lies

| Repo | Description |
|---|---|
| `altiusone` (prive) | Ce repo — apps Django (cloud, desktop, community) |
| `altiusone-community` (public) | Miroir de la branche community |
| `portal/` (prive) | Plateforme SaaS, provisioning Terraform/Ansible |
| `mobile/` (prive) | App React Native iOS/Android |
| `desktop/` (prive) | App Electron (CI/CD GitHub Actions) |
