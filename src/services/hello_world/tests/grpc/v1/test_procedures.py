import grpc
import pytest
from grpc_protos.v1.hello_world import hello_world_pb2, hello_world_pb2_grpc


@pytest.mark.asyncio(loop_scope="session")
async def test_get_host_when_called(hello_world_grpc_channel: grpc.aio.Channel) -> None:
    stub = hello_world_pb2_grpc.HelloWorldServiceStub(channel=hello_world_grpc_channel)
    response = await stub.GetHost(request=hello_world_pb2.GetHostRequest())

    assert response.host
    assert isinstance(response.host, str)
