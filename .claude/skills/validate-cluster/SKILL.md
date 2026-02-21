---
name: validate-cluster
description: Validate GKE cluster deployment health after cluster recreation or service deployment. Checks node pools, pod status, scheduling rules, TLS certificates, HTTP-to-HTTPS redirect, ingress, and service availability. Trigger phrases include "validate cluster", "check cluster", "verify deployment", "cluster health".
user_invocable: true
---

# Validate Cluster Deployment

Run all validation checks below **sequentially by section**. Within each section, run independent kubectl commands in parallel where possible. Report results as a table per section with pass/fail status. At the end, print a summary with total passed/failed checks.

If `kubectl` is not configured or the cluster is unreachable, stop immediately and report the error.

## 1. Node Pool Health

Run: `kubectl get nodes -o wide`

| Check | Expected |
|-------|----------|
| All nodes Ready | Every node shows `STATUS=Ready` — no `NotReady`, `SchedulingDisabled`, or unknown state |
| default-pool count >= 3 | `kubectl get nodes -l cloud.google.com/gke-nodepool=default-pool` returns >= 3 nodes |
| wearables-pool count >= 2 | `kubectl get nodes -l cloud.google.com/gke-nodepool=wearables-pool` returns >= 2 nodes |

## 2. System Components

Run these checks in parallel:

| Check | Command | Expected |
|-------|---------|----------|
| cert-manager running | `kubectl get pods -n cert-manager` | All pods Running, containers ready |
| ingress-nginx running | `kubectl get pods -n ingress-nginx` | 2 controller pods Running |
| ClusterIssuer ready | `kubectl get clusterissuer letsencrypt -o jsonpath='{.status.conditions[0].status}'` | `True` |
| Wildcard certificate ready | `kubectl get certificate eshop-test-wildcard-tls -o jsonpath='{.status.conditions[0].status}'` | `True` |
| Certificate not expired | `kubectl get certificate eshop-test-wildcard-tls -o jsonpath='{.status.notAfter}'` | Date is in the future |
| PgBouncer running | `kubectl get pods -l app=pgbouncer` | 2 pods Running, containers ready |
| PgBouncer node pool | `kubectl get pods -l app=pgbouncer -o wide` | All pods on `default-pool` nodes |
| PgBouncer anti-affinity | `kubectl get pods -l app=pgbouncer -o wide` | Two pods on different hostnames |
| PgBouncer strategy | `kubectl get deployment pgbouncer -o jsonpath='{.spec.strategy.type}'` | `RollingUpdate` |
| PgBouncer probes | `kubectl get deployment pgbouncer -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'` | TCP socket on port 5432 |
| KEDA operator running | `kubectl get pods -n keda` | 3 pods Running (operator, metrics-apiserver, admission-webhooks) |
| Redis auth secret exists | `kubectl get secret redis-auth` | Secret exists |
| redis-exporter running | `kubectl get pods -l app=redis-exporter` | 1 pod Running, container ready |
| redis-exporter node pool | `kubectl get pods -l app=redis-exporter -o wide` | Pod on `default-pool` node |
| redis-exporter strategy | `kubectl get deployment redis-exporter -o jsonpath='{.spec.strategy.type}'` | `Recreate` |
| redis-exporter probes | `kubectl get deployment redis-exporter -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'` | HTTP GET on `/health` port 9121 |
| redis-exporter streams flag | `kubectl get deployment redis-exporter -o jsonpath='{.spec.template.spec.containers[0].args}'` | Contains `--check-streams=taskiq` |
| redis-exporter PodMonitoring | `kubectl get podmonitoring redis-exporter -o jsonpath='{.spec.endpoints[0].port}'` | `9121` |

## 3. Pod Health (all namespaces)

Run: `kubectl get pods -A`

| Check | Expected |
|-------|----------|
| No Pending pods | `kubectl get pods -A --field-selector=status.phase=Pending` returns zero rows |
| No CrashLoopBackOff | Grep containerStatuses waiting.reason for CrashLoopBackOff — zero matches |
| No ImagePullBackOff | Same approach, grep for ImagePullBackOff or ErrImagePull — zero matches |
| All containers ready | Every pod READY column shows `N/N` |

## 4. Service Deployments (test-eu)

For each deployment, verify replica count and scheduling:

