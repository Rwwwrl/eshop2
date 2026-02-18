from datetime import datetime, timezone

from libs.datetime_ext.utils import utc_now


def test_utc_now_when_called() -> None:
    result = utc_now()

    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc
