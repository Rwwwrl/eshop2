from libs.faststream_ext import FaststreamSettingsMixin
from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings


class Settings(SentrySettingsMixin, FaststreamSettingsMixin, BaseAppSettings):
    pass


settings = Settings()
