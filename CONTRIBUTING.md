# Contributing to AltiusOne

Thank you for your interest in contributing to AltiusOne! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ with PostGIS and pgvector extensions
- Redis 7+
- Docker & Docker Compose (recommended)

### Development Setup with Docker (recommended)

```bash
# Clone the repository
git clone https://github.com/Altius-rebus-SARL/altiusone.git
cd altiusone

# Copy environment config
cp .env.example .env

# Start all services
docker compose up -d

# Run migrations
docker compose exec django python manage.py migrate

# Create your admin user
docker compose exec django python manage.py createsuperuser

# Load initial data
docker compose exec django python manage.py loaddata fixtures/initial_data.json

# Compile translations
docker compose exec django python manage.py compilemessages

# Access the app at http://localhost:8011
```

### Development Setup without Docker

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements_community.txt

# Set up PostgreSQL with extensions
# (requires PostGIS and pgvector installed on your system)
createdb altiusone
psql altiusone -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql altiusone -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Copy and edit environment config
cp .env.example .env
# Edit .env: set DATABASE_URL, disable USE_S3, etc.

# Run migrations and start
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Project Structure

```
altiusone/
├── AltiusOne/          # Django project settings
├── core/               # Users, mandats, clients, permissions
├── comptabilite/       # General accounting (chart of accounts, entries)
├── tva/                # VAT management (Swiss-specific)
├── facturation/        # Invoicing, time tracking, QR-bills
├── salaires/           # Payroll & HR (Swiss social contributions)
├── documents/          # Document management (GED), OCR
├── fiscalite/          # Tax declarations
├── analytics/          # Dashboards, KPIs, reports
├── mailing/            # Email campaigns
├── editeur/            # Document editor integration
├── chat/               # AI chat (optional)
├── modelforms/         # Dynamic form generation
├── projets/            # Project management, Gantt
├── graph/              # Relational graph (ontology, anomaly detection)
├── import_export/      # Data import/export
├── mcp/                # MCP server (Model Context Protocol)
├── templates/          # Django templates (Bootstrap 5 + HTMX)
├── static/             # Static assets (JS, CSS, images)
└── locale/             # Translations (FR, DE, IT, EN)
```

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/Altius-rebus-SARL/altiusone/issues) first
2. Create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, browser)

### Suggesting Features

Open an issue with the `enhancement` label. Describe the use case, not just the solution.

### Submitting Code

1. Fork the repository
2. Create a feature branch from `community`:
   ```bash
   git checkout -b feature/your-feature community
   ```
3. Write your code following our conventions (see below)
4. Add or update tests as needed
5. Test in Docker before submitting:
   ```bash
   docker compose exec django pytest
   ```
6. Submit a Pull Request against the `community` branch

### Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Include a clear description of what and why
- Reference related issues (`Fixes #123`)
- Make sure tests pass
- Update translations if you change user-facing strings

## Code Conventions

### General

- **Language**: Code, variables, and function names in English
- **Comments/docstrings**: English preferred, French accepted for Swiss-specific business logic
- **No Django Admin**: All UI is in templates/views, never in admin.py
- **Services pattern**: Business logic in `app/services/`, not in views or models
- **Lazy imports**: Import services inside methods that use them, not at module level

### Python

- Follow PEP 8
- Use type hints for function signatures
- Keep views thin — delegate to services

### Templates

- Bootstrap 5 + HTMX
- Use Django template inheritance (`{% extends %}`)
- Use `{% trans %}` / `{% blocktrans %}` for all user-facing strings

### Swiss-Specific

- Number formatting: apostrophe as thousands separator (`1'234.56`)
- Currency: always specify (CHF, EUR, XOF, etc.)
- Dates: `dd.mm.yyyy` format for Swiss context

### Testing

```bash
# Run all tests
docker compose exec django pytest

# With coverage
docker compose exec django pytest --cov=. --cov-report=html

# Specific app
docker compose exec django pytest comptabilite/tests/
```

## Translations

AltiusOne supports 4 languages: French, German, Italian, and English.

```bash
# Extract new strings
docker compose exec django python manage.py makemessages -l fr -l de -l it -l en

# Edit .po files in locale/<lang>/LC_MESSAGES/

# Compile
docker compose exec django python manage.py compilemessages
```

## AI Integration (Optional)

AltiusOne works fully without AI. To add AI capabilities:

1. **MCP Server** (`mcp/`): Exposes data via Model Context Protocol — connect any LLM (Claude, GPT, Ollama, etc.)
2. **AI Service** (`documents/ai_service.py`): Point `AI_API_URL` to any OpenAI-compatible API for OCR, embeddings, and chat

## License

By contributing, you agree that your contributions will be licensed under the [AGPL-3.0 License](LICENSE).

## Questions?

- Open an issue for technical questions
- Email: support@altiusone.ch
