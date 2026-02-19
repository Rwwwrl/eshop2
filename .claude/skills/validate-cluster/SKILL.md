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

| Check | Expected | How to verify |
|-------|----------|---------------|
| All nodes Ready | Every node shows `STATUS=Ready` | No node in `NotReady`, `SchedulingDisabled`, or unknown state |
| default-pool node count | >= 3 nodes with label `cloud.google.com/gke-nodepool=default-pool` | `kubectl get nodes -l cloud.google.com/gke-nodepool=default-pool` |
| wearables-pool node count | >= 2 nodes with label `cloud.google.com/gke-nodepool=wearables-pool` | `kubectl get nodes -l cloud.google.com/gke-nodepool=wearables-pool` |

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
| PgBouncer anti-affinity | Pods on different nodes | The two pods must be scheduled on different hostnames |
| PgBouncer strategy | `kubectl get deployment pgbouncer -o jsonpath='{.spec.strategy.type}'` | `Recreate` |
| PgBouncer probes | `kubectl get deployment pgbouncer -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'` | TCP socket on port 5432 |
| RedisInsight running | `kubectl get pods -l app=redisinsight` | 1 pod Running, container ready |
| RedisInsight node pool | `kubectl get pods -l app=redisinsight -o wide` | Pod on `default-pool` node |
| RedisInsight strategy | `kubectl get deployment redisinsight -o jsonpath='{.spec.strategy.type}'` | `Recreate` |
| RedisInsight probes | `kubectl get deployment redisinsight -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'` | HTTP GET on `/api/health` port 5540 |
| RedisInsight fsGroup | `kubectl get deployment redisinsight -o jsonpath='{.spec.template.spec.securityContext.fsGroup}'` | `1000` |
| RedisInsight PVC bound | `kubectl get pvc redisinsight-data` | Status `Bound` |

## 3. Pod Health (all namespaces)

Run: `kubectl get pods -A`

| Check | Expected | How to verify |
|-------|----------|---------------|
| No Pending pods | Zero pods in `Pending` state | `kubectl get pods -A --field-selector=status.phase=Pending` |
| No CrashLoopBackOff | Zero pods with CrashLoopBackOff | `kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.name}{" "}{range .status.containerStatuses[*]}{.state.waiting.reason}{end}{"\n"}{end}'` and grep for CrashLoopBackOff |
| No ImagePullBackOff | Zero pods with ImagePullBackOff or ErrImagePull | Same approach, grep for ImagePullBackOff or ErrImagePull |
| All pods containers ready | Every pod has all containers ready | Check READY column shows `N/N` (all containers) |

## 4. Service Deployments (test-eu)

For each deployment (HTTP servers and messaging workers), verify replica count and scheduling:

### api-gateway-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 Running pods | `kubectl get deployment api-gateway-http -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node selector | All pods on `default-pool` nodes | `kubectl get pods -l app=api-gateway-http -o wide` — NODE column must be default-pool nodes |
| Anti-affinity | Pods on different nodes | The two pods must be scheduled on different hostnames (required anti-affinity) |
| Health endpoints | Liveness and readiness probes passing | No restart count incrementing, pods in Running state |

### hello-world-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 Running pods | `kubectl get deployment hello-world-http -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node selector | All pods on `default-pool` nodes | `kubectl get pods -l app=hello-world-http -o wide` — NODE column must be default-pool nodes |
| Anti-affinity | Pods preferably on different nodes | Preferred (weight 100), so warn if co-located but don't fail |
| Health endpoints | Probes passing | No restart count incrementing |

