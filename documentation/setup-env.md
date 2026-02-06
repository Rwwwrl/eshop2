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
4. [Kubernetes Local Development (dev)](#kubernetes-local-development-dev)
5. [GCP & GKE Setup](#gcp--gke-setup)
6. [GKE Standard Cluster Setup (Console UI)](#gke-standard-cluster-setup-console-ui)
7. [Deploy via CI/CD](#deploy-via-cicd)

## Related Documentation

- [TLS Bootstrap Problem Explained](tls-bootstrap-problem.md) - Understanding the chicken-egg problem with TLS certificates

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
poetry run uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000

# Run hello-world (in separate terminal)
cd src/services/hello_world
poetry run uvicorn hello_world.main:app --host 0.0.0.0 --port 8001
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

## Kubernetes Local Development (dev)

### 1. Build Docker images locally

```bash
docker build -t api-gateway:latest src/services/api_gateway
docker build -t hello-world:latest src/services/hello_world
```

### 2. Apply Kubernetes manifests

```bash
kubectl apply -k deploy/k8s/services/api-gateway/dev
kubectl apply -k deploy/k8s/services/hello-world/dev
```

### 3. Verify deployment

```bash
kubectl get pods
kubectl get services
```

### 4. Access the api-gateway

```bash
kubectl port-forward svc/api-gateway 8080:80
```

Access at `localhost:8080`.

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
  --region=<REGION> \
  --num-nodes=1
```

### 5. Set up Workload Identity Federation for GitHub Actions

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

### 6. Configure GitHub Environment Variables

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
| Number of nodes | `2`            |

Cluster autoscaler:

| Field                       | Value        |
| --------------------------- | ------------ |
| Enable cluster autoscaler   | Enabled      |
| Location policy             | Balanced     |
| Size limits type            | Total limits |
| Minimum number of all nodes | `0`          |
| Maximum number of all nodes | `2`          |

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

### 1. Install cert-manager

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.17.2/cert-manager.yaml
kubectl get pods -n cert-manager
```

Wait for all pods to be `Running` before proceeding.

### 2. Apply ClusterIssuer

```bash
kubectl apply -f deploy/k8s/infrastructure/cert-manager/cluster-issuer.yaml
kubectl get clusterissuers
```

The ClusterIssuer is environment-agnostic and only needs to be applied once per cluster.

### 3. Create infrastructure config files

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

### 7. TLS Bootstrap

On a new environment, the TLS certificate must be issued BEFORE deploying services. See [TLS Bootstrap Problem Explained](tls-bootstrap-problem.md) for details.

#### 7.1 Deploy bootstrap NGINX

Deploy NGINX Ingress in a separate namespace with `ssl-redirect` disabled to allow HTTP-01 challenge:

```bash
helm repo add nginx-stable https://helm.nginx.com/stable
helm repo update
helm install nginx-ingress nginx-stable/nginx-ingress \
  --namespace ingress-nginx-bootstrap \
  --create-namespace \
  --set controller.replicaCount=1 \
  --set controller.service.loadBalancerIP="<STATIC_IP>" \
  --set controller.config.ssl-redirect="false"
```

Wait for LoadBalancer IP assignment:

```bash
kubectl get svc -n ingress-nginx-bootstrap
```

#### 7.2 Create and apply Certificate

Create `deploy/k8s/infrastructure/cert-manager/certificates/<ENV>/certificate.yaml`:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-gateway-tls
spec:
  secretName: api-gateway-tls
  issuerRef:
    name: letsencrypt
    kind: ClusterIssuer
  dnsNames:
    - <YOUR_DOMAIN>
```

Apply and wait for certificate:

```bash
kubectl apply -f deploy/k8s/infrastructure/cert-manager/certificates/<ENV>/certificate.yaml
kubectl get certificate --watch
```

Wait until `READY` shows `True`.

#### 7.3 Delete bootstrap NGINX

```bash
helm uninstall nginx-ingress --namespace ingress-nginx-bootstrap
kubectl delete namespace ingress-nginx-bootstrap
```

### 8. Trigger deployment

```bash
git checkout -b <ENV>/initial-deploy
git push -u origin <ENV>/initial-deploy
```

### 9. Verify deployment

```bash
kubectl get pods
kubectl get certificate
curl https://<YOUR_DOMAIN>/health
```
