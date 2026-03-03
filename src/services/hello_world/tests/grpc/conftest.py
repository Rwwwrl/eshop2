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
