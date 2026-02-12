from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings

from libs.common.enums import EnvironmentEnum
from libs.settings import is_stand_env


class SentrySettingsMixin(BaseSettings):
    environment: EnvironmentEnum
    sentry_dsn: str | None = None
    sentry_send_pii: bool = False

    @model_validator(mode="after")
    def _validate_sentry_settings(self) -> Self:
        if is_stand_env(environment=self.environment) and self.sentry_dsn is None:
            raise ValueError("sentry_dsn is required for stand environments")

        if not is_stand_env(environment=self.environment) and self.sentry_dsn is not None:
            raise ValueError("sentry_dsn must not be set for non-stand environments")

        if self.environment == EnvironmentEnum.PROD and self.sentry_send_pii is True:
            raise ValueError("sentry_send_pii must be False in production")

        return self
