from datetime import datetime, timezone

from libs.datetime_ext.utils import utc_now


def test_utc_now_returns_utc_datetime():
    result = utc_now()

    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc
