from libs.faststream_ext.settings import FaststreamSettingsMixin
from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings
from libs.sqlmodel_ext.settings import PostgresSettingsMixin
from libs.taskiq_ext import TaskiqSettingsMixin


class Settings(
    SentrySettingsMixin,
    PostgresSettingsMixin,
    TaskiqSettingsMixin,
    FaststreamSettingsMixin,
    BaseAppSettings,
): ...


settings = Settings()
