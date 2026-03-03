import logging
import socket

import grpc
from grpc_protos.v1.hello_world import hello_world_pb2

_logger = logging.getLogger(__name__)


async def get_host_procedure(
    request: hello_world_pb2.GetHostRequest,
    context: grpc.aio.ServicerContext,
) -> hello_world_pb2.GetHostResponse:
    hostname = socket.gethostname()
    _logger.info("get_host_procedure called, hostname: %s", hostname)
    return hello_world_pb2.GetHostResponse(host=hostname)
