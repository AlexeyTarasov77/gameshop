import argparse
from enum import StrEnum
import os
import re
import sys
import typing as t
from datetime import timedelta
from pathlib import Path

from pydantic import (
    BaseModel,
    BeforeValidator,
    EmailStr,
    Field,
    PostgresDsn,
    RedisDsn,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

PORT = t.Annotated[int, Field(gt=0, le=65535)]


def _parse_timedelta(delta: str) -> timedelta:
    """Transforms string like 1d / 1h / 60m ... etc TO timedelta object"""
    units_mapping = {"d": "days", "m": "minutes", "h": "hours"}
    match = re.match(r"(\d+\.?\d*)([a-zA-Z])", delta)
    assert match
    number, unit = match.groups()
    assert unit in units_mapping.keys(), "Unknown unit: %s" % unit
    return timedelta(**{units_mapping[unit]: float(number)})


ParsableTimedelta = t.Annotated[timedelta, BeforeValidator(_parse_timedelta)]


class ConfigMode(StrEnum):
    LOCAL = "local"
    LOCAL_TESTS = "local-tests"
    PROD = "prod"
    PROD_TESTS = "prod-tests"


class _HTTPSessions(BaseModel):
    key: str = Field(default="session_id")
    ttl: ParsableTimedelta = Field(default=timedelta(days=5))


class _PaypalychPaymentSystem(BaseModel):
    api_token: str
    shop_id: str


class _Payments(BaseModel):
    paypalych: _PaypalychPaymentSystem


class _Server(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: PORT = Field(default=8000)
    ssl_enabled: bool = Field(default=True)
    sessions: _HTTPSessions = Field(default=_HTTPSessions())

    @property
    def addr(self):
        return f"http{"s" if self.ssl_enabled else ""}://{self.host}:{self.port}"


class _SMTP(BaseModel):
    host: str
    port: PORT
    username: str
    password: str
    default_sender: EmailStr | None = None


class _Tokens(BaseModel):
    secret: str
    alg: t.Literal["HS256", "RS256", "SHA256"] = "HS256"
    auth_token_ttl: ParsableTimedelta
    activation_token_ttl: ParsableTimedelta
    password_reset_token_ttl: ParsableTimedelta
    email_verification_token_ttl: ParsableTimedelta


class _SteamAPIClient(BaseModel):
    auth_email: str
    auth_password: str


class _TelegramAPIClient(BaseModel):
    token: str
    admin_chat_id: int
    support_chat_id: int | None = None


class _ClientsConfig(BaseModel):
    steam_api: _SteamAPIClient
    tg_api: _TelegramAPIClient


class Config(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")
    api_version: str = "1.0.0"
    mode: ConfigMode
    server: _Server = Field(default=_Server())
    smtp: _SMTP
    clients: _ClientsConfig
    tokens: _Tokens
    payments: _Payments
    pg_dsn: PostgresDsn
    redis_dsn: RedisDsn

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_file_path = init_settings.init_kwargs.get("yaml_file")  # type: ignore
        if not yaml_file_path:
            raise Exception("Missing required init arg: yaml_file")
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=yaml_file_path),
        )

    @property
    def debug(self):
        return self.mode != ConfigMode.PROD


def init_config(
    parse_cli: bool = True, config_path: Path | str | None = None
) -> Config:
    cli_args = None
    if parse_cli:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--config-path",
            help="Path to the configuration file",
            dest="config_path",
        )
        parser.add_argument("--host", help="Server host", dest="host")
        parser.add_argument("-p", "--port", help="Server port", dest="port")
        cli_args, _ = parser.parse_known_args(sys.argv)
    final_cfg_path = config_path or getattr(cli_args, "config_path", None)
    if env_mode := os.environ.get("MODE"):
        final_cfg_path = final_cfg_path or (Path() / "config" / (env_mode + ".yaml"))
    if not final_cfg_path:
        raise ValueError(
            """Missing config_path. Provide it using a cli flag --config-path or a function arg.
            Also you can specify MODE env variable to find config by its value"""
        )
    if not Path(final_cfg_path).exists():
        raise ValueError("Config path doesn't exist: %s" % final_cfg_path)
    cfg = Config(yaml_file=final_cfg_path)  # type: ignore
    if cli_args:
        cfg.server.host = cli_args.host or cfg.server.host
        cfg.server.port = cli_args.port or cfg.server.port
    return cfg
