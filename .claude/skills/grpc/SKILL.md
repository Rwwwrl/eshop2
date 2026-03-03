---
name: grpc
description: Guides gRPC service development in MyEshop. Use when adding a new gRPC service, writing proto files, implementing a servicer, adding RPC procedures, configuring a gRPC client channel, writing gRPC tests, or setting up Kubernetes manifests for a gRPC deployment. Trigger phrases include "grpc", "proto", "servicer", "rpc procedure", "protobuf", "grpc channel", "grpc stub", "grpc health check", "grpc deployment".
---

# gRPC

## Quick Reference

| Component           | Location                                    | Import / Command                                             |
| ------------------- | ------------------------------------------- | ------------------------------------------------------------ |
| Proto source        | `src/grpc_protos/grpc_protos/v1/<service>/` | —                                                            |
| Generated code      | same directory as proto                     | `from grpc_protos.v1.<service> import <service>_pb2`         |
| Server entry point  | `<service>/grpc/main.py`                    | `python -m <service>.grpc.main`                              |
| Procedures          | `<service>/grpc/v1/procedures.py`           | called from servicer in `grpc/main.py`                       |
| gRPC client channel | `<service>/http/main.py` (lifespan)         | `grpc.aio.insecure_channel(target=...)`                      |
| Code generation     | `src/grpc_protos/justfile`                  | `just --justfile src/grpc_protos/justfile generate-protos`   |
| Test server         | `tests/grpc/conftest.py`                    | real `grpc.aio.server()` on port `0`                         |
| K8s manifests       | `deploy/k8s/services/<service>/base/grpc/`  | —                                                            |

---

## File Structure

```
src/
  grpc_protos/
    grpc_protos/
      v1/
        hello_world/
          hello_world.proto              # Source of truth — edit this
          hello_world_pb2.py             # Generated — do not edit manually
          hello_world_pb2_grpc.py        # Generated — do not edit manually
          hello_world_pb2.pyi            # Generated type stubs
    pyproject.toml
    justfile                             # just --justfile src/grpc_protos/justfile generate-protos

src/services/hello_world/
  hello_world/
    grpc/
      __init__.py
      main.py                            # Servicer class + _serve() entry point
      v1/
        __init__.py
        procedures.py                    # RPC handler logic

  tests/
    grpc/
      conftest.py                        # Real in-process gRPC test server
      v1/
        test_procedures.py

deploy/k8s/services/hello-world/
  base/grpc/
    deployment.yaml
    service.yaml
    kustomization.yaml
  test-eu/grpc/
    deployment.yaml
    hpa.yaml
    kustomization.yaml
```

---

## Proto File

```proto
syntax = "proto3";
package grpc_protos.v1.hello_world;

service HelloWorldService {
  rpc GetHost (GetHostRequest) returns (GetHostResponse);
}

message GetHostRequest {}

message GetHostResponse {
  string host = 1;
}
```

- Proto package name mirrors the Python namespace: `grpc_protos.v1.<service_name>`.
- One `.proto` file per service. Add messages and RPCs to the same file as the service grows.
- Run `just --justfile src/grpc_protos/justfile generate-protos` from the **project root** after any proto change.

### Code Generation

```bash
# Run from project root
just --justfile src/grpc_protos/justfile generate-protos
```

The justfile runs `grpc_tools.protoc` with root-relative paths, then fixes the import in `_pb2_grpc.py` with `sed`:

```just
generate-protos:
    poetry run python -m grpc_tools.protoc \
        --proto_path=src/grpc_protos/grpc_protos/v1/hello_world \
        --python_out=src/grpc_protos/grpc_protos/v1/hello_world \
        --grpc_python_out=src/grpc_protos/grpc_protos/v1/hello_world \
        --pyi_out=src/grpc_protos/grpc_protos/v1/hello_world \
        src/grpc_protos/grpc_protos/v1/hello_world/hello_world.proto
    sed -i '' 's/^import hello_world_pb2/from grpc_protos.v1.hello_world import hello_world_pb2/' \
        src/grpc_protos/grpc_protos/v1/hello_world/hello_world_pb2_grpc.py
```

- Always commit generated `_pb2.py`, `_pb2_grpc.py`, and `_pb2.pyi` files — they are not `.gitignore`d.
- The `sed` fix is mandatory: `protoc` generates a bare `import <service>_pb2` which breaks in a package namespace.
- When adding a new service, duplicate the pattern above in the justfile for the new service's proto path.

---

## Server: `grpc/main.py`

