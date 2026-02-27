# MyEshop - Environment Setup

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Setup](#docker-setup)
4. [GCP & GKE Setup](#gcp--gke-setup)
5. [Deploy via CI/CD](#deploy-via-cicd)

## Cluster Lifecycle Scripts

```bash
# Create cluster with full infrastructure (NGINX Ingress, cert-manager, TLS, KEDA)
export CLOUDFLARE_API_TOKEN="<your-token>"
just gke-up

# Delete cluster
just gke-down
```

Scripts: `scripts/gke-up.sh`, `scripts/gke-down.sh`

---

## Prerequisites

### Local Development

- Python 3.14
- Poetry 1.8.3
- Ruff
- Docker

### Kubernetes (local)

- Docker Desktop with Kubernetes enabled, or Minikube
- kubectl

### GKE Deployment

- Google Cloud account with a project
- gcloud CLI
- Helm (`brew install helm`)

---

## Local Development Setup

### 1. Clone and install dependencies

```bash
git clone <repository-url>
cd eshop2
poetry install
```

### 2. Install individual service dependencies

```bash
cd src/services/api_gateway
poetry install

cd ../hello_world
poetry install
```

### 3. Run services locally

```bash
# Run api-gateway
cd src/services/api_gateway
poetry run uvicorn api_gateway.http.main:app --host 0.0.0.0 --port 8000

# Run hello-world (in separate terminal)
cd src/services/hello_world
poetry run uvicorn hello_world.http.main:app --host 0.0.0.0 --port 8001
```

### 4. Lint and format

```bash
poetry run ruff check --fix .
poetry run ruff format .
```

### 5. Run tests

```bash
poetry run pytest -c pytest.ini
```

---

## Docker Setup

### Build production images

```bash
docker build -t api-gateway:latest src/services/api_gateway
docker build -t hello-world:latest src/services/hello_world
```

---

## GCP & GKE Setup

### 1. Create a GCP project

```bash
gcloud projects create <PROJECT_ID>
gcloud config set project <PROJECT_ID>
```

### 2. Enable required APIs

```bash
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable iamcredentials.googleapis.com
```

### 3. Create an Artifact Registry repository

```bash
gcloud artifacts repositories create <REGISTRY_NAME> \
  --repository-format=docker \
  --location=<REGION> \
  --description="MyEshop Docker images"
```

### 4. Reserve a static IP

```bash
gcloud compute addresses create nginx-ingress-ip \
  --region=<REGION> \
  --network-tier=PREMIUM
```

```bash
gcloud compute addresses describe nginx-ingress-ip \
  --region=<REGION> \
  --format="get(address)"
```

| Environment | IP Name            | Region       |
|-------------|--------------------|--------------|
| test-eu     | `nginx-ingress-ip` | europe-west3 |

### 5. Create a GKE cluster

```bash
gcloud container clusters create <CLUSTER_NAME> \
  --project <PROJECT_ID> \
  --region <REGION> \
  --node-locations <ZONE> \
  --machine-type e2-standard-2 \
  --disk-type pd-standard \
  --disk-size 30 \
  --num-nodes 3 \
  --enable-autoscaling \
  --total-min-nodes 3 --total-max-nodes 4 \
  --enable-autorepair \
  --enable-autoupgrade \
  --workload-pool=<PROJECT_ID>.svc.id.goog
```

### 6. Create wearables node pool

```bash
gcloud container node-pools create wearables-pool \
  --cluster=<CLUSTER_NAME> \
  --project=<PROJECT_ID> \
  --region=<REGION> \
  --node-locations=<ZONE> \
  --machine-type=e2-standard-2 \
  --disk-type=pd-standard \
  --disk-size=30 \
  --num-nodes=2 \
  --enable-autoscaling \
  --total-min-nodes=2 \
  --total-max-nodes=4 \
  --enable-autorepair \
  --enable-autoupgrade
```

### 7. Set up Workload Identity Federation for GitHub Actions

```bash
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:github-actions@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/container.admin"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:github-actions@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud iam workload-identity-pools create "github" \
  --location="global" \
  --display-name="GitHub"

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

gcloud iam service-accounts add-iam-policy-binding \
  github-actions@<PROJECT_ID>.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github/attribute.repository/<GITHUB_ORG>/<GITHUB_REPO>"
```

### 8. Configure GitHub Environment Variables

Create a GitHub environment (e.g., `test-eu`) with these variables:

| Variable                         | Example                                                                                  |
| -------------------------------- | ---------------------------------------------------------------------------------------- |
| `GCP_PROJECT_ID`                 | `<PROJECT_ID>`                                                                           |
| `GCP_REGION`                     | `europe-west3`                                                                           |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/<NUM>/locations/global/workloadIdentityPools/github/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT`            | `github-actions@my-eshop-123.iam.gserviceaccount.com`                                    |
| `GKE_CLUSTER_NAME`               | `my-cluster`                                                                             |
| `GCP_ARTIFACT_REGISTRY_NAME`     | `myeshop`                                                                                |

Path: GitHub repo -> Settings -> Environments -> New environment

### 9. Set Up Secret Manager + External Secrets Operator

#### Enable Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com
```

#### Create secrets in GCP Secret Manager

Each secret is a separate Secret Manager entry. Naming convention: `<service>-<key-name>` (e.g., `wearables-postgres-direct-db-url`, `api-gateway-sentry-dsn`).

```bash
echo -n "<VALUE>" | gcloud secrets create <SECRET_NAME> --data-file=-
```

Infrastructure secrets (shared across services):

| Secret Name          | Used By       |
|----------------------|---------------|
| `rabbitmq-url`       | rabbitmq-auth |
| `pgbouncer-ini`      | pgbouncer     |
| `pgbouncer-userlist` | pgbouncer     |

Per-service secrets:

| Secret Name                        | Service     |
|------------------------------------|-------------|
| `api-gateway-sentry-dsn`           | api-gateway |
| `hello-world-sentry-dsn`           | hello-world |
| `wearables-sentry-dsn`             | wearables   |
| `wearables-postgres-direct-db-url` | wearables   |
| `wearables-postgres-pooler-db-url` | wearables   |

#### Install External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace
```

#### Set up Workload Identity for ESO (Direct Principal)

```bash
gcloud projects describe <PROJECT_ID> --format="value(projectNumber)"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --role="roles/secretmanager.secretAccessor" \
  --member="principal://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/<PROJECT_ID>.svc.id.goog/subject/ns/external-secrets/sa/eso-ksa"
```

KSA manifest: `deploy/k8s/infrastructure/external-secrets/<ENV>/service-account.yaml`

#### Deploy ClusterSecretStore

```bash
kubectl apply -f deploy/k8s/infrastructure/external-secrets/<ENV>/cluster-secret-store.yaml
```

#### Key manifests

| Manifest | Purpose |
|----------|---------|
| `deploy/k8s/services/<SERVICE>/base/external-secret.yaml` | Per-service ExternalSecret |
| `deploy/k8s/infrastructure/external-secrets/<ENV>/external-secrets/` | Infrastructure-level ExternalSecrets |
| `deploy/k8s/infrastructure/external-secrets/<ENV>/cluster-secret-store.yaml` | ClusterSecretStore |

### 10. Create CloudAMQP Instance (RabbitMQ)

1. Create a RabbitMQ instance on [CloudAMQP](https://www.cloudamqp.com/)
2. Store the AMQP URL as `rabbitmq-url` in GCP Secret Manager

---

## Deploy via CI/CD

CI/CD deploys infrastructure (NGINX Ingress, ClusterIssuer) and services automatically.

### 1. Create Cloudflare API Token

Cloudflare dashboard → My Profile → API Tokens → Create Token:

| Permission | Value |
|------------|-------|
| Zone - DNS | Edit |
| Zone - Zone | Read |
| Zone Resources | Include - Specific zone - `eshop-test.com` |

Set as `CLOUDFLARE_API_TOKEN` before running `gke-up.sh`.

### 2. Create infrastructure config files

Create `deploy/k8s/infrastructure/ingress-nginx/<ENV>/values.yaml`:

```yaml
controller:
  replicaCount: 3
  service:
    loadBalancerIP: "<STATIC_IP>"
```

### 3. Create service Kubernetes overlays

Create overlay folder `deploy/k8s/services/<SERVICE>/<ENV>/` with:
- `kustomization.yaml`
- `deployment.yaml`
- `ingress.yaml` (for public services)

### 4. Create workflow file

Create `.github/workflows/on-push-<ENV>.yaml`:

```yaml
name: Deploy to <ENV>

on:
  push:
    branches:
      - "<ENV>/**"

permissions:
  contents: read
  id-token: write

jobs:
  deploy-infrastructure:
    uses: ./.github/workflows/called-deploy-infrastructure.yaml
    with:
      environment: <ENV>
    secrets: inherit

  deploy-api-gateway:
    needs: deploy-infrastructure
    uses: ./.github/workflows/called-deploy-to-gke.yaml
    with:
      environment: <ENV>
      service_name: api-gateway
      service_path: src/services/api_gateway
    secrets: inherit

  deploy-hello-world:
    needs: deploy-infrastructure
    uses: ./.github/workflows/called-deploy-to-gke.yaml
    with:
      environment: <ENV>
      service_name: hello-world
      service_path: src/services/hello_world
    secrets: inherit
```

### 5. Configure DNS

Create an A record pointing to the static IP:

| Field        | Value         |
| ------------ | ------------- |
| Type         | A             |
| Name         | `<SUBDOMAIN>` |
| IPv4 address | `<STATIC_IP>` |
| Proxy status | DNS only      |

### 6. Trigger deployment

```bash
git checkout -b <ENV>/initial-deploy
git push -u origin <ENV>/initial-deploy
```

### 7. Verify deployment

```bash
kubectl get pods
kubectl get certificate
curl https://<YOUR_DOMAIN>/health
```
