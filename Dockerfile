# apps/Dockerfile
# Multi-stage build pour réduire la taille de l'image finale

# =============================================================================
# Stage 1: Builder - Compilation des dépendances
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dépendances de compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    # Pour pycairo et graphiques
    pkg-config \
    libcairo2-dev \
    # Pour Pillow
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    # Pour lxml
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Créer un virtualenv pour isoler les dépendances
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt

# Pré-télécharger le modèle d'embedding dans l'image (évite téléchargement au runtime)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2', cache_folder='/opt/models')"

# =============================================================================
# Stage 2: Runtime - Image finale légère
# =============================================================================
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Tesseract
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata \
    # Sentence-transformers model cache (pré-téléchargé au build)
    SENTENCE_TRANSFORMERS_HOME=/opt/models \
    # Désactiver CUDA (CPU only)
    CUDA_VISIBLE_DEVICES=""

# Dépendances runtime uniquement (pas de compilateurs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client
    libpq5 \
    postgresql-client \
    # GDAL pour GeoDjango/PostGIS
    gdal-bin \
    libgdal32 \
    # PDF processing
    poppler-utils \
    wkhtmltopdf \
    # Image processing
    libmagic1 \
    libgl1 \
    libjpeg62-turbo \
    libpng16-16 \
    # Cairo runtime
    libcairo2 \
    # QR Code
    libzbar0 \
    # OCR - Tesseract
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-ita \
    # Networking
    netcat-openbsd \
    curl \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copier le virtualenv et le modèle d'embedding depuis le builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/models /opt/models

# Créer les répertoires de l'application
RUN mkdir -p /app/models /app/logs /app/staticfiles /app/media

WORKDIR /app

# Copier l'application
COPY entrypoint.sh ./
COPY . .

# Permissions
RUN chmod +x entrypoint.sh

# Vérifications
RUN python --version && tesseract --version

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
