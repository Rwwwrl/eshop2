from collections.abc import Callable
from functools import wraps
from typing import Any

from faststream import ContextRepo
from faststream.exceptions import AckMessage, NackMessage, RejectMessage
from rabbitmq_topology.services import publish_to_delayed_retry_queue

from libs.faststream_ext.consts import RETRY_ATTEMPT_HEADER
from libs.faststream_ext.exceptions import DuplicateMessageError


def retry(
    max_attempts: int,
    countdown: int,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    dlq: bool = False,
) -> Callable[..., Any]:
    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)

            except (AckMessage, NackMessage, RejectMessage, DuplicateMessageError):
                raise

            except exceptions:
                context: ContextRepo = kwargs["context"]
                message = context.resolve("message")
                broker = context.resolve("broker")
                queue = context.resolve("handler_").queue

                retry_attempt = int(message.headers.get(RETRY_ATTEMPT_HEADER, 0)) + 1

                if retry_attempt > max_attempts:
                    if dlq:
                        raise NackMessage(requeue=False)
                    raise

                extra_headers = {RETRY_ATTEMPT_HEADER: str(retry_attempt)}
                await publish_to_delayed_retry_queue(
                    broker=broker,
                    message=message,
                    original_queue=queue,
                    extra_headers=extra_headers,
                    expiration=countdown,
                )

                # NOTE @sosov: Re-raise so FastStream applies its ack_policy naturally.
                # ACK → message is acked (retry copy already in delayed-retry queue).
                # REJECT_ON_ERROR → message is nacked → routed to DLQ via DLX.
                raise

        return _wrapper

    return _decorator
