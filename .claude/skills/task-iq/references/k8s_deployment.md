# TaskIQ Kubernetes Deployment

## Manifest Structure

```
deploy/k8s/services/<service>/
    base/messaging/
        deployment.yaml
        kustomization.yaml
    <env>/messaging/
        deployment.yaml
        kustomization.yaml
```

## Base Deployment (wearables example)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wearables-messaging
spec:
  selector:
    matchLabels:
      app: wearables-messaging
  template:
    metadata:
      labels:
        app: wearables-messaging
    spec:
      containers:
        - name: wearables-messaging
          command: ["poetry", "run", "taskiq", "worker", "wearables.messaging.main:broker", "wearables.messaging.handlers"]
          livenessProbe:
            exec:
              command:
                - sh
                - -c
                - |
                  test -f /tmp/taskiq_heartbeat &&
                  written_at=$(cat /tmp/taskiq_heartbeat) &&
                  now=$(date +%s) &&
                  age=$((now - ${written_at%%.*})) &&
                  test "$age" -lt 60
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

Rules:
- Deployment name: `<service>-messaging`
- Same Docker image as HTTP deployment (no CMD in Dockerfile — command in manifest)
- Worker command format: `taskiq worker <service>.messaging.main:broker <service>.messaging.handlers`
- No Service resource needed (worker doesn't receive traffic)

## Liveness Probe

Heartbeat file mechanism in `libs/taskiq_ext/liveness_check.py`:

1. `start_heartbeat_loop()` — writes timestamp to `/tmp/taskiq_heartbeat` every 10s
2. `stop_heartbeat_loop()` — cancels the loop task, removes file

The k8s liveness probe uses a lightweight shell command to check the heartbeat file freshness (< 60s). This avoids the overhead of `poetry run python` which can timeout on CPU-constrained containers.

## CI/CD

The deploy workflow (`called-deploy-service-to-gke.yaml`) has a `run_messaging_deployment` input:

```yaml
run_messaging_deployment:
  required: false
  type: boolean
  default: false
```

Enable it for services that have a messaging worker.