### api-gateway-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 Running pods | `kubectl get deployment api-gateway-http -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node selector | All pods on `default-pool` nodes | `kubectl get pods -l app=api-gateway-http -o wide` — NODE column must be default-pool nodes |
| Anti-affinity | Pods on different nodes | The two pods must be scheduled on different hostnames (required anti-affinity) |
| Graceful shutdown | terminationGracePeriodSeconds=95, preStop sleep 10 | `kubectl get deployment api-gateway-http -o jsonpath='{.spec.template.spec.terminationGracePeriodSeconds}'` = 95 and preStop exec contains `sleep` `10` |
| Strategy | RollingUpdate | `kubectl get deployment api-gateway-http -o jsonpath='{.spec.strategy.type}'` = `RollingUpdate` |
| Health endpoints | Liveness and readiness probes passing | No restart count incrementing, pods in Running state |

### hello-world-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 Running pods | `kubectl get deployment hello-world-http -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node selector | All pods on `default-pool` nodes | `kubectl get pods -l app=hello-world-http -o wide` — NODE column must be default-pool nodes |
| Anti-affinity | Pods preferably on different nodes | Preferred (weight 100), so warn if co-located but don't fail |
| Graceful shutdown | terminationGracePeriodSeconds=95, preStop sleep 10 | `kubectl get deployment hello-world-http -o jsonpath='{.spec.template.spec.terminationGracePeriodSeconds}'` = 95 and preStop exec contains `sleep` `10` |
| Strategy | RollingUpdate | `kubectl get deployment hello-world-http -o jsonpath='{.spec.strategy.type}'` = `RollingUpdate` |
| Health endpoints | Probes passing | No restart count incrementing |

### wearables-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 Running pods | `kubectl get deployment wearables-http -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node selector | All pods on `wearables-pool` nodes | `kubectl get pods -l app=wearables-http -o wide` — NODE column must be wearables-pool nodes |
| Topology spread | maxSkew <= 1 across hostnames | Count pods per node; difference between most-loaded and least-loaded node must be <= 1 |
| Graceful shutdown | terminationGracePeriodSeconds=95, preStop sleep 10 | `kubectl get deployment wearables-http -o jsonpath='{.spec.template.spec.terminationGracePeriodSeconds}'` = 95 and preStop exec contains `sleep` `10` |
| Strategy | RollingUpdate | `kubectl get deployment wearables-http -o jsonpath='{.spec.strategy.type}'` = `RollingUpdate` |
| Health endpoints | Probes passing | No restart count incrementing |

### wearables-scheduler (TaskIQ scheduler)

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 1 Running pod | `kubectl get deployment wearables-scheduler -o jsonpath='{.status.readyReplicas}'` = 1 |
| Node selector | Pod on `wearables-pool` node | `kubectl get pods -l app=wearables-scheduler -o wide` — NODE column must be wearables-pool node |
| Strategy | Recreate (singleton, must not run two copies) | `kubectl get deployment wearables-scheduler -o jsonpath='{.spec.strategy.type}'` = `Recreate` |
| Graceful shutdown | terminationGracePeriodSeconds=30 | `kubectl get deployment wearables-scheduler -o jsonpath='{.spec.template.spec.terminationGracePeriodSeconds}'` = 30 |
| Health | No restarts, pod in Running state | No restart count incrementing |

### wearables-messaging (TaskIQ worker)

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | >= 2 Running pods (KEDA-managed) | `kubectl get deployment wearables-messaging -o jsonpath='{.status.readyReplicas}'` >= 2 |
| Node selector | All pods on `wearables-pool` nodes | `kubectl get pods -l app=wearables-messaging -o wide` — NODE column must be wearables-pool nodes |
| Topology spread | maxSkew <= 1 across hostnames | Count pods per node; difference between most-loaded and least-loaded node must be <= 1 |
| Strategy | RollingUpdate | `kubectl get deployment wearables-messaging -o jsonpath='{.spec.strategy.type}'` = `RollingUpdate` |
| Graceful shutdown | terminationGracePeriodSeconds=80 | `kubectl get deployment wearables-messaging -o jsonpath='{.spec.template.spec.terminationGracePeriodSeconds}'` = 80 |
| Liveness probe | Shell-based heartbeat file check (`/tmp/taskiq_heartbeat` freshness < 60s) | `kubectl get deployment wearables-messaging -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'` — exec with `sh -c`, initialDelaySeconds=30, periodSeconds=10 |
| Health | Probes passing, no restarts | No restart count incrementing, pods in Running state |
| ScaledObject ready | READY=True | `kubectl get scaledobject wearables-worker-scaler -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'` = `True` |
| ScaledObject target | Targets wearables-messaging | `kubectl get scaledobject wearables-worker-scaler -o jsonpath='{.spec.scaleTargetRef.name}'` = `wearables-messaging` |
| ScaledObject min/max | minReplicaCount=2, maxReplicaCount=10 | `kubectl get scaledobject wearables-worker-scaler -o jsonpath='{.spec.minReplicaCount}'` = 2 and `{.spec.maxReplicaCount}` = 10 |
| HPA created by KEDA | HPA exists for wearables-messaging | `kubectl get hpa` — should show an HPA targeting wearables-messaging |
| TriggerAuthentication exists | redis-trigger-auth present | `kubectl get triggerauthentication redis-trigger-auth` — must exist |

