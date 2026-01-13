#!/bin/bash
# =============================================================================
# Script de build et push des images Docs pour AltiusOne
# =============================================================================
# Usage:
#   ./scripts/build-docs-images.sh              # Build seulement
#   ./scripts/build-docs-images.sh --push       # Build et push
#   ./scripts/build-docs-images.sh --version 1.0.0 --push  # Avec version
#
# Variables d'environnement:
#   DOCS_REGISTRY  - Registry Docker (défaut: ghcr.io/altiusone)
#   DOCS_VERSION   - Version/tag des images (défaut: latest)
# =============================================================================

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration par défaut
REGISTRY="${DOCS_REGISTRY:-ghcr.io/altiusone}"
VERSION="${DOCS_VERSION:-latest}"
PUSH=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --push              Push images to registry after build"
            echo "  --version VERSION   Tag images with VERSION (default: latest)"
            echo "  --registry REGISTRY Use custom registry (default: ghcr.io/altiusone)"
            echo "  --help              Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AltiusOne Docs - Image Builder${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Registry:${NC} $REGISTRY"
echo -e "${YELLOW}Version:${NC}  $VERSION"
echo -e "${YELLOW}Push:${NC}     $PUSH"
echo ""

cd "$PROJECT_DIR"

# Vérifier que docs-suite existe
if [ ! -d "docs-suite" ]; then
    echo -e "${RED}Erreur: Le dossier docs-suite n'existe pas!${NC}"
    echo "Clonez d'abord le repo: git clone https://github.com/suitenumerique/docs docs-suite"
    exit 1
fi

# Export des variables pour docker-compose
export DOCS_REGISTRY="$REGISTRY"
export DOCS_VERSION="$VERSION"

# Liste des services à builder
SERVICES=("docs-api" "docs-frontend" "docs-yprovider")

# Build des images
echo -e "${GREEN}>>> Building images...${NC}"
echo ""

for service in "${SERVICES[@]}"; do
    echo -e "${YELLOW}Building $service...${NC}"
    docker compose -f docker-compose.docs.build.yml build "$service"
    echo -e "${GREEN}✓ $service built successfully${NC}"
    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  All images built successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Afficher les images créées
echo -e "${YELLOW}Images créées:${NC}"
docker images | grep -E "docs-(api|frontend|yprovider)" | head -10 || true
echo ""

# Push si demandé
if [ "$PUSH" = true ]; then
    echo -e "${GREEN}>>> Pushing images to $REGISTRY...${NC}"
    echo ""

    # Login check
    echo -e "${YELLOW}Vérification de l'authentification au registry...${NC}"

    for service in "${SERVICES[@]}"; do
        IMAGE="$REGISTRY/$service:$VERSION"
        echo -e "${YELLOW}Pushing $IMAGE...${NC}"
        docker push "$IMAGE"
        echo -e "${GREEN}✓ $IMAGE pushed successfully${NC}"

        # Si version != latest, pusher aussi avec tag latest
        if [ "$VERSION" != "latest" ]; then
            LATEST_IMAGE="$REGISTRY/$service:latest"
            echo -e "${YELLOW}Tagging and pushing $LATEST_IMAGE...${NC}"
            docker tag "$IMAGE" "$LATEST_IMAGE"
            docker push "$LATEST_IMAGE"
            echo -e "${GREEN}✓ $LATEST_IMAGE pushed successfully${NC}"
        fi
        echo ""
    done

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  All images pushed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
fi

echo ""
echo -e "${BLUE}Pour utiliser ces images en production:${NC}"
echo "  export DOCS_REGISTRY=$REGISTRY"
echo "  export DOCS_VERSION=$VERSION"
echo "  docker compose -f docker-compose.yml -f docker-compose.docs.yml up -d"
echo ""
