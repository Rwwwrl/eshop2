from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource

from libs.common.enums import EnvironmentEnum
from libs.logging.settings import LoggingSettingsMixin


class BaseAppSettings(LoggingSettingsMixin, BaseSettings):
    model_config = SettingsConfigDict(
        yaml_file="env.yaml",
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
        # via K8s env vars (ConfigMap + Secret), so no env.yaml exists. In local dev, env.yaml provides values.
        sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
        yaml_file = cls.model_config.get("yaml_file")
        if yaml_file and Path(yaml_file).exists():
            sources.append(YamlConfigSettingsSource(settings_cls=settings_cls))

        return tuple(sources)
