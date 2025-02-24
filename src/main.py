import asyncio
from logging import Logger

from redis.asyncio import Redis

from sessions.sessions import SessionCreatorI, session_middleware
from core.exception_mappers import HTTPExceptionsMapper
from core.ioc import Resolve
from config import Config
import uvicorn
from core.router import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gateways.db.main import SqlAlchemyDatabase


def app_factory() -> FastAPI:
    cfg = Resolve(Config)
    app = FastAPI(version=cfg.api_version)
    app.include_router(router)
    HTTPExceptionsMapper(app).setup_handlers()
    app.middleware("http")(
        session_middleware(
            max_age=cfg.server.sessions.ttl,
            session_creator=Resolve(SessionCreatorI),
        )
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            "https://127.0.0.1:3000",
            "https://gamebazaar.ru",
            "http://gamebazaar.ru",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


async def main() -> None:
    cfg = Resolve(Config)
    logger = Resolve(Logger)
    db = Resolve(SqlAlchemyDatabase)
    redis_client = Resolve(Redis)
    logger.info("Pinging database...")
    done_tasks, _ = await asyncio.wait(
        [asyncio.create_task(redis_client.ping()), asyncio.create_task(db.ping())],
        timeout=3,
    )
    [await task for task in done_tasks]
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
