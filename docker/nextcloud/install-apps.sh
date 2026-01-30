#!/bin/bash
# =============================================================================
# Nextcloud Apps Installation Script
# =============================================================================
# This script installs essential Nextcloud apps for AltiusOne workspace.
# =============================================================================

set -e

echo "========================================"
echo "Nextcloud Apps Installation"
echo "========================================"

# Helper function to run occ commands as www-data
run_occ() {
    su -s /bin/sh www-data -c "php /var/www/html/occ $*"
}

echo ""
echo "Installing apps..."
echo "----------------------------------------"

# =============================================================================
# COLLABORATION & OFFICE
# =============================================================================

echo "[1/12] Installing OnlyOffice (Office suite)..."
run_occ app:install onlyoffice || echo "onlyoffice already installed"
run_occ app:enable onlyoffice || true

echo "[2/12] Installing Talk (chat & video)..."
run_occ app:install spreed || echo "spreed already installed"
run_occ app:enable spreed || true

echo "[3/12] Installing Deck (Kanban boards)..."
run_occ app:install deck || echo "deck already installed"
run_occ app:enable deck || true

echo "[4/12] Installing Forms..."
run_occ app:install forms || echo "forms already installed"
run_occ app:enable forms || true

# =============================================================================
# GROUPWARE
# =============================================================================

echo "[5/12] Installing Calendar..."
run_occ app:install calendar || echo "calendar already installed"
run_occ app:enable calendar || true

echo "[6/12] Installing Contacts..."
run_occ app:install contacts || echo "contacts already installed"
run_occ app:enable contacts || true

echo "[7/12] Installing Mail..."
run_occ app:install mail || echo "mail already installed"
run_occ app:enable mail || true

echo "[8/12] Installing Tasks..."
run_occ app:install tasks || echo "tasks already installed"
run_occ app:enable tasks || true

# =============================================================================
# SSO & STORAGE
# =============================================================================

echo "[9/12] Installing User OIDC (SSO)..."
run_occ app:install user_oidc || echo "user_oidc already installed"
run_occ app:enable user_oidc || true

echo "[10/12] Installing External Storage..."
run_occ app:install files_external || echo "files_external already installed"
run_occ app:enable files_external || true

echo "[11/12] Installing Group Folders..."
run_occ app:install groupfolders || echo "groupfolders already installed"
run_occ app:enable groupfolders || true

# =============================================================================
# CLEANUP
# =============================================================================

echo "[12/12] Removing unnecessary apps..."
run_occ app:disable firstrunwizard || true
run_occ app:disable recommendations || true
run_occ app:disable weather_status || true

echo ""
echo "========================================"
echo "Apps installation complete!"
echo "========================================"
run_occ app:list --enabled | head -20
