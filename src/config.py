import typing as t

from pydantic import BaseModel, Field, IPvAnyAddress, PostgresDsn
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

# TODO: Разобраться, можно ли указать игнорировать unrecognized cli args


class _Server(BaseModel):
    host: IPvAnyAddress = Field(default="0.0.0.0")
    port: int = Field(default="8000", gt=0, lte=65535)


class Config(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")

    mode: t.Literal["local", "prod"]
    server: _Server = Field(default_factory=_Server)
    storage_dsn: PostgresDsn

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_file_path = init_settings.init_kwargs.get("yaml_file")
        if not yaml_file_path:
            raise Exception("Missing required init arg: yaml_file")
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file_path),
        )
