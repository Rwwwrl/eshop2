from unittest.mock import patch

from libs.common.enums import EnvironmentEnum
from libs.sentry_ext import SentrySettingsMixin
from libs.sentry_ext.utils import setup_sentry

_DSN = "https://key@sentry.io/1"


def test_setup_sentry_when_dsn_is_none() -> None:
    settings = SentrySettingsMixin(environment=EnvironmentEnum.DEV)

    with patch("libs.sentry_ext.utils.sentry_sdk.init") as mock_init:
        setup_sentry(settings=settings, release="1.0.0")

    mock_init.assert_not_called()


def test_setup_sentry_when_dsn_is_set() -> None:
    settings = SentrySettingsMixin(
        environment=EnvironmentEnum.TEST,
        sentry_dsn=_DSN,
        sentry_send_pii=False,
        sentry_traces_sample_rate=0.5,
    )

    with patch("libs.sentry_ext.utils.sentry_sdk.init") as mock_init:
        setup_sentry(settings=settings, release="1.0.0")

    mock_init.assert_called_once_with(
        dsn=_DSN,
        environment="test",
        release="1.0.0",
        traces_sample_rate=0.5,
        send_default_pii=False,
    )
