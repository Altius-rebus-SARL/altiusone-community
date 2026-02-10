#!/bin/bash
# =============================================================================
# Nextcloud Configuration Script
# =============================================================================
# This script configures Nextcloud settings after initial installation.
# It sets up performance optimizations, security settings, S3 and OIDC integration.
# =============================================================================

set -e

echo "========================================"
echo "Nextcloud Configuration"
echo "========================================"

# Helper function to run occ commands as www-data
run_occ() {
    su -s /bin/sh www-data -c "php /var/www/html/occ $*"
}

echo "Applying configuration..."

# =============================================================================
# AltiusOne Theme Configuration
# =============================================================================

# Enable AltiusOne custom theme if it exists
if [ -d "/var/www/html/themes/altiusone" ]; then
    echo "Enabling AltiusOne custom theme..."
    run_occ config:system:set theme --value='altiusone'
    echo "AltiusOne theme enabled"
else
    echo "AltiusOne theme not found, using default theme"
fi

# =============================================================================
# Performance Optimizations
# =============================================================================

echo "Configuring performance optimizations..."

# Enable APCu for local caching
run_occ config:system:set memcache.local --value='\OC\Memcache\APCu'

# Enable Redis for distributed caching and locking (reuses AltiusOne Redis)
run_occ config:system:set memcache.distributed --value='\OC\Memcache\Redis'
run_occ config:system:set memcache.locking --value='\OC\Memcache\Redis'
run_occ config:system:set redis host --value="${REDIS_HOST:-redis}"
run_occ config:system:set redis port --value='6379'
run_occ config:system:set redis dbindex --value='1'

# =============================================================================
# Security Settings
# =============================================================================

echo "Configuring security settings..."

# Set default phone region (Switzerland)
run_occ config:system:set default_phone_region --value='CH'

# Set trusted proxies for Docker networks
run_occ config:system:set trusted_proxies 0 --value='172.16.0.0/12'
run_occ config:system:set trusted_proxies 1 --value='192.168.0.0/16'
run_occ config:system:set trusted_proxies 2 --value='10.0.0.0/8'

# Enable HTTPS enforcement (when behind reverse proxy)
run_occ config:system:set overwriteprotocol --value='https'

# =============================================================================
# File Handling
# =============================================================================

echo "Configuring file handling..."

# Set default quota (10GB)
run_occ config:app:set files default_quota --value='10 GB'

# Enable big file chunking
run_occ config:system:set max_chunk_size --value='0'

# =============================================================================
# S3 External Storage Configuration (MinIO)
# =============================================================================

if [ -n "${MINIO_ENDPOINT}" ] && [ -n "${MINIO_ACCESS_KEY}" ] && [ -n "${MINIO_SECRET_KEY}" ]; then
    echo "Configuring MinIO external storage..."

    # Enable external storage
    run_occ app:enable files_external || true

    # Check if external storage already exists
    EXISTING_STORAGE=$(run_occ files_external:list --all 2>/dev/null | grep -c "Documents AltiusOne" || echo "0")

    if [ "$EXISTING_STORAGE" = "0" ]; then
        # Add MinIO as S3 external storage
        echo "Creating MinIO external storage mount..."
        su -s /bin/sh www-data -c "php /var/www/html/occ files_external:create \
            'Documents AltiusOne' \
            amazons3 \
            amazons3::accesskey \
            -c bucket='${MINIO_BUCKET:-altiusone-media}' \
            -c hostname='${MINIO_ENDPOINT:-minio}' \
            -c port='${MINIO_PORT:-9000}' \
            -c use_ssl=false \
            -c use_path_style=true \
            -c region='us-east-1' \
            -c key='${MINIO_ACCESS_KEY}' \
            -c secret='${MINIO_SECRET_KEY}'" \
            || echo "External storage creation failed or already exists"
    else
        echo "MinIO external storage already configured"
    fi
else
    echo "MinIO not configured (MINIO_ENDPOINT, MINIO_ACCESS_KEY, or MINIO_SECRET_KEY not set)"
fi

# =============================================================================
# Background Jobs
# =============================================================================

echo "Configuring background jobs..."
run_occ background:cron

# =============================================================================
# OIDC Configuration (AltiusOne SSO)
# =============================================================================

if [ -n "${OIDC_PROVIDER_URL}" ] && [ -n "${OIDC_CLIENT_ID}" ] && [ -n "${OIDC_CLIENT_SECRET}" ]; then
    echo "Configuring OIDC authentication with AltiusOne..."

    # Enable user_oidc app
    run_occ app:enable user_oidc || true

    # Create or update OIDC provider for AltiusOne
    echo "Creating/updating OIDC provider 'AltiusOne'..."
    su -s /bin/sh www-data -c "php /var/www/html/occ user_oidc:provider 'AltiusOne' \
        --clientid='${OIDC_CLIENT_ID}' \
        --clientsecret='${OIDC_CLIENT_SECRET}' \
        --discoveryuri='${OIDC_PROVIDER_URL}/o/.well-known/openid-configuration' \
        --mapping-uid='sub' \
        --mapping-email='email' \
        --mapping-display-name='name'" \
        || echo "OIDC provider configuration completed with warnings"

    # Allow multiple user backends (OIDC + local)
    run_occ config:app:set user_oidc allow_multiple_user_backends --value='1' || true

    echo "OIDC configuration complete!"
else
    echo "OIDC not configured (OIDC_PROVIDER_URL, OIDC_CLIENT_ID, or OIDC_CLIENT_SECRET not set)"
fi

# =============================================================================
# OnlyOffice Document Server Configuration
# =============================================================================

run_occ app:enable onlyoffice 2>/dev/null || true
if run_occ app:list --enabled 2>/dev/null | grep -q "onlyoffice"; then
    echo "Configuring OnlyOffice Document Server..."

    # Set the public Document Server URL (for browser access)
    # This will be configured via environment variable or default to internal URL
    ONLYOFFICE_URL=${ONLYOFFICE_PUBLIC_URL:-http://localhost:9980/}
    run_occ config:app:set onlyoffice DocumentServerUrl --value="${ONLYOFFICE_URL}" || true

    # Set internal Document Server URL (for container-to-container communication)
    run_occ config:app:set onlyoffice DocumentServerInternalUrl --value='http://altiusone_onlyoffice/' || true

    # Set the Storage URL (Nextcloud URL for OnlyOffice callbacks)
    run_occ config:app:set onlyoffice StorageUrl --value='http://altiusone_nextcloud/' || true

    # Configure JWT if secret is set
    if [ -n "${ONLYOFFICE_JWT_SECRET}" ]; then
        run_occ config:app:set onlyoffice jwt_secret --value="${ONLYOFFICE_JWT_SECRET}" || true
    fi

    echo "OnlyOffice configuration complete!"
else
    echo "onlyoffice app not enabled, skipping OnlyOffice configuration"
fi

echo ""
echo "========================================"
echo "Nextcloud configuration complete!"
echo "========================================"

# Show current configuration
echo "Current Nextcloud status:"
run_occ status
