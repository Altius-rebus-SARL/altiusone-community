# apps/Dockerfile
FROM python:3.12-bookworm

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 

# Installation des dépendances système en une seule couche
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash build-essential gcc g++ make libffi-dev libssl-dev \
    zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
    wget curl git git-lfs unzip \
    poppler-utils libmagic1 libzbar0 libzbar-dev \
    gdal-bin libgdal-dev postgresql-client mariadb-client \
    libmariadb-dev nodejs npm netcat-openbsd \
    libgl1-mesa-dev libaio1 default-jdk wkhtmltopdf \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-ita \
    libtesseract-dev \
    && git lfs install \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Vérifier l'installation de Tesseract
RUN tesseract --version && tesseract --list-langs
# Mise à jour pip
RUN pip install --no-cache-dir --upgrade pip

# Création des répertoires
RUN mkdir -p /app/models /app/logs 

WORKDIR /app

# Copier et installer les dépendances Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'entrypoint et l'application
COPY entrypoint.sh ./
COPY . .

# Configuration finale des permissions
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]



