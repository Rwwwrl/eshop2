from time import time

import pytest
from libs.taskiq_ext.liveness_check import _HEARTBEAT_PATH, _MAX_STALENESS_SECONDS, check_liveness


@pytest.fixture(autouse=True)
def _cleanup_heartbeat_file():
    yield
    _HEARTBEAT_PATH.unlink(missing_ok=True)


def test_check_liveness_when_heartbeat_file_missing():
    _HEARTBEAT_PATH.unlink(missing_ok=True)

    with pytest.raises(SystemExit, match="1"):
        check_liveness()


def test_check_liveness_when_heartbeat_is_stale():
    stale_timestamp = time() - _MAX_STALENESS_SECONDS - 1
    _HEARTBEAT_PATH.write_text(str(stale_timestamp))

    with pytest.raises(SystemExit, match="1"):
        check_liveness()


def test_check_liveness_when_heartbeat_is_fresh():
    _HEARTBEAT_PATH.write_text(str(time()))

    with pytest.raises(SystemExit, match="0"):
        check_liveness()
