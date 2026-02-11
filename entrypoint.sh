#!/bin/bash
set -e

# Définir un environnement par défaut si non spécifié
: ${ENVIRONMENT:="production"}
echo "Running in $ENVIRONMENT environment"

# Fonction pour initialiser une base de données avec PostGIS
init_postgis_db() {
    local db_name=$1
    echo "Initializing PostGIS for database: $db_name"
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$db_name" -c "CREATE EXTENSION IF NOT EXISTS postgis;"
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$db_name" -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$db_name" -c "CREATE EXTENSION IF NOT EXISTS postgis_sfcgal;"
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$db_name" -c "CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;"
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$db_name" -c "CREATE EXTENSION IF NOT EXISTS address_standardizer;"

    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$db_name" -c "CREATE EXTENSION IF NOT EXISTS vector;"

    echo "✓ All extensions created successfully"
}


# Attendre que la base de données soit prête avec timeout
echo "Waiting for PostgreSQL to be ready..."
RETRY_COUNT=0
MAX_RETRIES=60

while ! PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "❌ Failed to connect to PostgreSQL after $MAX_RETRIES attempts"
    exit 1
  fi
  >&2 echo "Postgres is unavailable - sleeping (attempt $RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done
>&2 echo "✓ Postgres is up - executing command"

# Créer l'extension PostGIS
init_postgis_db "$POSTGRES_DB"

# # Setup FastVLM (seulement pour le service principal Django, pas Celery)
# if [ "${SETUP_FASTVLM:-true}" = "true" ]; then
#     setup_fastvlm
# fi

# Création des répertoires nécessaires
echo "Creating necessary directories..."
mkdir -p /app/staticfiles
mkdir -p /app/media
mkdir -p /app/media/tmp
mkdir -p /app/media/outputs

# Appliquer les permissions correctes
echo "Setting permissions..."
chmod -R 755 /app/staticfiles
chmod -R 755 /app/media
chown -R nobody:nogroup /app/staticfiles 2>/dev/null || true
chown -R nobody:nogroup /app/media 2>/dev/null || true

# Collecter les fichiers statiques
echo "Collecting static files..."
if [ "$ENVIRONMENT" = "production" ]; then
    # En production, toujours collecter pour s'assurer que les fichiers sont à jour
    python manage.py collectstatic --noinput
elif [ "$FORCE_COLLECTSTATIC" = "true" ]; then
    # Force la collecte avec effacement
    python manage.py collectstatic --noinput --clear
elif [ -d "/app/staticfiles" ] && [ "$(ls -A /app/staticfiles 2>/dev/null)" ]; then
    # En développement, si le répertoire existe et n'est pas vide, on ignore
    echo "Static files directory already exists and is not empty. Skipping collection."
    echo "Set FORCE_COLLECTSTATIC=true to force collection."
else
    # Premier démarrage ou répertoire vide
    python manage.py collectstatic --noinput
fi

if [ $? -ne 0 ]; then
    echo "❌ Failed to collect static files. Exiting."
    exit 1
fi

# === GESTION DES MIGRATIONS ===

# Vérifier si la base est vide (première exécution)
DB_HAS_TABLES=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
DB_HAS_TABLES=$(echo $DB_HAS_TABLES | xargs)  # Trim

FIRST_RUN=false
if [ "$DB_HAS_TABLES" = "0" ] || [ "$FORCE_INIT" = "true" ]; then
    echo "First run detected or forced initialization"
    FIRST_RUN=true
fi

# En développement, on peut réinitialiser les migrations si demandé
if [ "$ENVIRONMENT" = "development" ] && [ "$RESET_MIGRATIONS" = "true" ]; then
    echo "Development environment with RESET_MIGRATIONS=true, resetting migrations..."
    find . -path "*/migrations/*.py" -not -name "__init__.py" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
fi

# En développement uniquement, créer les migrations manquantes
if [ "$ENVIRONMENT" = "development" ]; then
    echo "Creating any missing migrations (development only)..."
    python manage.py makemigrations
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create migrations. Exiting."
        exit 1
    fi
else
    echo "Skipping makemigrations in production (migrations should be committed to repo)"
fi

echo "Applying migrations..."
python manage.py migrate --noinput

if [ $? -ne 0 ]; then
    echo "❌ Failed to apply migrations. Exiting."
    exit 1
fi

echo "✓ Migrations applied successfully."

#======= commande ========
echo "Load setup swiss chart of accounts (if empty)"
python manage.py load_swiss_chart_of_accounts || echo "Warning: Chart of accounts loading failed, continuing..."

echo "Load modelforms default templates"
python manage.py create_default_templates || echo "Warning: Default templates loading failed, continuing..."

echo "Setup OIDC clients (Nextcloud, MinIO)"
python manage.py setup_oidc_clients || echo "Warning: OIDC clients setup failed, continuing..."

echo "Setup commands done"


# === DEMARRAGE DU SERVEUR ===

echo "✓ Starting server..."
if [ "$ENVIRONMENT" = "production" ]; then
    # Production: utiliser Gunicorn pour de meilleures performances
    exec gunicorn AltiusOne.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers ${GUNICORN_WORKERS:-4} \
        --threads ${GUNICORN_THREADS:-2} \
        --timeout ${GUNICORN_TIMEOUT:-120} \
        --access-logfile - \
        --error-logfile - \
        --capture-output \
        --enable-stdio-inheritance
else
    # Développement: utiliser le serveur Django avec rechargement automatique
    exec python manage.py runserver 0.0.0.0:8000
fi