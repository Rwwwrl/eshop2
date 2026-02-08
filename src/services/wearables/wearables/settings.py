from libs.settings import BaseAppSettings
from libs.sqlmodel_ext.settings import PostgresSettingsMixin


class Settings(PostgresSettingsMixin, BaseAppSettings):
    pass


settings = Settings()
