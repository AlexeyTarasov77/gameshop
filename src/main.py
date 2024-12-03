import argparse
import pathlib

import punq
import uvicorn
from core.ioc import init_container
from core.router import router
from fastapi import FastAPI

from config import Config

DEFAULT_CONFIG_PATH = (pathlib.Path() / "config" / "local.yaml").resolve()

container: punq.Container


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-path",
        default=DEFAULT_CONFIG_PATH,
        help="Path to the configuration file",
        dest="config_path",
    )
    parser.add_argument("--host", help="Server host", dest="host")
    parser.add_argument("-p", "--port", help="Server port", dest="port")
    args = parser.parse_args()
    return args


def main() -> None:
    app = FastAPI()
    app.include_router(router)
    args = parse_cli()

    container = init_container(args.config_path)
    app.state.ioc_container = container

    config = container.resolve(Config)
    s = config.server
    s.port = args.port or s.port
    s.host = args.host or s.host
    uvicorn.run(
        "main:app",
        host=s.host,
        port=int(s.port),
        reload=(config.mode == "local"),
    )


if __name__ == "__main__":
    main()
