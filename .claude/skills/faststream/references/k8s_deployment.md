# FastStream Kubernetes Deployment

The messaging worker is a **separate Deployment** from the HTTP server. Same Docker image, different command.

## Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: <service>-messaging
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
  template:
    spec:
      nodeSelector:
        cloud.google.com/gke-nodepool: default-pool
      terminationGracePeriodSeconds: 75
      containers:
        - name: <service>-messaging
          command:
            - poetry
            - run
            - uvicorn
            - <service>.messaging.main:app
            - --host
            - "0.0.0.0"
            - --port
            - "8001"
            - --workers
            - "1"
          ports:
            - containerPort: 8001
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 3
            timeoutSeconds: 5
          resources:
            requests:
              cpu: "50m"
              memory: "128Mi"
            limits:
              cpu: "200m"
              memory: "256Mi"
```

## Key Details

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Command | `uvicorn <service>.messaging.main:app` | ASGI app, not `faststream run` |
| Port | 8001 | HTTP server uses 8000 |
| `--workers` | 1 | Scale horizontally via replicas, not threads |
| `terminationGracePeriodSeconds` | 75 | `faststream_graceful_timeout (65s)` + 10s buffer |
| Liveness probe | `GET /health` on port 8001 | `make_ping_asgi` pings RabbitMQ broker |
| Readiness probe | None | Liveness is sufficient for a worker |
| Naming | `<service>-messaging` | Distinguishes from HTTP deployment |

## Graceful Shutdown

```
SIGTERM → broker stops accepting → drains in-flight messages (graceful_timeout=65s) → exit
```

- `faststream_graceful_timeout` (65s) controls how long broker waits for in-flight messages
- `terminationGracePeriodSeconds` (75s) must exceed graceful timeout + buffer
- No `preStop` hook needed — workers pull from RabbitMQ, no ingress traffic to drain
- K8s sends SIGTERM, then SIGKILL when grace period expires

## Kustomization Structure

```
deploy/k8s/services/<service>/
    base/messaging/
        deployment.yaml
        kustomization.yaml        # resources: [deployment.yaml]
    test-eu/messaging/
        kustomization.yaml        # resources: [../../base/messaging, ../shared]
```

The messaging overlay includes the shared ConfigMap/Secret from the service's `shared/` folder.
