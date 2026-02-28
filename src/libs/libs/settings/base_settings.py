from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource

from libs.common.enums import EnvironmentEnum
from libs.logging.settings import LoggingSettingsMixin


class BaseAppSettings(LoggingSettingsMixin, BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    environment: EnvironmentEnum

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # NOTE @sosov: YAML source is conditional on file existence. In production, config is injected
        # via K8s env vars (ConfigMap + Secret), so no env.yaml exists. In local dev, env.dev.yaml provides values.
        sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
        if Path("env.dev.yaml").exists():
            sources.append(YamlConfigSettingsSource(settings_cls=settings_cls, yaml_file="env.dev.yaml"))

        return tuple(sources)
