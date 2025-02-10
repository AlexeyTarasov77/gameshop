from fastapi import FastAPI, Request, Response
from secrets import token_urlsafe
from starlette.middleware.base import BaseHTTPMiddleware, DispatchFunction


class Middlewares:
    def __init__(self, app: FastAPI):
        self._app = app

    async def check_session(self, req: Request, call_next) -> Response:
        if not req.cookies.get("session_id"):
            req.cookies["session_id"] = token_urlsafe(16)
        return await call_next(req)

    def setup(self):
        def add_middleware(func: DispatchFunction):
            self._app.add_middleware(BaseHTTPMiddleware, dispatch=func)

        add_middleware(self.check_session)
