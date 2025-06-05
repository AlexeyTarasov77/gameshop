import asyncio
from collections.abc import Callable
from functools import wraps
from hashlib import md5
from core.logging import AbstractLogger
from fastapi import HTTPException, Request, Response, status
from fastapi.dependencies.utils import get_typed_signature
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from core.ioc import Resolve
from gateways.db import RedisClient
import json
import inspect


def _uncacheable(request: Request) -> bool:
    return request.method != "GET" or request.headers.get("Cache-Control") == "no-store"


def _get_etag_for_resp(resp: str):
    return f"W/{hash(resp)}"


def _get_cache_headers(max_age: int, etag: str) -> dict[str, str]:
    return {"Cache-Control": f"max-age={max_age}", "Etag": etag}


def _locate_param(
    sig: inspect.Signature, dep: inspect.Parameter, to_inject: list[inspect.Parameter]
) -> inspect.Parameter:
    """Locate an existing parameter in the decorated endpoint
    If not found, returns the injectable parameter, and adds it to the to_inject list."""
    param = next(
        (p for p in sig.parameters.values() if p.annotation is dep.annotation), None
    )
    if param is None:
        to_inject.append(dep)
        param = dep
    return param


def cache(ttl: int = 300):
    injected_request = inspect.Parameter(
        name="__cache_request",
        annotation=Request,
        kind=inspect.Parameter.KEYWORD_ONLY,
    )
    injected_response = inspect.Parameter(
        name="__cache_response",
        annotation=Response,
        kind=inspect.Parameter.KEYWORD_ONLY,
    )

    def decorator[T](func: Callable[..., T]):
        ns = f"{func.__module__}.{func.__name__}"
        sig = get_typed_signature(func)
        to_inject: list[inspect.Parameter] = []
        request_param = _locate_param(sig, injected_request, to_inject)
        response_param = _locate_param(sig, injected_response, to_inject)

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async def compute_resp() -> T:
                return (
                    await func(*args, **kwargs)
                    if inspect.iscoroutinefunction(func)
                    else await run_in_threadpool(func, *args, **kwargs)
                )

            req: Request = kwargs.pop(request_param.name)
            resp: Response = kwargs.pop(response_param.name)
            if _uncacheable(req):
                return await compute_resp()

            etag = req.headers.get("If-None-Match")
            params = repr(args) + repr(kwargs)
            cache_key = f"{ns}:{md5(params.encode()).hexdigest()}"
            logger = Resolve(AbstractLogger)
            cache = Resolve(RedisClient)
            cached_resp = None
            try:
                cached_resp, ttl_left = await asyncio.gather(
                    cache.get(cache_key), cache.ttl(cache_key)
                )
            except Exception as e:
                logger.error("Failed to retrieve response from cache", err_msg=e)
            else:
                if cached_resp and req.headers.get("Cache-Control") != "no-cache":
                    logger.debug("Retrieved response from cache")
                    resp_etag = _get_etag_for_resp(cached_resp)
                    if etag is not None and etag == resp_etag:
                        raise HTTPException(status.HTTP_304_NOT_MODIFIED)
                    resp.headers.update(_get_cache_headers(ttl_left, resp_etag))
                    return json.loads(cached_resp)
            computed_response = await compute_resp()
            response_dump = (
                computed_response.model_dump_json()
                if isinstance(computed_response, BaseModel)
                else json.dumps(computed_response)
            )
            await cache.set(cache_key, response_dump, ttl)
            logger.debug("Computed and cached response")
            resp_etag = _get_etag_for_resp(response_dump)
            if etag is not None and etag == resp_etag:
                raise HTTPException(status.HTTP_304_NOT_MODIFIED)
            resp.headers.update(_get_cache_headers(ttl, resp_etag))
            return computed_response

        if to_inject:
            wrapper.__signature__ = sig.replace(  # type: ignore
                parameters=[*sig.parameters.values(), *to_inject]
            )
        return wrapper

    return decorator
