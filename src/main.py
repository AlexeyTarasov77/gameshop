import asyncio
import signal
from logging import Logger
from typing import cast

import uvicorn
from core.ioc import get_container
from core.router import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from gateways.db.main import SqlAlchemyDatabase


def app_factory() -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    @app.get("/ping")
    async def ping() -> dict[str, str | list[str]]:
        return {
            "status": "available",
            "available_routes": [route.path for route in app.routes],
        }

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


async def main() -> None:
    container = get_container()
    cfg = cast(Config, container.resolve(Config))
    logger = cast(Logger, container.resolve(Logger))
    db = cast(SqlAlchemyDatabase, container.resolve(SqlAlchemyDatabase))
    logger.info("Pinging database...")
    await asyncio.wait_for(db.ping(), 3)
    logger.info("Database is ready!")
    logger.info(f"Running server in {cfg.mode} mode")
    uvicorn_conf = uvicorn.Config(
        app="main:app_factory",
        factory=True,
        host=str(cfg.server.host),
        port=int(cfg.server.port),
        reload=cfg.debug,
    )
    server = uvicorn.Server(uvicorn_conf)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        ...
