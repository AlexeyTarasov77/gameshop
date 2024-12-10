from typing import cast

import uvicorn
from core.ioc import get_container
from core.router import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config


def app_factory() -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    @app.get("/ping")
    async def ping() -> dict[str, str | list[str]]:
        return {"status": "available", "available_routes": [route.path for route in app.routes]}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def main() -> None:
    cfg = cast(Config, get_container().resolve(Config))
    print(f"Running in {cfg.mode} mode")
    uvicorn.run(
        app="main:app_factory",
        factory=True,
        host=cfg.server.host,
        port=int(cfg.server.port),
        reload=cfg.debug,
    )


if __name__ == "__main__":
    main()
