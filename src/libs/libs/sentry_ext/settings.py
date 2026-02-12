from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings

from libs.common.enums import EnvironmentEnum
from libs.settings import is_stand_env


class SentrySettingsMixin(BaseSettings):
    environment: EnvironmentEnum
    sentry_dsn: str | None = None

    @model_validator(mode="after")
    def _validate_sentry_dsn(self) -> Self:
        if is_stand_env(environment=self.environment) and self.sentry_dsn is None:
            raise ValueError("sentry_dsn is required for stand environments")

        if not is_stand_env(environment=self.environment) and self.sentry_dsn is not None:
            raise ValueError("sentry_dsn must not be set for non-stand environments")

        return self
