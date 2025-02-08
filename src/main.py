import asyncio
from logging import Logger

from core.exception_mappers import HTTPExceptionsMapper
from core.ioc import Resolve
from config import Config
import uvicorn
from core.router import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gateways.db.main import SqlAlchemyDatabase


def app_factory() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    HTTPExceptionsMapper(app).setup_handlers()

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
        host="0.0.0.0",  # deliberately not using cfg.server.host because binded host should always by local to current host
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
