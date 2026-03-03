# gRPC Tests: Full Implementation

## `tests/grpc/conftest.py`

```python
from collections.abc import AsyncGenerator

import grpc
import pytest_asyncio
from grpc_protos.v1.hello_world import hello_world_pb2_grpc
from hello_world.grpc.main import HelloWorldServiceServicer


@pytest_asyncio.fixture(scope="session")
async def grpc_server() -> AsyncGenerator[tuple[grpc.aio.Server, int], None]:
    server = grpc.aio.server()
    hello_world_pb2_grpc.add_HelloWorldServiceServicer_to_server(
        servicer=HelloWorldServiceServicer(),
        server=server,
    )
    port = server.add_insecure_port(address="[::]:0")
    await server.start()
    yield server, port
    await server.stop(grace=0)


@pytest_asyncio.fixture(scope="session")
async def hello_world_grpc_channel(
    grpc_server: tuple[grpc.aio.Server, int],
) -> AsyncGenerator[grpc.aio.Channel, None]:
    _, port = grpc_server
    async with grpc.aio.insecure_channel(target=f"localhost:{port}") as channel:
        yield channel
```

## `tests/grpc/v1/test_procedures.py`

```python
import grpc
import pytest
from grpc_protos.v1.hello_world import hello_world_pb2, hello_world_pb2_grpc


@pytest.mark.asyncio(loop_scope="session")
async def test_get_host_when_called(hello_world_grpc_channel: grpc.aio.Channel) -> None:
    stub = hello_world_pb2_grpc.HelloWorldServiceStub(channel=hello_world_grpc_channel)
    response = await stub.GetHost(request=hello_world_pb2.GetHostRequest())

    assert response.host
    assert isinstance(response.host, str)
```

## Rules

- Port `0` — OS assigns a free port, preventing CI conflicts.
- `scope="session"` for all gRPC fixtures — one server for the entire test run.
- `grace=0` in teardown — no need to drain in-flight RPCs during tests.
- `@pytest.mark.asyncio(loop_scope="session")` — consistent with project-wide pytest-asyncio setting.
- Create a stub per test, not per fixture — stubs are lightweight wrappers.
- Do NOT include the `HealthServicer` in the test server — tests call procedures directly, not health checks.
