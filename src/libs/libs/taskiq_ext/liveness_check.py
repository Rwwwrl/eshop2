import asyncio
from pathlib import Path
from time import time

_HEARTBEAT_PATH = Path("/tmp/taskiq_heartbeat")
_HEARTBEAT_LOOP_INTERVAL_SECONDS = 10


async def _heartbeat_loop() -> None:
    while True:
        _HEARTBEAT_PATH.write_text(str(time()))
        await asyncio.sleep(_HEARTBEAT_LOOP_INTERVAL_SECONDS)


def start_heartbeat_loop() -> None:
    _HEARTBEAT_PATH.write_text(str(time()))
    asyncio.create_task(_heartbeat_loop(), name=_heartbeat_loop.__name__)


async def stop_heartbeat_loop() -> None:
    for task in asyncio.all_tasks():
        if task.get_name() == _heartbeat_loop.__name__:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            break

    _HEARTBEAT_PATH.unlink(missing_ok=True)
