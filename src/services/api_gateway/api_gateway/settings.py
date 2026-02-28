from libs.faststream_ext.settings import FaststreamSettingsMixin
from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings


class Settings(SentrySettingsMixin, FaststreamSettingsMixin, BaseAppSettings): ...


settings = Settings()
