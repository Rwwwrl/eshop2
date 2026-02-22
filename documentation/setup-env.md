# MyEshop - Environment Setup

---

## How We Write This Documentation

- Write clear facts only, without notes or suggestions unless explicitly provided
- Do not imagine or describe environments that are not set up (e.g., prod)
- Provide a clear list that another developer can follow to repeat the setup on a new environment

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Setup](#docker-setup)
4. [GCP & GKE Setup](#gcp--gke-setup)
5. [GKE Standard Cluster Setup (Console UI)](#gke-standard-cluster-setup-console-ui)
6. [Deploy via CI/CD](#deploy-via-cicd)

## Cluster Lifecycle Scripts

To save costs, the GKE cluster can be deleted when not in use and recreated on demand.

```bash
# Create cluster with full infrastructure (NGINX Ingress, cert-manager, TLS)
export CLOUDFLARE_API_TOKEN="<your-token>"
just gke-up

# Delete cluster
just gke-down
```

Scripts: `scripts/gke-up.sh`, `scripts/gke-down.sh`

The static IP and Workload Identity Federation (pools, providers, service account bindings) are GCP project-level resources and persist across cluster deletions. DNS records also remain unchanged.

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

### 4. Create a GKE cluster

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

The `--workload-pool` flag enables Workload Identity, which is required for CI/CD (GitHub Actions) to authenticate to the cluster.

### 5. Create wearables node pool

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

### 6. Set up Workload Identity Federation for GitHub Actions

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

### 7. Configure GitHub Environment Variables

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

### 8. Set Up Secret Manager + External Secrets Operator

Service configuration is split into two sources injected as Kubernetes environment variables:

- **ConfigMaps** — non-secret values (environment, log level, feature flags). Defined per service per environment in `deploy/k8s/services/<SERVICE>/<ENV>/configmap.yaml`.
- **Secrets** — sensitive values (database URLs, API keys, DSNs). Stored in GCP Secret Manager and synced to Kubernetes Secrets via External Secrets Operator (ESO).

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
| `redis-password`     | redis-auth    |
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
| `wearables-taskiq-redis-url`       | wearables   |

#### Install External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace
```

#### Set up Workload Identity for ESO (Direct Principal)

Grant the ESO Kubernetes service account direct access to Secret Manager — no GCP service account intermediary needed.

```bash
# Get your project number (not project ID)
gcloud projects describe <PROJECT_ID> --format="value(projectNumber)"

# Grant the K8s SA direct access to Secret Manager
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --role="roles/secretmanager.secretAccessor" \
  --member="principal://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/<PROJECT_ID>.svc.id.goog/subject/ns/external-secrets/sa/eso-ksa"
```

The K8s ServiceAccount manifest is at `deploy/k8s/infrastructure/external-secrets/<ENV>/service-account.yaml` and is applied by `gke-up.sh`.

#### Deploy ClusterSecretStore

The `ClusterSecretStore` connects ESO to GCP Secret Manager. Manifest: `deploy/k8s/infrastructure/external-secrets/<ENV>/cluster-secret-store.yaml`.

```bash
kubectl apply -f deploy/k8s/infrastructure/external-secrets/<ENV>/cluster-secret-store.yaml
```

#### How it works

Each service has an `ExternalSecret` manifest (`deploy/k8s/services/<SERVICE>/base/external-secret.yaml`) that references secrets from the `ClusterSecretStore`. ESO syncs these into Kubernetes Secrets, which are mounted via `envFrom` in deployments alongside ConfigMaps.

Infrastructure-level ExternalSecrets (e.g., `redis-auth`) are stored in `deploy/k8s/infrastructure/external-secrets/<ENV>/external-secrets/` and deployed by the `called-apply-secrets.yaml` CI workflow.

The `gke-up.sh` script handles the full ESO bootstrap: Helm install, KSA creation, workload identity annotation, and ClusterSecretStore deployment.

### 9. Create Google Cloud Memorystore (Redis)

- Create a Redis instance in Memorystore (console or gcloud)
- Note the connection string
- Store the Redis URL as `wearables-taskiq-redis-url` in GCP Secret Manager

---

## GKE Standard Cluster Setup (Console UI)

### Step 1: Navigate to GKE

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Navigation Menu -> Kubernetes Engine -> Clusters
4. Click CREATE
5. Click SWITCH TO STANDARD CLUSTER

### Step 2: Cluster Basics

| Field                 | Value           |
| --------------------- | --------------- |
| Name                  | `eshop-cluster` |
| Location type         | Regional        |
| Region                | `europe-west3`  |
| Control plane version | Regular         |

Default node locations: Select Custom, pick one zone (e.g., `europe-west3-a`)

### Step 3: Node Pool Configuration

Click default-pool in the left sidebar.

| Field           | Value          |
| --------------- | -------------- |
| Name            | `default-pool` |
| Number of nodes | `3`            |

Node configuration (click Nodes in the left sidebar under default-pool):

| Field          | Value                                      |
| -------------- | ------------------------------------------ |
| Series         | E2                                         |
| Machine type   | `e2-standard-2` (2 vCPU, 1 core, 8 GB)    |
| Boot disk type | Standard persistent disk                   |
| Boot disk size | 30 GB                                      |

Cluster autoscaler:

| Field                       | Value        |
| --------------------------- | ------------ |
| Enable cluster autoscaler   | Enabled      |
| Location policy             | Balanced     |
| Size limits type            | Total limits |
| Minimum number of all nodes | `3`          |
| Maximum number of all nodes | `4`          |

Automation:

| Field                                                  | Value   |
| ------------------------------------------------------ | ------- |
| Automatically upgrade nodes to next available version  | Enabled |
| Enable auto-repair                                     | Enabled |

### Step 4: Create Cluster

1. Click CREATE
2. Wait for provisioning

### Post-Creation: Update GitHub Variables

Path: GitHub repo -> Settings -> Secrets and variables -> Actions -> Variables

| Variable           | Value           |
| ------------------ | --------------- |
| `GKE_CLUSTER_NAME` | `eshop-cluster` |
| `GCP_REGION`       | `europe-west3`  |

### Post-Creation: Reserve Static IP

1. Navigation Menu -> VPC network -> IP addresses
2. Click RESERVE EXTERNAL STATIC ADDRESS
3. Configure:
   - Name: `nginx-ingress-ip`
   - Network Service Tier: Premium
   - IP version: IPv4
   - Type: Regional
   - Region: `europe-west3`
4. Click RESERVE

| Environment | IP Name            | IP Address       | Region       |
|-------------|--------------------|------------------|--------------|
| test-eu     | `nginx-ingress-ip` | `<STATIC_IP>`    | europe-west3 |

---

## Deploy via CI/CD

CI/CD deploys infrastructure (NGINX Ingress, ClusterIssuer) and services automatically.

### 1. Create Cloudflare API Token

Create a scoped API token at Cloudflare dashboard (My Profile > API Tokens > Create Token):

| Permission | Value |
|------------|-------|
| Zone - DNS | Edit |
| Zone - Zone | Read |
| Zone Resources | Include - Specific zone - `eshop-test.com` |

This token is used by cert-manager to create/delete DNS TXT records for Let's Encrypt DNS-01 challenges. Set it as `CLOUDFLARE_API_TOKEN` before running `gke-up.sh`.

### 2. Create infrastructure config files

Create `deploy/k8s/infrastructure/ingress-nginx/<ENV>/values.yaml`:

```yaml
controller:
  replicaCount: 3
  service:
    loadBalancerIP: "<STATIC_IP>"
```

### 4. Create service Kubernetes overlays

Create overlay folder `deploy/k8s/services/<SERVICE>/<ENV>/` with:
- `kustomization.yaml`
- `deployment.yaml`
- `ingress.yaml` (for public services)

### 5. Create workflow file

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

### 6. Configure DNS

Create an A record pointing to the static IP:

| Field        | Value         |
| ------------ | ------------- |
| Type         | A             |
| Name         | `<SUBDOMAIN>` |
| IPv4 address | `<STATIC_IP>` |
| Proxy status | DNS only      |

### 7. Trigger deployment

```bash
git checkout -b <ENV>/initial-deploy
git push -u origin <ENV>/initial-deploy
```

### 8. Verify deployment

```bash
kubectl get pods
kubectl get certificate
curl https://<YOUR_DOMAIN>/health
```
