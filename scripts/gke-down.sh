#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../.tls-backup"

echo "=== Backing up TLS secret ==="
mkdir -p "$BACKUP_DIR"
if kubectl get secret eshop-test-wildcard-tls &>/dev/null; then
    kubectl get secret eshop-test-wildcard-tls -o yaml \
        | grep -v 'resourceVersion\|uid\|creationTimestamp\|namespace' \
        > "$BACKUP_DIR/eshop-test-wildcard-tls.yaml"
    echo "TLS secret backed up to $BACKUP_DIR/eshop-test-wildcard-tls.yaml"
else
    echo "No TLS secret found, skipping backup"
fi

echo "=== Deleting GKE cluster ==="
gcloud container clusters delete eshop-cluster \
    --region europe-west3 \
    --project eshop-test-485206 \
    --quiet
