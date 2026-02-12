import pytest
from libs.common.enums import EnvironmentEnum
from libs.sentry_ext import SentrySettingsMixin
from pydantic import ValidationError


class _TestSettings(SentrySettingsMixin):
    environment: EnvironmentEnum
    sentry_dsn: str | None = None


def test_stand_env_requires_sentry_dsn() -> None:
    with pytest.raises(ValidationError, match="sentry_dsn is required for stand environments"):
        _TestSettings(environment=EnvironmentEnum.TEST)


def test_stand_env_accepts_sentry_dsn() -> None:
    settings = _TestSettings(environment=EnvironmentEnum.TEST, sentry_dsn="https://key@sentry.io/1")
    assert settings.sentry_dsn == "https://key@sentry.io/1"


def test_non_stand_env_rejects_sentry_dsn() -> None:
    with pytest.raises(ValidationError, match="sentry_dsn must not be set for non-stand environments"):
        _TestSettings(environment=EnvironmentEnum.DEV, sentry_dsn="https://key@sentry.io/1")


def test_non_stand_env_accepts_no_sentry_dsn() -> None:
    settings = _TestSettings(environment=EnvironmentEnum.DEV)
    assert settings.sentry_dsn is None


def test_cicd_env_rejects_sentry_dsn() -> None:
    with pytest.raises(ValidationError, match="sentry_dsn must not be set for non-stand environments"):
        _TestSettings(environment=EnvironmentEnum.CICD, sentry_dsn="https://key@sentry.io/1")


def test_cicd_env_accepts_no_sentry_dsn() -> None:
    settings = _TestSettings(environment=EnvironmentEnum.CICD)
    assert settings.sentry_dsn is None


def test_prod_env_requires_sentry_dsn() -> None:
    with pytest.raises(ValidationError, match="sentry_dsn is required for stand environments"):
        _TestSettings(environment=EnvironmentEnum.PROD)


def test_prod_env_accepts_sentry_dsn() -> None:
    settings = _TestSettings(environment=EnvironmentEnum.PROD, sentry_dsn="https://key@sentry.io/1")
    assert settings.sentry_dsn == "https://key@sentry.io/1"


def test_prod_env_rejects_send_pii_true() -> None:
    with pytest.raises(ValidationError, match="sentry_send_pii must be False in production"):
        _TestSettings(environment=EnvironmentEnum.PROD, sentry_dsn="https://key@sentry.io/1", sentry_send_pii=True)


def test_prod_env_accepts_send_pii_false() -> None:
    settings = _TestSettings(
        environment=EnvironmentEnum.PROD, sentry_dsn="https://key@sentry.io/1", sentry_send_pii=False
    )
    assert settings.sentry_send_pii is False


def test_test_env_accepts_send_pii_true() -> None:
    settings = _TestSettings(
        environment=EnvironmentEnum.TEST, sentry_dsn="https://key@sentry.io/1", sentry_send_pii=True
    )
    assert settings.sentry_send_pii is True
