# AltiusOne Community Edition

Open-source business management platform for SMEs, accounting firms, and enterprises.

Built with Django 6, PostgreSQL, Bootstrap 5 + HTMX.

## Features

- **Accounting** — Swiss & OHADA charts of accounts, journal entries, trial balance, financial statements
- **Invoicing** — Quotes, invoices, Swiss QR-bills, time tracking, payment management
- **Payroll** — Employee management, salary slips, Swiss social contributions, certificates
- **VAT** — VAT declarations, rates, reconciliation (Swiss-compliant)
- **Tax** — Tax declarations, corrections, multi-regime support
- **Documents** — Document management (GED), OCR, full-text + semantic search
- **Analytics** — Dashboards, KPIs, custom reports, data export
- **Projects** — Project management, task tracking, Gantt charts
- **Graph** — Relational knowledge graph, anomaly detection, ontology management
- **Email** — Campaign management, SMTP configuration, templates
- **MCP Server** — Model Context Protocol endpoint for connecting any LLM
- **API** — Full REST API with JWT authentication, OpenAPI documentation
- **Multi-language** — French, German, Italian, English

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Altius-rebus-SARL/altiusone-community.git
cd altiusone-community

# Copy environment config
cp .env.example .env
# Edit .env — change passwords!

# Start all services
docker compose up -d

# Run migrations and create admin user
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser

# Access the app
open http://localhost:8011
```

## Architecture

```
Services (Docker Compose):
  django        Django 6 + Gunicorn (port 8011)
  postgres      PostgreSQL 15 + PostGIS + pgvector
  redis         Cache + Celery broker
  celery        Background task worker
  celery-beat   Scheduled tasks
  minio         S3-compatible object storage
  nginx         Reverse proxy
```

## AI Integration (Optional)

AltiusOne works fully without AI. To add AI capabilities:

1. **MCP Server** — The built-in MCP endpoint (`/mcp/`) lets you connect any LLM (Claude, GPT, Ollama, etc.) to your business data
2. **OpenAI-compatible API** — Set `AI_API_URL` and `AI_API_KEY` in `.env` to enable OCR, embeddings, and AI chat via any compatible API (Ollama, vLLM, LiteLLM)

## Community vs Cloud

| | Community (this repo) | Cloud |
|---|---|---|
| Core business apps | All 15 modules | All 15 modules |
| Self-hosted | Docker Compose | Managed hosting |
| AI | BYO via MCP / API | Integrated AI service |
| Collaboration | - | Nextcloud + OnlyOffice |
| Provisioning | Manual | Automated (Terraform) |
| Support | Community (GitHub Issues) | Professional support |
| License | AGPL-3.0 | Proprietary |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code conventions, and how to submit pull requests.

```bash
# Install dependencies (without Docker)
pip install -r requirements_community.txt

# Run with community settings
DJANGO_SETTINGS_MODULE=AltiusOne.settings_community python manage.py runserver
```

## License

[AGPL-3.0](LICENSE) — Free to use, modify, and distribute. If you modify and deploy AltiusOne as a service, you must share your changes under the same license.

## Links

- **Cloud Edition**: [altiusone.ch](https://altiusone.ch)
- **Issues**: [GitHub Issues](https://github.com/Altius-rebus-SARL/altiusone-community/issues)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
