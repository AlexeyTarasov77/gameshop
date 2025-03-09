import asyncio
from logging import Logger
from redis.asyncio import Redis

from sessions.sessions import SessionCreatorI, session_middleware
from core.exception_mappers import HTTPExceptionsMapper
from core.ioc import Resolve, cleanup_list
from config import Config
import uvicorn
from core.router import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gateways.db.main import SqlAlchemyDatabase
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = Resolve(Logger)
    db = Resolve(SqlAlchemyDatabase)
    r = Resolve(Redis)
    logger.info("Pinging database...")
    done_tasks, _ = await asyncio.wait(
        [asyncio.create_task(r.ping()), asyncio.create_task(db.ping())],
        timeout=3,
    )
    [await task for task in done_tasks]
    logger.info("Database is ready!")
    yield
    print("cleaning up", cleanup_list)
    await asyncio.gather(*[obj.aclose() for obj in cleanup_list])


def app_factory() -> FastAPI:
    cfg = Resolve(Config)
    app = FastAPI(version=cfg.api_version, lifespan=lifespan)
    app.include_router(router)
    Resolve(HTTPExceptionsMapper, app=app).setup_handlers()
    app.middleware("http")(
        session_middleware(
            max_age=cfg.server.sessions.ttl,
            session_creator=Resolve(SessionCreatorI),
        )
    )
    allow_origins = [
        "https://gamebazaar.ru",
        "http://gamebazaar.ru",
        "https://www.gamebazaar.ru",
        "http://www.gamebazaar.ru",
    ]
    if cfg.debug:
        allow_origins.extend(
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


async def main() -> None:
    cfg = Resolve(Config)
    logger = Resolve(Logger)
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
