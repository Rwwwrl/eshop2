import asyncio
import sys
from pathlib import Path
from time import time

_HEARTBEAT_PATH = Path("/tmp/taskiq_heartbeat")
_HEARTBEAT_LOOP_INTERVAL_SECONDS = 10
_MAX_STALENESS_SECONDS = 60


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


def check_liveness() -> None:
    if not _HEARTBEAT_PATH.exists():
        sys.exit(1)

    try:
        written_at = float(_HEARTBEAT_PATH.read_text().strip())
    except (ValueError, OSError):
        sys.exit(1)

    if (time() - written_at) >= _MAX_STALENESS_SECONDS:
        sys.exit(1)

    sys.exit(0)