## 5. Ingress & TLS

### Ingress resources

Run: `kubectl get ingress`

| Check | Expected | How to verify |
|-------|----------|---------------|
| api-gateway-ingress exists | Host: `test.eshop-test.com`, TLS secret: `eshop-test-wildcard-tls` | `kubectl get ingress api-gateway-ingress -o yaml` |
| wearables-ingress exists | Host: `wearables-test.eshop-test.com`, TLS secret: `eshop-test-wildcard-tls` | `kubectl get ingress wearables-ingress -o yaml` |

### NGINX Ingress Controller

| Check | Expected | How to verify |
|-------|----------|---------------|
| LoadBalancer IP | External IP = `34.159.106.171` | `kubectl get svc -n ingress-nginx` — EXTERNAL-IP column |
| Controller replicas | 2 pods on different nodes (required anti-affinity) | `kubectl get pods -n ingress-nginx -o wide` — check NODE column |
| Controller node pool | All on `default-pool` | Same command — verify nodes are default-pool nodes |

### HTTP to HTTPS redirect

```bash
curl -s -o /dev/null -w "%{http_code}" -H "Host: test.eshop-test.com" http://34.159.106.171/health
curl -s -o /dev/null -w "%{http_code}" -H "Host: wearables-test.eshop-test.com" http://34.159.106.171/health
```

Both must return 308.

### TLS endpoints reachable

```bash
curl -s -o /dev/null -w "%{http_code}" https://test.eshop-test.com/health          # expect 200
curl -s -o /dev/null -w "%{http_code}" https://wearables-test.eshop-test.com/health # expect 200
```

TLS certificate is valid if curl succeeds without `--insecure`.

## 6. Services & DNS Resolution

| Check | Expected | How to verify |
|-------|----------|---------------|
| api-gateway-http ClusterIP service exists | Port 80 -> 8000 | `kubectl get svc api-gateway-http` |
| hello-world-http ClusterIP service exists | Port 80 -> 8000 | `kubectl get svc hello-world-http` |
| wearables-http ClusterIP service exists | Port 80 -> 8000 | `kubectl get svc wearables-http` |
| pgbouncer ClusterIP service exists | Port 5432 -> 5432 | `kubectl get svc pgbouncer` |
| Internal DNS resolution | Services resolvable within cluster | `kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup api-gateway-http.default.svc.cluster.local` (skip if impractical) |

## 7. Resource Requests & Limits

Verify with: `kubectl get deployment <name> -o jsonpath='{.spec.template.spec.containers[0].resources}'`

| Service | CPU Request | Memory Request | CPU Limit | Memory Limit |
|---------|-------------|----------------|-----------|--------------|
| api-gateway-http | 50m | 128Mi | 200m | 256Mi |
| hello-world-http | 50m | 128Mi | 200m | 256Mi |
| wearables-http | 50m | 128Mi | 200m | 256Mi |
| wearables-messaging | 50m | 205Mi | 200m | 430Mi |
| pgbouncer | 50m | 64Mi | 200m | 128Mi |
| redis-exporter | 50m | 64Mi | 100m | 128Mi |

## Summary Format

After all checks, print:

```
=== Cluster Validation Summary ===

Section                    | Passed | Failed | Warnings
---------------------------|--------|--------|----------
1. Node Pool Health        |   X    |   X    |    X
2. System Components       |   X    |   X    |    X
3. Pod Health              |   X    |   X    |    X
4. Service Deployments     |   X    |   X    |    X
5. Ingress & TLS           |   X    |   X    |    X
6. Services & DNS          |   X    |   X    |    X
7. Resource Configuration  |   X    |   X    |    X
---------------------------|--------|--------|----------
TOTAL                      |   X    |   X    |    X

Result: PASS / FAIL
```

If any check fails, list the failed checks at the bottom with details.
