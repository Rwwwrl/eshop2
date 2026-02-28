from libs.faststream_ext.settings import FaststreamSettingsMixin
from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings
from libs.sqlmodel_ext.settings import PostgresSettingsMixin


class Settings(
    SentrySettingsMixin,
    PostgresSettingsMixin,
    FaststreamSettingsMixin,
    BaseAppSettings,
): ...


settings = Settings()
