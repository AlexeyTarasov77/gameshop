import argparse
import pathlib

import punq
import uvicorn
from core.router import router
from fastapi import FastAPI

from config import Config

DEFAULT_CONFIG_PATH = (pathlib.Path() / "config" / "local.yaml").resolve()

container = punq.Container()

app = FastAPI()


def main() -> None:
    app.include_router(router)
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
    config = Config(yaml_file=args.config_path)
    config.server.port = args.port or config.server.port
    config.server.host = args.host or config.server.host
    container.register(Config, instance=config)
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=int(config.server.port),
        reload=(config.mode == "local"),
    )


if __name__ == "__main__":
    main()
