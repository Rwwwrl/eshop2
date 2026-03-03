---
name: validate-cluster
description: Validate GKE cluster deployment health after cluster recreation or service deployment. Checks node pools, pod status, scheduling rules, TLS certificates, HTTP-to-HTTPS redirect, ingress, and service availability. Trigger phrases include "validate cluster", "check cluster", "verify deployment", "cluster health".
user_invocable: true
---

# Validate Cluster Deployment

Run all sections **sequentially**. Within each section, run independent kubectl commands **in parallel**. Report a pass/fail table per section. Print a summary at the end.

If `kubectl` is not configured or the cluster is unreachable, stop immediately and report the error.

## 1. Node Pool Health

Run: `kubectl get nodes -o wide`

| Check | Expected |
|-------|----------|
| All nodes Ready | Every node `STATUS=Ready` — no `NotReady`, `SchedulingDisabled`, or unknown |
| default-pool >= 3 | `kubectl get nodes -l cloud.google.com/gke-nodepool=default-pool` returns >= 3 |
| wearables-pool >= 2 | `kubectl get nodes -l cloud.google.com/gke-nodepool=wearables-pool` returns >= 2 |

## 2. System Components

Run in parallel:

| Check | Command | Expected |
|-------|---------|----------|
| cert-manager | `kubectl get pods -n cert-manager` | All Running, containers ready |
| ingress-nginx | `kubectl get pods -n ingress-nginx` | 2 controller pods Running |
| ClusterIssuer | `kubectl get clusterissuer letsencrypt -o jsonpath='{.status.conditions[0].status}'` | `True` |
| Wildcard cert ready | `kubectl get certificate eshop-test-wildcard-tls -o jsonpath='{.status.conditions[0].status}'` | `True` |
| Cert not expired | `kubectl get certificate eshop-test-wildcard-tls -o jsonpath='{.status.notAfter}'` | Date in the future |
| PgBouncer running | `kubectl get pods -l app=pgbouncer` | 2 pods Running |
| PgBouncer node pool | `kubectl get pods -l app=pgbouncer -o wide` | All on `default-pool` |
| PgBouncer anti-affinity | `kubectl get pods -l app=pgbouncer -o wide` | Two pods on different hostnames |
| PgBouncer strategy | `kubectl get deployment pgbouncer -o jsonpath='{.spec.strategy.type}'` | `RollingUpdate` |
| PgBouncer probes | `kubectl get deployment pgbouncer -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'` | TCP socket on port 5432 |
| KEDA operator | `kubectl get pods -n keda` | 3 pods Running (operator, metrics-apiserver, admission-webhooks) |

## 3. External Secrets Operator

### ServiceAccount & ClusterSecretStore

| Check | Expected | How to verify |
|-------|----------|---------------|
| eso-ksa exists | Present in external-secrets ns | `kubectl get serviceaccount eso-ksa -n external-secrets` — no `NotFound` |
| gcp-cluster-store ready | Status=Valid | `kubectl get clustersecretstore gcp-cluster-store -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |

### ExternalSecrets (all must show Ready)

Run: `kubectl get externalsecrets`

| ExternalSecret | Target Secret | Verify Ready |
|----------------|---------------|--------------|
| rabbitmq-auth | rabbitmq-auth | `kubectl get externalsecret rabbitmq-auth -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |
| sentry-auth | sentry-auth | `kubectl get externalsecret sentry-auth -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |
| pgbouncer-config | pgbouncer-config | `kubectl get externalsecret pgbouncer-config -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |
| api-gateway-secrets | api-gateway-secrets | `kubectl get externalsecret api-gateway-secrets -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |
| hello-world-secrets | hello-world-secrets | `kubectl get externalsecret hello-world-secrets -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |
| wearables-secrets | wearables-secrets | `kubectl get externalsecret wearables-secrets -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |

### Generated Secrets & ConfigMaps

Verify ESO created the target secrets:

`kubectl get secret rabbitmq-auth sentry-auth pgbouncer-config api-gateway-secrets hello-world-secrets wearables-secrets`

All must exist (no `NotFound`).

| ConfigMap | Verify |
|-----------|--------|
| api-gateway-config | `kubectl get configmap api-gateway-config` |
| hello-world-config | `kubectl get configmap hello-world-config` |
| wearables-config | `kubectl get configmap wearables-config` |

## 4. Pod Health

Run: `kubectl get pods -A`

| Check | Expected |
|-------|----------|
| No Pending pods | `kubectl get pods -A --field-selector=status.phase=Pending` returns zero rows |
| No CrashLoopBackOff | Grep containerStatuses for `CrashLoopBackOff` — zero matches |
| No ImagePullBackOff | Grep for `ImagePullBackOff` or `ErrImagePull` — zero matches |
| All containers ready | Every pod READY column shows `N/N` |

## 5. Service Deployments

### api-gateway-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | >= 2 (HPA) | `kubectl get deployment api-gateway-http -o jsonpath='{.status.readyReplicas}'` >= 2 |
| HPA | min=2, max=4, CPU target=70 | `kubectl get hpa api-gateway-http` |
| HPA metrics | TARGETS not `<unknown>` | `kubectl get hpa api-gateway-http` — TARGETS shows current/70% |
| Node pool | `default-pool` | `kubectl get pods -l app=api-gateway-http -o wide` |
| Anti-affinity | Pods on different nodes (required) | Two pods on different hostnames |
| Graceful shutdown | terminationGracePeriodSeconds=95, preStop sleep 10 | `kubectl get deployment api-gateway-http -o jsonpath='{.spec.template.spec.terminationGracePeriodSeconds}'` |
| Strategy | RollingUpdate | `kubectl get deployment api-gateway-http -o jsonpath='{.spec.strategy.type}'` |
| Health | Probes passing, no restarts | No restart count incrementing |

### hello-world-messaging

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 (fixed) | `kubectl get deployment hello-world-messaging -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node pool | `default-pool` | `kubectl get pods -l app=hello-world-messaging -o wide` |
| Strategy | RollingUpdate | jsonpath check |
| Graceful shutdown | terminationGracePeriodSeconds=75 | jsonpath check |
| Liveness probe | HTTP GET `/health` port 8001, initialDelay=30, period=10 | jsonpath check |
| Health | Probes passing, no restarts | No restart count incrementing |

