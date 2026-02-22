#!/usr/bin/env bash
set -euo pipefail

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
    echo "ERROR: CLOUDFLARE_API_TOKEN is not set"
    exit 1
fi

PROJECT="eshop-test-485206"
CLUSTER="eshop-cluster"
REGION="europe-west3"
ZONE="europe-west3-a"
STATIC_IP="34.159.106.171"

echo "=== Creating GKE cluster ==="
gcloud container clusters create "$CLUSTER" \
    --project "$PROJECT" \
    --region "$REGION" \
    --node-locations "$ZONE" \
    --machine-type e2-standard-2 \
    --disk-type pd-standard \
    --disk-size 30 \
    --num-nodes 3 \
    --enable-autoscaling \
    --total-min-nodes 3 --total-max-nodes 4 \
    --enable-autorepair \
    --enable-autoupgrade \
    --workload-pool="$PROJECT.svc.id.goog"

echo "=== Creating wearables node pool ==="
gcloud container node-pools create wearables-pool \
    --cluster "$CLUSTER" \
    --project "$PROJECT" \
    --region "$REGION" \
    --node-locations "$ZONE" \
    --machine-type e2-standard-2 \
    --disk-type pd-standard \
    --disk-size 30 \
    --num-nodes 2 \
    --enable-autoscaling \
    --total-min-nodes 2 \
    --total-max-nodes 4 \
    --enable-autorepair \
    --enable-autoupgrade

echo "=== Getting cluster credentials ==="
gcloud container clusters get-credentials "$CLUSTER" \
    --region "$REGION" \
    --project "$PROJECT"

echo "=== Installing cert-manager ==="
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.19.3/cert-manager.yaml

echo "=== Waiting for cert-manager to be ready ==="
kubectl wait --for=condition=Available deployment --all \
    -n cert-manager --timeout=120s

echo "=== Creating Cloudflare API token secret ==="
kubectl create secret generic cloudflare-api-token \
    --namespace cert-manager \
    --from-literal=api-token="$CLOUDFLARE_API_TOKEN"

echo "=== Applying ClusterIssuer ==="
kubectl apply -f deploy/k8s/infrastructure/cert-manager/test-eu/cluster-issuer.yaml

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../.tls-backup"
TLS_BACKUP="$BACKUP_DIR/eshop-test-wildcard-tls.yaml"

if [ -f "$TLS_BACKUP" ]; then
    echo "=== Restoring TLS secret from backup ==="
    kubectl apply -f "$TLS_BACKUP"
fi

echo "=== Applying wildcard Certificate ==="
kubectl apply -f deploy/k8s/infrastructure/cert-manager/certificates/test-eu/certificate.yaml

echo "=== Waiting for certificate to be ready ==="
kubectl wait --for=condition=Ready certificate/eshop-test-wildcard-tls \
    --timeout=300s

echo "=== Deploying production NGINX Ingress ==="
helm repo add nginx-stable https://helm.nginx.com/stable
helm repo update
helm install nginx-ingress nginx-stable/nginx-ingress \
    --namespace ingress-nginx \
    --create-namespace \
    --version 2.4.4 \
    -f deploy/k8s/infrastructure/ingress-nginx/test-eu/values.yaml

echo "=== Installing External Secrets Operator ==="
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm install external-secrets external-secrets/external-secrets \
    --namespace external-secrets \
    --create-namespace \
    --version 2.0.1

echo "=== Waiting for ESO to be ready ==="
kubectl wait --for=condition=Available deployment --all \
    -n external-secrets --timeout=120s

echo "=== Creating ESO Kubernetes Service Account ==="
kubectl apply -f deploy/k8s/infrastructure/external-secrets/test-eu/service-account.yaml

echo "=== Applying ClusterSecretStore ==="
kubectl apply -f deploy/k8s/infrastructure/external-secrets/test-eu/cluster-secret-store.yaml

echo "=== Installing KEDA ==="
helm repo add kedacore https://kedacore.github.io/charts
helm repo update
helm install keda kedacore/keda \
    --namespace keda \
    --create-namespace \
    --version 2.19.0

echo "=== Waiting for KEDA to be ready ==="
kubectl wait --for=condition=Available deployment --all \
    -n keda --timeout=120s

echo "=== Cluster is ready ==="
kubectl get nodes
kubectl get certificate
kubectl get svc -n ingress-nginx
