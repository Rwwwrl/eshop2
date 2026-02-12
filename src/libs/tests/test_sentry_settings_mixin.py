import pytest
from libs.common.enums import EnvironmentEnum
from libs.sentry_ext import SentrySettingsMixin
from pydantic import ValidationError

_DSN = "https://key@sentry.io/1"
_STAND_ENVS = [EnvironmentEnum.TEST, EnvironmentEnum.PROD]
_NON_STAND_ENVS = [EnvironmentEnum.DEV, EnvironmentEnum.CICD]


class _TestSettings(SentrySettingsMixin):
    environment: EnvironmentEnum


@pytest.mark.parametrize("env", _STAND_ENVS)
def test_validate_sentry_settings_when_stand_env_and_dsn_is_none(env: EnvironmentEnum) -> None:
    with pytest.raises(ValidationError, match="sentry_dsn is required for stand environments"):
        _TestSettings(environment=env, sentry_dsn=None, sentry_send_pii=None, sentry_traces_sample_rate=None)


@pytest.mark.parametrize("env", _STAND_ENVS)
def test_validate_sentry_settings_when_stand_env_and_send_pii_is_none(env: EnvironmentEnum) -> None:
    with pytest.raises(ValidationError, match="sentry_send_pii is required for stand environments"):
        _TestSettings(environment=env, sentry_dsn=_DSN, sentry_send_pii=None, sentry_traces_sample_rate=1.0)


@pytest.mark.parametrize("env", _STAND_ENVS)
def test_validate_sentry_settings_when_stand_env_and_traces_sample_rate_is_none(env: EnvironmentEnum) -> None:
    with pytest.raises(ValidationError, match="sentry_traces_sample_rate is required for stand environments"):
        _TestSettings(environment=env, sentry_dsn=_DSN, sentry_send_pii=False, sentry_traces_sample_rate=None)


@pytest.mark.parametrize("env", _STAND_ENVS)
def test_validate_sentry_settings_when_stand_env_and_all_fields_set(env: EnvironmentEnum) -> None:
    settings = _TestSettings(environment=env, sentry_dsn=_DSN, sentry_send_pii=False, sentry_traces_sample_rate=0.5)
    assert settings.sentry_dsn == _DSN
    assert settings.sentry_send_pii is False
    assert settings.sentry_traces_sample_rate == 0.5


@pytest.mark.parametrize("env", _NON_STAND_ENVS)
def test_validate_sentry_settings_when_non_stand_env_and_dsn_is_set(env: EnvironmentEnum) -> None:
    with pytest.raises(ValidationError, match="sentry_dsn must not be set for non-stand environments"):
        _TestSettings(environment=env, sentry_dsn=_DSN, sentry_send_pii=None, sentry_traces_sample_rate=None)


@pytest.mark.parametrize("env", _NON_STAND_ENVS)
def test_validate_sentry_settings_when_non_stand_env_and_send_pii_is_set(env: EnvironmentEnum) -> None:
    with pytest.raises(ValidationError, match="sentry_send_pii must not be set for non-stand environments"):
        _TestSettings(environment=env, sentry_dsn=None, sentry_send_pii=False, sentry_traces_sample_rate=None)


@pytest.mark.parametrize("env", _NON_STAND_ENVS)
def test_validate_sentry_settings_when_non_stand_env_and_traces_sample_rate_is_set(env: EnvironmentEnum) -> None:
    with pytest.raises(ValidationError, match="sentry_traces_sample_rate must not be set for non-stand environments"):
        _TestSettings(environment=env, sentry_dsn=None, sentry_send_pii=None, sentry_traces_sample_rate=0.5)


@pytest.mark.parametrize("env", _NON_STAND_ENVS)
def test_validate_sentry_settings_when_non_stand_env_and_all_fields_none(env: EnvironmentEnum) -> None:
    settings = _TestSettings(environment=env, sentry_dsn=None, sentry_send_pii=None, sentry_traces_sample_rate=None)
    assert settings.sentry_dsn is None
    assert settings.sentry_send_pii is None
    assert settings.sentry_traces_sample_rate is None


def test_validate_sentry_settings_when_prod_and_send_pii_is_true() -> None:
    with pytest.raises(ValidationError, match="sentry_send_pii must be False in production"):
        _TestSettings(
            environment=EnvironmentEnum.PROD, sentry_dsn=_DSN, sentry_send_pii=True, sentry_traces_sample_rate=0.1
        )


def test_validate_sentry_settings_when_test_env_and_send_pii_is_true() -> None:
    settings = _TestSettings(
        environment=EnvironmentEnum.TEST, sentry_dsn=_DSN, sentry_send_pii=True, sentry_traces_sample_rate=1.0
    )
    assert settings.sentry_send_pii is True


@pytest.mark.parametrize("rate", [-0.1, 1.5])
def test_validate_sentry_settings_when_traces_sample_rate_out_of_range(rate: float) -> None:
    with pytest.raises(ValidationError):
        _TestSettings(
            environment=EnvironmentEnum.TEST, sentry_dsn=_DSN, sentry_send_pii=False, sentry_traces_sample_rate=rate
        )
