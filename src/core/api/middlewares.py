import time

from starlette.routing import Match
from datetime import timedelta
from fastapi import Request, Response, status
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    DispatchFunction,
    RequestResponseEndpoint,
)
from starlette.types import ASGIApp
from core.api.metrics import (
    INFO,
    REQUESTS,
    REQUESTS_IN_PROGRESS,
    REQUESTS_PROCESSING_TIME,
    RESPONSES,
    EXCEPTIONS,
)
from shopping.sessions import SessionCreatorI


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, app_name: str = "fastapi-app") -> None:
        super().__init__(app)
        self.app_name = app_name
        INFO.labels(app_name=self.app_name).inc()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        method = request.method
        path, is_handled_path = self.get_path(request)

        if not is_handled_path:
            return await call_next(request)

        REQUESTS_IN_PROGRESS.labels(
            method=method, path=path, app_name=self.app_name
        ).inc()
        REQUESTS.labels(method=method, path=path, app_name=self.app_name).inc()
        before_time = time.perf_counter()
        status_code: int | None = None
        try:
            response = await call_next(request)
        except BaseException as e:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            EXCEPTIONS.labels(
                method=method,
                path=path,
                exception_type=type(e).__name__,
                app_name=self.app_name,
            ).inc()
            raise e from None
        else:
            status_code = response.status_code
            after_time = time.perf_counter()

            REQUESTS_PROCESSING_TIME.labels(
                method=method, path=path, app_name=self.app_name
            ).observe(after_time - before_time)
        finally:
            RESPONSES.labels(
                method=method,
                path=path,
                status_code=status_code,
                app_name=self.app_name,
            ).inc()  # type: ignore
            REQUESTS_IN_PROGRESS.labels(
                method=method, path=path, app_name=self.app_name
            ).dec()

        return response

    @staticmethod
    def get_path(request: Request) -> tuple[str, bool]:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path, True

        return request.url.path, False


def create_session_middleware(
    session_creator: SessionCreatorI,
    max_age: int | timedelta,
    session_key_name: str = "session_id",
) -> DispatchFunction:
    async def middleware(req: Request, call_next: RequestResponseEndpoint) -> Response:
        nonlocal max_age
        session_key: str | None = req.cookies.get(session_key_name)
        if session_key is None:
            session_key = await session_creator.create({"cart": {}, "wishlist": []})
        req.scope[session_key_name] = session_key
        resp = await call_next(req)
        if isinstance(max_age, timedelta):
            max_age = int(max_age.total_seconds())
        resp.set_cookie(
            session_key_name,
            session_key,
            max_age,
            httponly=True,
            samesite="none",
            secure=True,
        )
        return resp

    return middleware
