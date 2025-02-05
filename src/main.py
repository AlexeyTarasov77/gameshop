import asyncio
from logging import Logger

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import Config
from core.exception_mappers import HttpExceptionsMapper
from core.ioc import Resolve
from core.router import router
from core.services.exceptions import MappedServiceError
from core.utils import get_upload_dir
from gateways.db.main import SqlAlchemyDatabase


def app_factory() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(MappedServiceError, HttpExceptionsMapper().handle)

    @app.get("/ping")
    async def ping() -> dict[str, str | list[str]]:
        return {
            "status": "available",
            "available_routes": [route.path for route in app.routes],
        }

    @app.get("/%s/{filename}" % Resolve(Config).server.media_serve_url)
    async def media_serve(filename: str):
        if not (get_upload_dir() / filename).exists():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"File {filename} does not exist"
            )
        return FileResponse(get_upload_dir() / filename)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


async def main() -> None:
    cfg = Resolve(Config)
    logger = Resolve(Logger)
    db = Resolve(SqlAlchemyDatabase)
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