```python
import asyncio
import signal

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_protos.v1.hello_world import hello_world_pb2, hello_world_pb2_grpc

from hello_world.grpc.v1.procedures import get_host_procedure
from hello_world.settings import settings


class HelloWorldServiceServicer(hello_world_pb2_grpc.HelloWorldServiceServicer):
    async def GetHost(
        self,
        request: hello_world_pb2.GetHostRequest,
        context: grpc.aio.ServicerContext,
    ) -> hello_world_pb2.GetHostResponse:
        return await get_host_procedure(request=request, context=context)


async def _serve() -> None:
    # setup_logging, setup_sentry, DB engine init go here — see references/server.md

    server = grpc.aio.server()

    hello_world_pb2_grpc.add_HelloWorldServiceServicer_to_server(
        servicer=HelloWorldServiceServicer(), server=server,
    )

    health_servicer = health.aio.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(servicer=health_servicer, server=server)
    await health_servicer.set(service="", status=health_pb2.HealthCheckResponse.SERVING)

    server.add_insecure_port(address="[::]:50051")
    await server.start()

    async def _graceful_shutdown() -> None:
        await health_servicer.set(service="", status=health_pb2.HealthCheckResponse.NOT_SERVING)
        await server.stop(grace=30)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_graceful_shutdown()))

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(_serve())
```

Rules:

- Use `import grpc` — access async API as `grpc.aio.server()`, `grpc.aio.ServicerContext`.
- Always register `grpcio-health-checking`'s `HealthServicer` — Kubernetes uses it for `grpc` probes.
- Health check uses `service=""` — this sets status for all registered services globally.
- Set health to `NOT_SERVING` before `server.stop()` — drains traffic gracefully before termination.
- Use `grace=30` in `server.stop()` to wait for in-flight RPCs.
- Signal handler wraps the async shutdown function in `asyncio.create_task()` — signal handlers must be synchronous.
- `server.wait_for_termination()` blocks until shutdown completes; do not use a manual `stop_event`.
- The servicer method delegates immediately to a procedure function. Never put business logic in the servicer class.
- Entry point is `asyncio.run(_serve())` — no ASGI, no uvicorn.

See [references/server.md](references/server.md) for the full implementation with logging, Sentry, and DB setup.

---

## Procedure: `grpc/v1/procedures.py`

```python
import socket

import grpc
from grpc_protos.v1.hello_world import hello_world_pb2


async def get_host_procedure(
    request: hello_world_pb2.GetHostRequest,
    context: grpc.aio.ServicerContext,
) -> hello_world_pb2.GetHostResponse:
    hostname = socket.gethostname()
    return hello_world_pb2.GetHostResponse(host=hostname)
```

Rules:

- Name the file `procedures.py` — this is the gRPC equivalent of HTTP `routes.py` and messaging `handlers.py`.
- Each RPC maps to one top-level `async def` function.
- Always pass `request` and `context` as keyword arguments (project convention).
- Use `context: grpc.aio.ServicerContext` to set error codes: `await context.abort(grpc.StatusCode.NOT_FOUND, "...")`.
- Procedures delegate to `services.py` for business logic, just like HTTP routes do.

---

## gRPC Client (in another service)

```python
# In the consuming service's http/main.py lifespan:
import grpc
from grpc_protos.v1.hello_world import hello_world_pb2, hello_world_pb2_grpc

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    channel = grpc.aio.insecure_channel(target=settings.hello_world_grpc_url)
    app.state.hello_world_grpc_channel = channel
    yield
    await channel.close()

# In a route handler:
async def some_route(request: Request) -> SomeResponse:
    stub = hello_world_pb2_grpc.HelloWorldServiceStub(
        channel=request.app.state.hello_world_grpc_channel,
    )
    response = await stub.GetHost(request=hello_world_pb2.GetHostRequest())
    ...
```

Rules:

- Create one channel per service on startup — channels are expensive to create and meant to be long-lived.
- Store the channel on `app.state` in FastAPI's lifespan.
- Create a new stub per request — stubs are lightweight wrappers around a channel.
- The URL setting is `HELLO_WORLD_GRPC_URL: "hello-world:50051"` in the k8s ConfigMap.
- Use `insecure_channel` for in-cluster traffic — TLS termination is at the ingress layer.

---

## Tests

