from libs.sentry_ext import SentrySettingsMixin
from libs.settings import BaseAppSettings


class Settings(SentrySettingsMixin, BaseAppSettings):
    pass


settings = Settings()
