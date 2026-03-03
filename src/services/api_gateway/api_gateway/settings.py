from pathlib import Path
from typing import ClassVar

from libs.faststream_ext.settings import FaststreamSettingsMixin
from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(SentrySettingsMixin, FaststreamSettingsMixin, BaseAppSettings):
    env_dev_yaml: ClassVar[Path] = BASE_DIR / "env.dev.yaml"

    hello_world_grpc_url: str


settings = Settings()