```python
# tests/grpc/conftest.py — session-scoped server on port 0
@pytest_asyncio.fixture(scope="session")
async def grpc_server() -> AsyncGenerator[tuple[grpc.aio.Server, int], None]:
    server = grpc.aio.server()
    hello_world_pb2_grpc.add_HelloWorldServiceServicer_to_server(
        servicer=HelloWorldServiceServicer(), server=server,
    )
    port = server.add_insecure_port(address="[::]:0")  # OS assigns free port
    await server.start()
    yield server, port
    await server.stop(grace=0)

# tests/grpc/v1/test_procedures.py
@pytest.mark.asyncio(loop_scope="session")
async def test_get_host_when_called(hello_world_grpc_channel: grpc.aio.Channel) -> None:
    stub = hello_world_pb2_grpc.HelloWorldServiceStub(channel=hello_world_grpc_channel)
    response = await stub.GetHost(request=hello_world_pb2.GetHostRequest())
    assert response.host
```

Rules:

- Use a real `grpc.aio.server()` — no mocks. The in-process server gives full integration confidence.
- Bind to port `0` — the OS assigns a free port, preventing conflicts in CI.
- All gRPC fixtures are `scope="session"` — one server for the entire test run.
- Do NOT register `HealthServicer` in the test server.

See [references/tests.md](references/tests.md) for the full fixture and test file implementations.

---

## Kubernetes Manifests

Key differences from HTTP deployments:

- Command is `python -m <service>.grpc.main` — not uvicorn.
- Probes use `grpc:` protocol (requires `grpcio-health-checking` in the image).
- `terminationGracePeriodSeconds: 60` — must exceed the `grace=30` in `server.stop()`.
- No Ingress — gRPC services are ClusterIP only (internal cluster traffic).
- The k8s Service `name` becomes the DNS hostname other services use to connect.
- `podAntiAffinity` prevents two gRPC pods on the same node — HPA `minReplicas: 2` ensures this is satisfiable.
- `livenessProbe.initialDelaySeconds: 30` — gRPC takes longer to start (DB engine, Sentry setup).

See [references/k8s_manifests.md](references/k8s_manifests.md) for full manifest files (base + test-eu overlay).

---

## Dependencies

Add to the service that **runs the gRPC server**:

```bash
poetry add grpcio grpcio-health-checking
poetry add --group dev grpcio-tools
```

Add to the service that **calls the gRPC server** (client only):

```bash
poetry add grpcio
```

Add `myeshop-grpc-protos` to any service that uses the proto stubs:

```toml
# pyproject.toml (dev/local — path dep)
myeshop-grpc-protos = { path = "../../grpc_protos", develop = true }
```

---

## `grpc_protos` Package Rules

- Lives at `src/grpc_protos/` — a separate Poetry package (`myeshop-grpc-protos`), published to the internal registry.
- Namespace: `grpc_protos.v1.<service_name>` — version prefix in both the Python package and proto `package` declaration.
- `grpc_protos` must not import `libs`, any service, `messaging_contracts`, or `rabbitmq_topology` — enforced by `.importlinter`.
- Add a new service's proto at `grpc_protos/v1/<new_service>/`.
- Bump `grpc_protos` version after adding or changing any proto.

---

## Adding a New gRPC Service — Checklist

1. Add `.proto` file at `src/grpc_protos/grpc_protos/v1/<service>/`
2. Add the new service to the `generate-protos` recipe in `src/grpc_protos/justfile`
3. Run `just --justfile src/grpc_protos/justfile generate-protos` and commit generated files
4. Bump `grpc_protos` version
5. Add `grpcio`, `grpcio-health-checking` to the service's `pyproject.toml`
6. Add `myeshop-grpc-protos` path dep to the service's `pyproject.toml`
7. Create `<service>/grpc/__init__.py`, `grpc/main.py`, `grpc/v1/__init__.py`, `grpc/v1/procedures.py`
8. Implement servicer and `_serve()` in `grpc/main.py` (see [references/server.md](references/server.md))
9. Implement procedure functions in `grpc/v1/procedures.py`
10. Expose port `50051` in Dockerfile (alongside any other ports)
11. Create `deploy/k8s/services/<service>/base/grpc/` manifests (see [references/k8s_manifests.md](references/k8s_manifests.md))
12. Create `deploy/k8s/services/<service>/test-eu/grpc/` overlay
13. Add the client channel to the consuming service's lifespan (if any)
14. Add `grpcio` + `myeshop-grpc-protos` to the consuming service
15. Write tests in `tests/grpc/conftest.py` and `tests/grpc/v1/test_procedures.py` (see [references/tests.md](references/tests.md))
16. Update `.importlinter` contracts if a new top-level package was added
