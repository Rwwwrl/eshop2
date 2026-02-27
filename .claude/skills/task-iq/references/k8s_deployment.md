# TaskIQ Kubernetes Deployment

## Manifest Structure

```
deploy/k8s/services/<service>/
    base/background-tasks/
        workers-deployment.yaml
        scheduler-deployment.yaml
        kustomization.yaml
    <env>/background-tasks/
        deployment.yaml
        kustomization.yaml
```

## Process Model

TaskIQ always spawns a main orchestrator + N child worker processes (even with `--workers 1` = 2 OS processes). The main process does NOT process tasks — it only manages children.

Use `--workers 1` in k8s. One worker process per pod, scale horizontally with replicas. This follows the Kubernetes "one process per container" principle:
- Liveness probe accurately reflects the single worker's health
- No silent worker death hidden behind a healthy sibling process
- Resource limits map 1:1 to actual worker consumption
- HPA/KEDA scaling granularity is per-worker

## Memory Budgeting

Formula: `idle_memory + max_async_tasks × per_task_memory`

| Component | Measured (macOS) | Estimated (Linux slim) |
|-----------|-----------------|----------------------|
| Main process (orchestrator) | ~63 MB | ~50 MB |
| Worker child process | ~103 MB | ~80 MB |
| **Idle total (`--workers 1`)** | **~166 MB** | **~130 MB** |

Resource calculation (using 75Mi per task estimate, 4 max async tasks):
- `requests.memory` = idle + 1 × per_task = 130 + 75 = **205Mi** (guaranteed minimum)
- `limits.memory` = idle + max_async_tasks × per_task = 130 + 4 × 75 = **430Mi** (worst case)

Add a NOTE comment above resources in the deployment manifest explaining the budget formula.

## Base Deployment (wearables example)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wearables-background-tasks
spec:
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: wearables-background-tasks
  template:
    metadata:
      labels:
        app: wearables-background-tasks
    spec:
      nodeSelector:
        cloud.google.com/gke-nodepool: wearables-pool
      topologySpreadConstraints:
        - topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: wearables-background-tasks
      terminationGracePeriodSeconds: 80
      containers:
        - name: wearables-background-tasks
          command: ["poetry", "run", "taskiq", "worker", "--workers", "1", "--max-async-tasks", "4", "--wait-tasks-timeout", "65", "--shutdown-timeout", "10", "wearables.background_tasks.main:broker", "wearables.background_tasks.tasks"]
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
          # NOTE @sosov: memory budget: ~130Mi idle (main + 1 worker) + 75Mi per async task.
          # requests = 130 idle + 75 × 1 task = 205Mi (guaranteed minimum).
          # limits = 130 idle + 75 × 4 tasks (--max-async-tasks) = 430Mi (worst case).
          resources:
            requests:
              cpu: "50m"
              memory: "205Mi"
            limits:
              cpu: "200m"
              memory: "430Mi"
```

Rules:
- Deployment name: `<service>-background-tasks`
- Same Docker image as HTTP deployment (no CMD in Dockerfile — command in manifest)
- Worker command: `taskiq worker --workers 1 --max-async-tasks 4 --wait-tasks-timeout 65 --shutdown-timeout 10 <service>.background_tasks.main:broker <service>.background_tasks.tasks`
- Always use `--workers 1` — scale with k8s replicas, not in-process workers
- Always set `--max-async-tasks` to bound memory usage
- No Service resource needed (worker doesn't receive traffic)
- Always set `terminationGracePeriodSeconds` to cover full shutdown (wait-tasks + shutdown + buffer)
- Always set `--wait-tasks-timeout` and `--shutdown-timeout` explicitly
- Base includes `strategy: Recreate`, `nodeSelector`, and `topologySpreadConstraints` (without `maxSkew`) — overlays set `replicas`, `maxSkew`, and `image`

## Scheduler Deployment

The scheduler is a separate process that only dispatches scheduled tasks to the broker — it does not execute them.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wearables-scheduler
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: wearables-scheduler
  template:
    metadata:
      labels:
        app: wearables-scheduler
    spec:
      nodeSelector:
        cloud.google.com/gke-nodepool: wearables-pool
      terminationGracePeriodSeconds: 30
      containers:
        - name: wearables-scheduler
          command: ["poetry", "run", "taskiq", "scheduler", "wearables.background_tasks.main:scheduler", "wearables.background_tasks.tasks", "--skip-first-run"]
          resources:
            requests:
              cpu: "25m"
              memory: "100Mi"
            limits:
              cpu: "100m"
              memory: "200Mi"
```

Rules:
- **Exactly 1 replica** — multiple schedulers = duplicate task dispatches
- **`strategy: Recreate`** — prevents two schedulers running during rollout
- **`--skip-first-run`** — on startup, the scheduler checks for overdue tasks and would fire them all immediately. This flag waits for the next natural cron tick instead, preventing a burst on every deploy/restart
- Task modules must be passed as CLI args (e.g., `wearables.background_tasks.tasks`) so the scheduler can read `schedule=[...]` labels
- Lightweight resources — scheduler only polls schedule sources and calls `.kiq()`, no task execution
- No `WORKER_STARTUP`/`WORKER_SHUTDOWN` events fire in the scheduler process — those are worker-only

## Graceful Shutdown

K8s pod termination sends exactly **one SIGTERM**, then **one SIGKILL** when `terminationGracePeriodSeconds` expires. No retries, no second SIGTERM.

TaskIQ shutdown sequence after SIGTERM:

```
SIGTERM
  ↓
1. Process manager sends SIGINT to worker child process
2. Worker sets shutdown_event → prefetcher stops pulling from RabbitMQ
3. Prefetched-but-unstarted messages stay in RabbitMQ (picked up by other workers)
4. QUEUE_DONE sentinel placed on internal queue
5. Runner calls: asyncio.wait(tasks, timeout=wait_tasks_timeout)  ← Phase 1
6. broker.shutdown() called with asyncio.wait_for(timeout=shutdown_timeout)  ← Phase 2
   - WORKER_SHUTDOWN event handlers (engine dispose, heartbeat stop)
   - Middleware shutdown
   - RabbitMQ connection close
7. Process exits
```

Timeout alignment:

```
terminationGracePeriodSeconds (80s)
├── wait-tasks-timeout (65s)  ← in-flight task drain
├── shutdown-timeout (10s)    ← broker cleanup
└── 5s buffer                 ← process overhead
```

No `preStop` hook needed — background task workers pull from Redis, there's no ingress endpoint removal to wait for (unlike HTTP pods)

## Liveness Probe

Heartbeat file mechanism in `libs/taskiq_ext/liveness_check.py`:

1. `start_heartbeat_loop()` — writes timestamp to `/tmp/taskiq_heartbeat` every 10s
2. `stop_heartbeat_loop()` — cancels the loop task, removes file

The k8s liveness probe uses a lightweight shell command to check the heartbeat file freshness (< 60s). This avoids the overhead of `poetry run python` which can timeout on CPU-constrained containers.

## CI/CD

The deploy workflow (`called-deploy-service-to-gke.yaml`) has a `run_background_tasks_deployment` input:

```yaml
run_background_tasks_deployment:
  required: false
  type: boolean
  default: false
```

Enable it for services that have a background tasks worker. The workflow:
1. Runs `kustomize build . | kubectl apply -f -` in the background-tasks overlay — deploys both worker and scheduler
2. Waits for both rollouts: `<service>-background-tasks` and `<service>-scheduler`
