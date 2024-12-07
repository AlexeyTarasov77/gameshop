import argparse
import typing as t

from pydantic import BaseModel, Field, IPvAnyAddress, PostgresDsn
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


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


def init_config() -> Config:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-path",
        help="Path to the configuration file",
        dest="config_path",
    )
    parser.add_argument("--host", help="Server host", dest="host")
    parser.add_argument("-p", "--port", help="Server port", dest="port")
    args = parser.parse_args()
    cfg = Config(yaml_file=args.config_path)
    cfg.server.host = args.host or cfg.server.host
    cfg.server.port = args.port or cfg.server.port
    return cfg