### wearables-http

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 Running pods | `kubectl get deployment wearables-http -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node selector | All pods on `wearables-pool` nodes | `kubectl get pods -l app=wearables-http -o wide` — NODE column must be wearables-pool nodes |
| Topology spread | maxSkew <= 1 across hostnames | Count pods per node; the difference between the most-loaded and least-loaded node must be <= 1 |
| Health endpoints | Probes passing | No restart count incrementing |

### wearables-messaging (TaskIQ worker)

| Check | Expected | How to verify |
|-------|----------|---------------|
| Replicas | 2 Running pods | `kubectl get deployment wearables-messaging -o jsonpath='{.status.readyReplicas}'` = 2 |
| Node selector | All pods on `wearables-pool` nodes | `kubectl get pods -l app=wearables-messaging -o wide` — NODE column must be wearables-pool nodes |
| Strategy | Recreate (not RollingUpdate) | `kubectl get deployment wearables-messaging -o jsonpath='{.spec.strategy.type}'` = `Recreate` |
| Liveness probe | Shell-based heartbeat file check (`/tmp/taskiq_heartbeat` freshness < 60s) | `kubectl get deployment wearables-messaging -o jsonpath='{.spec.template.spec.containers[0].livenessProbe}'` — must use exec with `sh -c`, initialDelaySeconds=30, periodSeconds=10 |
| Health | Probes passing, no restarts | No restart count incrementing, pods in Running state |

## 5. Ingress & TLS

### Ingress resources

Run: `kubectl get ingress`

| Check | Expected | How to verify |
|-------|----------|---------------|
| api-gateway-ingress exists | Host: `test.eshop-test.com`, TLS secret: `eshop-test-wildcard-tls` | `kubectl get ingress api-gateway-ingress -o yaml` |
| wearables-ingress exists | Host: `wearables-test.eshop-test.com`, TLS secret: `eshop-test-wildcard-tls` | `kubectl get ingress wearables-ingress -o yaml` |
| redisinsight-ingress exists | Host: `redisinsight-test.eshop-test.com`, TLS secret: `eshop-test-wildcard-tls`, basic auth enabled | `kubectl get ingress redisinsight-ingress -o yaml` — must have `nginx.org/basic-auth-secret` annotation |

### NGINX Ingress Controller

| Check | Expected | How to verify |
|-------|----------|---------------|
| LoadBalancer IP | External IP = `34.159.106.171` | `kubectl get svc -n ingress-nginx` — EXTERNAL-IP column |
| Controller replicas | 2 pods on different nodes (required anti-affinity) | `kubectl get pods -n ingress-nginx -o wide` — check NODE column |
| Controller node pool | All on `default-pool` | Same command — verify nodes are default-pool nodes |

### HTTP to HTTPS redirect

Use `curl` to verify redirect behavior:

```bash
# Should return 308 redirect to HTTPS
curl -s -o /dev/null -w "%{http_code}" -H "Host: test.eshop-test.com" http://34.159.106.171/health

# Should return 308 redirect to HTTPS
curl -s -o /dev/null -w "%{http_code}" -H "Host: wearables-test.eshop-test.com" http://34.159.106.171/health

# Should return 308 redirect to HTTPS
curl -s -o /dev/null -w "%{http_code}" -H "Host: redisinsight-test.eshop-test.com" http://34.159.106.171/api/health
```

| Check | Expected | How to verify |
|-------|----------|---------------|
| api-gateway HTTP redirect | HTTP request returns 301 or 308 status | curl command above |
| wearables HTTP redirect | HTTP request returns 301 or 308 status | curl command above |
| redisinsight HTTP redirect | HTTP request returns 301 or 308 status | curl command above |

### TLS endpoints reachable

```bash
# Should return 200
curl -s -o /dev/null -w "%{http_code}" https://test.eshop-test.com/health

# Should return 200
curl -s -o /dev/null -w "%{http_code}" https://wearables-test.eshop-test.com/health

# Should return 401 (basic auth required)
curl -s -o /dev/null -w "%{http_code}" https://redisinsight-test.eshop-test.com/api/health
```

| Check | Expected | How to verify |
|-------|----------|---------------|
| api-gateway HTTPS reachable | Returns 200 on /health | curl command above |
| wearables HTTPS reachable | Returns 200 on /health | curl command above |
| redisinsight HTTPS basic auth | Returns 401 on /api/health (no credentials) | curl command above |
| TLS certificate valid | curl succeeds without `--insecure` flag | If curl fails with SSL error, certificate is invalid |

## 6. Services & DNS Resolution

| Check | Expected | How to verify |
|-------|----------|---------------|
| api-gateway-http ClusterIP service exists | Port 80 -> 8000 | `kubectl get svc api-gateway-http` |
| hello-world-http ClusterIP service exists | Port 80 -> 8000 | `kubectl get svc hello-world-http` |
| wearables-http ClusterIP service exists | Port 80 -> 8000 | `kubectl get svc wearables-http` |
| pgbouncer ClusterIP service exists | Port 5432 -> 5432 | `kubectl get svc pgbouncer` |
| redisinsight ClusterIP service exists | Port 80 -> 5540 | `kubectl get svc redisinsight` |
| Internal DNS resolution | Services resolvable within cluster | `kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- nslookup api-gateway-http.default.svc.cluster.local` (skip if impractical) |

## 7. Resource Requests & Limits

For each deployment, verify resource configuration matches manifests:

| Service | CPU Request | Memory Request | CPU Limit | Memory Limit |
|---------|-------------|----------------|-----------|--------------|
| api-gateway-http | 50m | 128Mi | 200m | 256Mi |
| hello-world-http | 50m | 128Mi | 200m | 256Mi |
| wearables-http | 50m | 128Mi | 200m | 256Mi |
| wearables-messaging | 50m | 205Mi | 200m | 430Mi |
| pgbouncer | 50m | 64Mi | 200m | 128Mi |
| redisinsight | 100m | 128Mi | 500m | 256Mi |

Verify with: `kubectl get deployment <name> -o jsonpath='{.spec.template.spec.containers[0].resources}'`

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
