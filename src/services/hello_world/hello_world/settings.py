from pathlib import Path

from libs.faststream_ext.settings import FaststreamSettingsMixin
from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings
from libs.sqlmodel_ext.settings import PostgresSettingsMixin
from pydantic_settings import SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(
    SentrySettingsMixin,
    PostgresSettingsMixin,
    FaststreamSettingsMixin,
    BaseAppSettings,
):
    model_config = SettingsConfigDict(
        yaml_file=str(_BASE_DIR / "env.yaml"),
        extra="ignore",
    )


settings = Settings()
