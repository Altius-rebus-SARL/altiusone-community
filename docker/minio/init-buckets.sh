#!/bin/bash
# =============================================================================
# MinIO Bucket Initialization Script
# =============================================================================
# This script creates the necessary buckets in MinIO for AltiusOne.
# It runs once when MinIO starts for the first time.
# =============================================================================

set -e

# Wait for MinIO to be ready
echo "Waiting for MinIO to be ready..."
until mc alias set local http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD} > /dev/null 2>&1; do
    echo "MinIO not ready, retrying..."
    sleep 2
done
echo "MinIO is ready!"

# Create the main media bucket
BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME:-altiusone-media}
echo "Creating bucket: ${BUCKET_NAME}..."

mc mb --ignore-existing local/${BUCKET_NAME}

# Set public policy for the media bucket (public read access for media files)
mc anonymous set download local/${BUCKET_NAME}

# List buckets to verify
echo "Created buckets:"
mc ls local/

echo "MinIO initialization complete!"
