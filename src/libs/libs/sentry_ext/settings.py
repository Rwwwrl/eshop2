from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from libs.common.enums import EnvironmentEnum
from libs.settings import is_stand_env


class SentrySettingsMixin(BaseSettings):
    environment: EnvironmentEnum
    sentry_dsn: str | None
    sentry_send_pii: bool | None
    sentry_traces_sample_rate: float | None = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _validate_sentry_settings(self) -> Self:
        if is_stand_env(environment=self.environment):
            if self.sentry_dsn is None:
                raise ValueError("sentry_dsn is required for stand environments")
            if self.sentry_send_pii is None:
                raise ValueError("sentry_send_pii is required for stand environments")
            if self.sentry_traces_sample_rate is None:
                raise ValueError("sentry_traces_sample_rate is required for stand environments")
            if self.environment == EnvironmentEnum.PROD and self.sentry_send_pii is True:
                raise ValueError("sentry_send_pii must be False in production")
        else:
            if self.sentry_dsn is not None:
                raise ValueError("sentry_dsn must not be set for non-stand environments")
            if self.sentry_send_pii is not None:
                raise ValueError("sentry_send_pii must not be set for non-stand environments")
            if self.sentry_traces_sample_rate is not None:
                raise ValueError("sentry_traces_sample_rate must not be set for non-stand environments")

        return self
