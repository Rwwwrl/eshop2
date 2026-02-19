import pytest
from libs.common.enums import EnvironmentEnum
from libs.settings import is_data_sensitive_env, is_stand_env


@pytest.mark.parametrize("env", [EnvironmentEnum.TEST, EnvironmentEnum.PROD])
def test_is_stand_env_returns_true_for_stand_environments(env: EnvironmentEnum) -> None:
    assert is_stand_env(environment=env) is True


@pytest.mark.parametrize("env", [EnvironmentEnum.DEV, EnvironmentEnum.CICD])
def test_is_stand_env_returns_false_for_non_stand_environments(env: EnvironmentEnum) -> None:
    assert is_stand_env(environment=env) is False


def test_is_data_sensitive_env_returns_true_for_prod() -> None:
    assert is_data_sensitive_env(environment=EnvironmentEnum.PROD) is True


@pytest.mark.parametrize("env", [EnvironmentEnum.DEV, EnvironmentEnum.TEST, EnvironmentEnum.CICD])
def test_is_data_sensitive_env_returns_false_for_non_prod(env: EnvironmentEnum) -> None:
    assert is_data_sensitive_env(environment=env) is False