### hello-world-grpc

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | >= 2 (HPA) | `kubectl get deployment hello-world-grpc -o jsonpath='{.status.readyReplicas}'` >= 2 |
| HPA | min=2, max=4, CPU target=70 | `kubectl get hpa hello-world-grpc` |
| HPA metrics | TARGETS not `<unknown>` | `kubectl get hpa hello-world-grpc` |
| Node pool | `default-pool` | `kubectl get pods -l app=hello-world-grpc -o wide` |
| Anti-affinity | Required (hard) — pods must be on different nodes, FAIL if co-located | Check hostnames — two pods on different nodes is the project convention for gRPC deployments |
| Graceful shutdown | terminationGracePeriodSeconds=95, preStop sleep 10 | jsonpath check |
| Strategy | RollingUpdate | jsonpath check |
| gRPC health | `grpc_health_probe -addr=:50051` passes | Check pod logs or exec into pod |
| Health | Probes passing, no restarts | No restart count incrementing |

### wearables-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | >= 2 (HPA) | `kubectl get deployment wearables-http -o jsonpath='{.status.readyReplicas}'` >= 2 |
| HPA | min=2, max=4, CPU target=70 | `kubectl get hpa wearables-http` |
| HPA metrics | TARGETS not `<unknown>` | `kubectl get hpa wearables-http` |
| Node pool | `wearables-pool` | `kubectl get pods -l app=wearables-http -o wide` |
| Topology spread | maxSkew <= 1 across hostnames | Count pods per node |
| Graceful shutdown | terminationGracePeriodSeconds=95, preStop sleep 10 | jsonpath check |
| Strategy | RollingUpdate | jsonpath check |
| Health | Probes passing, no restarts | No restart count incrementing |

### wearables-messaging

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 (fixed) | `kubectl get deployment wearables-messaging -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node pool | `wearables-pool` | `kubectl get pods -l app=wearables-messaging -o wide` |
| Strategy | RollingUpdate | jsonpath check |
| Graceful shutdown | terminationGracePeriodSeconds=75 | jsonpath check |
| Liveness probe | HTTP GET `/health` port 8001, initialDelay=30, period=10 | jsonpath check |
| Health | Probes passing, no restarts | No restart count incrementing |

### wearables-scheduler (TaskIQ)

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 1 (singleton) | `kubectl get deployment wearables-scheduler -o jsonpath='{.status.readyReplicas}'` = 1 |
| Node pool | `wearables-pool` | `kubectl get pods -l app=wearables-scheduler -o wide` |
| Strategy | Recreate (must not run two copies) | jsonpath check |
| Graceful shutdown | terminationGracePeriodSeconds=30 | jsonpath check |
| Health | No restarts, Running | No restart count incrementing |

### wearables-background-tasks (TaskIQ worker, KEDA-managed)

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | >= 2 (KEDA) | `kubectl get deployment wearables-background-tasks -o jsonpath='{.status.readyReplicas}'` >= 2 |
| Node pool | `wearables-pool` | `kubectl get pods -l app=wearables-background-tasks -o wide` |
| Topology spread | maxSkew <= 1 across hostnames | Count pods per node |
| Strategy | RollingUpdate | jsonpath check |
| Graceful shutdown | terminationGracePeriodSeconds=80 | jsonpath check |
| Liveness probe | HTTP GET `/health-check` port 8081, initialDelay=30, period=10, failure=3, timeout=5 | jsonpath check |
| Readiness probe | HTTP GET `/readiness-check` port 8081, initialDelay=10, period=10, failure=3, timeout=5 | jsonpath check |
| Health | Probes passing, no restarts | No restart count incrementing |
| ScaledObject ready | `kubectl get scaledobject wearables-worker-scaler -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |
| ScaledObject target | `wearables-background-tasks` | jsonpath `{.spec.scaleTargetRef.name}` |
| ScaledObject min/max | min=2, max=10 | jsonpath check |
| HPA by KEDA | HPA exists for wearables-background-tasks | `kubectl get hpa` |
| TriggerAuthentication | `kubectl get triggerauthentication rabbitmq-trigger-auth` — must exist |

