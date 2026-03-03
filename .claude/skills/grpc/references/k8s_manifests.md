# gRPC Kubernetes Manifests: Full Implementation

## `base/grpc/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-world-grpc
spec:
  strategy:
    type: RollingUpdate
  selector:
    matchLabels:
      app: hello-world-grpc
  template:
    metadata:
      labels:
        app: hello-world-grpc
    spec:
      terminationGracePeriodSeconds: 60
      nodeSelector:
        cloud.google.com/gke-nodepool: default-pool
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchLabels:
                  app: hello-world-grpc
              topologyKey: kubernetes.io/hostname
      containers:
        - name: hello-world
          command: ["poetry", "run", "python", "-m", "hello_world.grpc.main"]
          envFrom:
            - configMapRef:
                name: hello-world-config
            - secretRef:
                name: hello-world-secrets
          ports:
            - containerPort: 50051
          resources:
            requests:
              cpu: "50m"
              memory: "128Mi"
            limits:
              cpu: "200m"
              memory: "256Mi"
          livenessProbe:
            grpc:
              port: 50051
            initialDelaySeconds: 30
            periodSeconds: 10
            failureThreshold: 3
            successThreshold: 1
            timeoutSeconds: 1
          readinessProbe:
            grpc:
              port: 50051
            initialDelaySeconds: 3
            periodSeconds: 5
            failureThreshold: 3
            successThreshold: 1
            timeoutSeconds: 1
```

## `base/grpc/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hello-world  # DNS hostname used by clients: hello-world:50051
spec:
  type: ClusterIP    # gRPC is internal only — no Ingress
  selector:
    app: hello-world-grpc
  ports:
    - port: 50051
      targetPort: 50051
```

## `base/grpc/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
  - ../shared
```

## `test-eu/grpc/deployment.yaml` (overlay patch)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-world-grpc
spec:
  template:
    spec:
      containers:
        - name: hello-world
          image: hello-world
          imagePullPolicy: Always
```

## `test-eu/grpc/hpa.yaml`

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hello-world-grpc
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: hello-world-grpc
  minReplicas: 2
  maxReplicas: 4
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## `test-eu/grpc/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base/grpc
  - hpa.yaml
  - ../shared
patches:
  - path: deployment.yaml
```

## Rules

- `terminationGracePeriodSeconds: 60` must exceed the `grace=30` passed to `server.stop()`.
- `podAntiAffinity` with `requiredDuringSchedulingIgnoredDuringExecution` — prevents two gRPC pods scheduling on the same node. Same pattern as HTTP deployments.
- `livenessProbe.initialDelaySeconds: 30` — gRPC server takes longer to start than HTTP (DB engine init, sentry setup).
- `readinessProbe.initialDelaySeconds: 3` — fast readiness check.
- Service `name: hello-world` (not `hello-world-grpc`) — this is the DNS name clients use to connect (`hello-world:50051`).
- `selector: app: hello-world-grpc` in the Service — matches the Deployment label, not the Service name.
- The overlay patch only sets `image` and `imagePullPolicy: Always` — everything else comes from `base/`.
- HPA `minReplicas: 2` — ensures anti-affinity can be satisfied (needs at least 2 nodes).
