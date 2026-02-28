from pathlib import Path
from typing import ClassVar

from libs.faststream_ext.settings import FaststreamSettingsMixin
from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings
from libs.sqlmodel_ext.settings import PostgresSettingsMixin
from libs.taskiq_ext import TaskiqSettingsMixin

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(
    SentrySettingsMixin,
    PostgresSettingsMixin,
    TaskiqSettingsMixin,
    FaststreamSettingsMixin,
    BaseAppSettings,
):
    env_dev_yaml: ClassVar[Path] = BASE_DIR / "env.dev.yaml"


settings = Settings()
