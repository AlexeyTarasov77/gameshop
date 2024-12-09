import argparse
import pathlib
import re
import typing as t
from datetime import timedelta

from pydantic import (
    BaseModel,
    BeforeValidator,
    EmailStr,
    Field,
    IPvAnyAddress,
    PostgresDsn,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

PORT = t.Annotated[int, Field(default="8000", gt=0, lte=65535)]


def _parse_timedelta(delta: str) -> timedelta:
    """Transforms string like 1d / 1h / 60m ... etc TO timedelta object"""
    units_mapping = {"d": "days", "m": "minutes", "h": "hours"}
    match = re.match(r"(\d+\.?\d*)([a-zA-Z])", delta)
    number, unit = match.groups()
    assert unit in units_mapping.keys(), "Unknown unit: %s" % unit
    return timedelta(**{units_mapping[unit]: float(number)})


ParsableTimedelta = t.Annotated[timedelta, BeforeValidator(_parse_timedelta)]


class _Server(BaseModel):
    host: IPvAnyAddress = Field(default="0.0.0.0")
    port: PORT


class _SMTP(BaseModel):
    host: str
    port: PORT
    username: str
    password: str
    default_sender: EmailStr | None = None


class _JWT(BaseModel):
    secret: str
    alg: t.Literal["HS256", "RS256", "SHA256"] = "HS256"
    activation_token_ttl: ParsableTimedelta


class Config(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")

    mode: t.Literal["local", "prod"]
    server: _Server = Field(default_factory=_Server)
    smtp: _SMTP
    jwt: _JWT
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


def init_config(parse_cli: bool = True, config_path: pathlib.Path | str | None = None) -> Config:
    if parse_cli:
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
    else:
        cfg = Config(yaml_file=config_path or (pathlib.Path() / "config" / "local.yaml").resolve())
    return cfg