## 6. Ingress & TLS

### Ingress Resources

Run: `kubectl get ingress`

| Check | Expected |
|-------|----------|
| api-gateway-ingress | Host: `test.eshop-test.com`, TLS secret: `eshop-test-wildcard-tls` |
| wearables-ingress | Host: `wearables-test.eshop-test.com`, TLS secret: `eshop-test-wildcard-tls` |

### NGINX Ingress Controller

| Check | Expected |
|-------|----------|
| LoadBalancer IP | `34.159.106.171` via `kubectl get svc -n ingress-nginx` |
| Controller replicas | 2 pods on different nodes (required anti-affinity) |
| Controller node pool | All on `default-pool` |

### HTTP-to-HTTPS Redirect

```bash
curl -s -o /dev/null -w "%{http_code}" -H "Host: test.eshop-test.com" http://34.159.106.171/health
curl -s -o /dev/null -w "%{http_code}" -H "Host: wearables-test.eshop-test.com" http://34.159.106.171/health
```

Both must return **301** (NGINX Inc ingress controller default).

### TLS Endpoints

test-eu uses Let's Encrypt **production**:

```bash
curl -s -o /dev/null -w "%{http_code}" https://test.eshop-test.com/health          # expect 200
curl -s -o /dev/null -w "%{http_code}" https://wearables-test.eshop-test.com/health # expect 200
```

## 7. Services & DNS

| Check | Expected |
|-------|----------|
| api-gateway-http ClusterIP | Port 80 -> 8000 via `kubectl get svc api-gateway-http` |
| hello-world ClusterIP | Port 50051 -> 50051 via `kubectl get svc hello-world` |
| wearables-http ClusterIP | Port 80 -> 8000 via `kubectl get svc wearables-http` |
| pgbouncer ClusterIP | Port 5432 -> 5432 via `kubectl get svc pgbouncer` |
| Internal DNS | `kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup api-gateway-http.default.svc.cluster.local` (skip if impractical) |
| Internal gRPC DNS | `kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup hello-world.default.svc.cluster.local` (skip if impractical) |

## 8. Resource Requests & Limits

Verify: `kubectl get deployment <name> -o jsonpath='{.spec.template.spec.containers[0].resources}'`

| Deployment | CPU Req | Mem Req | CPU Limit | Mem Limit |
|------------|---------|---------|-----------|-----------|
| api-gateway-http | 50m | 128Mi | 200m | 256Mi |
| hello-world-messaging | 50m | 128Mi | 200m | 256Mi |
| hello-world-grpc | 50m | 128Mi | 200m | 256Mi |
| wearables-http | 50m | 128Mi | 200m | 256Mi |
| wearables-messaging | 50m | 128Mi | 200m | 256Mi |
| wearables-background-tasks | 50m | 205Mi | 200m | 430Mi |
| pgbouncer | 50m | 64Mi | 200m | 128Mi |
| wearables-scheduler | 25m | 100Mi | 100m | 200Mi |

## Summary Format

After all checks, print:

```
=== Cluster Validation Summary ===

Section                    | Passed | Failed | Warnings
---------------------------|--------|--------|----------
1. Node Pool Health        |   X    |   X    |    X
2. System Components       |   X    |   X    |    X
3. External Secrets        |   X    |   X    |    X
4. Pod Health              |   X    |   X    |    X
5. Service Deployments     |   X    |   X    |    X
6. Ingress & TLS           |   X    |   X    |    X
7. Services & DNS          |   X    |   X    |    X
8. Resource Configuration  |   X    |   X    |    X
---------------------------|--------|--------|----------
TOTAL                      |   X    |   X    |    X

Result: PASS / FAIL
```

If any check fails, list failed checks at the bottom with details.
