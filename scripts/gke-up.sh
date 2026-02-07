#!/usr/bin/env bash
set -euo pipefail

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
    --num-nodes 3 \
    --enable-autoscaling \
    --total-min-nodes 3 --total-max-nodes 4 \
    --enable-autorepair \
    --enable-autoupgrade \
    --workload-pool="$PROJECT.svc.id.goog"

echo "=== Getting cluster credentials ==="
gcloud container clusters get-credentials "$CLUSTER" \
    --region "$REGION" \
    --project "$PROJECT"

echo "=== Installing cert-manager ==="
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.2/cert-manager.yaml

echo "=== Waiting for cert-manager to be ready ==="
kubectl wait --for=condition=Available deployment --all \
    -n cert-manager --timeout=120s

echo "=== Applying ClusterIssuer ==="
kubectl apply -f deploy/k8s/infrastructure/cert-manager/cluster-issuer.yaml

echo "=== TLS bootstrap: deploying temporary NGINX ==="
helm repo add nginx-stable https://helm.nginx.com/stable
helm repo update
helm install nginx-ingress nginx-stable/nginx-ingress \
    --namespace ingress-nginx-bootstrap \
    --create-namespace \
    --set controller.replicaCount=1 \
    --set controller.service.loadBalancerIP="$STATIC_IP" \
    --set controller.config.entries.ssl-redirect=\"false\"

echo "=== Waiting for bootstrap LoadBalancer IP ==="
while true; do
    IP=$(kubectl get svc -n ingress-nginx-bootstrap nginx-ingress-controller \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
    if [ -n "$IP" ]; then
        echo "LoadBalancer IP: $IP"
        break
    fi
    echo "Waiting for external IP..."
    sleep 10
done

echo "=== Applying Certificate ==="
kubectl apply -f deploy/k8s/infrastructure/cert-manager/certificates/test-eu/certificate.yaml

echo "=== Waiting for certificate to be ready ==="
kubectl wait --for=condition=Ready certificate/api-gateway-tls \
    --timeout=300s

echo "=== Deleting bootstrap NGINX ==="
helm uninstall nginx-ingress --namespace ingress-nginx-bootstrap
kubectl delete namespace ingress-nginx-bootstrap

echo "=== Deploying production NGINX Ingress ==="
helm install nginx-ingress nginx-stable/nginx-ingress \
    --namespace ingress-nginx \
    --create-namespace \
    -f deploy/k8s/infrastructure/ingress-nginx/test-eu/values.yaml

echo "=== Cluster is ready ==="
kubectl get nodes
kubectl get certificate
kubectl get svc -n ingress-nginx
