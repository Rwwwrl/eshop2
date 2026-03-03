# gRPC Server: Full `grpc/main.py` Implementation

Real implementation from `src/services/hello_world/hello_world/grpc/main.py`.

```python
import asyncio
import logging
import signal
from importlib.metadata import version

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_protos.v1.hello_world import hello_world_pb2, hello_world_pb2_grpc
from libs.common.enums import ServiceNameEnum
from libs.grpc_ext.interceptors.request_id import RequestIdServerInterceptor
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum
from libs.sentry_ext import setup_sentry
from libs.sqlmodel_ext import Session

from hello_world.grpc.v1.procedures import get_host_procedure
from hello_world.settings import settings
from hello_world.utils import init_sqlmodel_engine


class HelloWorldServiceServicer(hello_world_pb2_grpc.HelloWorldServiceServicer):
    async def GetHost(
        self,
        request: hello_world_pb2.GetHostRequest,
        context: grpc.aio.ServicerContext,
    ) -> hello_world_pb2.GetHostResponse:
        return await get_host_procedure(request=request, context=context)


async def _serve() -> None:
    setup_logging(settings=settings, service_name=ServiceNameEnum.HELLO_WORLD, process_type=ProcessTypeEnum.GRPC)
    setup_sentry(settings=settings, release=version("hello-world"))

    db_url = settings.postgres_pooler_db_url or settings.postgres_direct_db_url
    engine = init_sqlmodel_engine(db_url=db_url)
    Session.configure(bind=engine)

    server = grpc.aio.server(interceptors=[RequestIdServerInterceptor()])

    hello_world_pb2_grpc.add_HelloWorldServiceServicer_to_server(
        servicer=HelloWorldServiceServicer(),
        server=server,
    )

    health_servicer = health.aio.HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(servicer=health_servicer, server=server)
    await health_servicer.set(service="", status=health_pb2.HealthCheckResponse.SERVING)

    server.add_insecure_port(address="[::]:50051")
    await server.start()
    logging.info("gRPC server started on port 50051")

    async def _graceful_shutdown() -> None:
        logging.info("Starting graceful shutdown...")
        await health_servicer.set(service="", status=health_pb2.HealthCheckResponse.NOT_SERVING)
        await server.stop(grace=30)
        await engine.dispose()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_graceful_shutdown()))

    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(_serve())
```

## Annotations

| Section | Detail |
| ------- | ------ |
| `setup_logging(...)` | Call first in `_serve()`, before any other setup. `ProcessTypeEnum.GRPC` distinguishes logs from HTTP/messaging processes. |
| `setup_sentry(...)` | Call right after logging. Use `version("hello-world")` (package name from pyproject.toml). |
| DB setup | `init_sqlmodel_engine(db_url=...)` + `Session.configure(bind=engine)`. Prefer `postgres_pooler_db_url`, fall back to direct. |
| `health_servicer` | Register **after** the service servicer. `service=""` sets status for all services globally — don't use per-servicer name. |
| `server.wait_for_termination()` | Blocks until the server shuts down. Signal handler triggers `_graceful_shutdown()` via `asyncio.create_task()`. |
| `_graceful_shutdown()` | Nested async function. Sets health to `NOT_SERVING` first, then `server.stop(grace=30)`, then `engine.dispose()`. |
| Signal handler | `loop.add_signal_handler(sig, lambda: asyncio.create_task(_graceful_shutdown()))` — wraps the coroutine in a task since signal handlers must be synchronous. |
