import asyncio
import sentry_sdk
from fastapi.encoders import jsonable_encoder
from functools import partial
from logging import Logger

from fastapi.openapi.models import HTTPBearer
from core.tasks import BackgroundJobs
from gateways.db import RedisClient, SqlAlchemyClient
from shopping.sessions import SessionCreatorI, session_middleware
from core.exception_mappers import HTTPExceptionsMapper
from core.ioc import Resolve, cleanup_list
from config import Config
import uvicorn
from core.api.router import router
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


def custom_openapi(app: FastAPI, version: str):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Gameshop API",
        version=version,
        routes=app.routes,
    )
    bearer_auth = jsonable_encoder(
        HTTPBearer(
            bearerFormat="JWT",
            description="Enter your JWT token obtained from sign in endpoint",
        )
    )

    openapi_schema["components"]["securitySchemes"] = {"BearerAuth": bearer_auth}
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [
                {"BearerAuth": bearer_auth}
            ]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


async def ping_gateways():
    logger = Resolve(Logger)
    db = Resolve(SqlAlchemyClient)
    redis_client = Resolve(RedisClient)
    logger.info("Pinging database...")
    done_tasks, _ = await asyncio.wait(
        [asyncio.create_task(redis_client.ping()), asyncio.create_task(db.ping())],
        timeout=3,
    )
    [await task for task in done_tasks]
    await redis_client.setup()
    logger.info("Gateways are ready to accept connections!")


async def close_connections():
    await asyncio.gather(*[obj.aclose() for obj in cleanup_list])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = Resolve(Logger)
    bg_jobs = Resolve(BackgroundJobs)
    await ping_gateways()
    bg_jobs.start_all()
    logger.info("Background jobs succesfully launched!")
    try:
        yield
    finally:
        await close_connections()


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
    app.openapi = partial(custom_openapi, app, cfg.api_version)
    if cfg.debug:
        allow_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    else:
        allow_origins = [
            prefix + cfg.server.host
            for prefix in ["https://", "http://", "https://www.", "http://www."]
        ]

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
    if not cfg.debug:
        sentry_cfg = cfg.clients.sentry
        assert sentry_cfg
        logger.info("Initializing sentry")
        sentry_sdk.init(
            dsn=str(sentry_cfg.dsn),
            environment=cfg.mode,
            # Add data like request headers and IP for users,
            # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
            send_default_pii=True,
        )
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
