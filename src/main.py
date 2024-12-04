
import uvicorn
from core.ioc import get_container
from core.router import router
from fastapi import FastAPI

from config import Config


def app_factory() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def main() -> None:
    cfg = get_container().resolve(Config)
    uvicorn.run(
        app="main:app_factory",
        factory=True,
        host=cfg.server.host,
        port=int(cfg.server.port),
        reload=(cfg.mode == "local"),
    )


if __name__ == "__main__":
    main()
