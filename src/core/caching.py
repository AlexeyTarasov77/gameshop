from collections.abc import Callable
from functools import wraps
from hashlib import md5
from logging import Logger
from fastapi import Request
from pydantic import BaseModel
from fastapi.concurrency import run_in_threadpool
from core.ioc import Resolve
from gateways.db import RedisClient
import json
import inspect


def _uncacheable(request: Request) -> bool:
    return request.method != "GET" or request.headers.get("Cache-Control") == "no-store"


def cache(ttl: int = 300):
    def decorator[T](func: Callable[..., T]):
        @wraps(func)
        async def wrapper(req: Request, *args, **kwargs) -> T:
            async def compute_resp() -> T:
                return (
                    await func(*args, **kwargs)
                    if inspect.iscoroutinefunction(func)
                    else await run_in_threadpool(func, *args, **kwargs)
                )

            if _uncacheable(req):
                return await compute_resp()

            params = repr(args) + repr(kwargs)
            print("PARAMS", params)
            cache_key = f"{func.__name__}:{md5(params.encode()).hexdigest()}"
            logger = Resolve(Logger)
            cache = Resolve(RedisClient)
            cached_resp = None
            try:
                cached_resp = await cache.get(cache_key)
            except Exception as e:
                logger.error("Failed to retrieve response from cache. Error: %s", e)
            if cached_resp:
                logger.debug("Retrieved response from cache")
                return json.loads(cached_resp)
            resp = await compute_resp()
            dumped_resp = (
                resp.model_dump_json()
                if isinstance(resp, BaseModel)
                else json.dumps(resp)
            )
            await cache.set(cache_key, dumped_resp, ttl)
            logger.debug("Computed and cached response")
            return resp

        return wrapper

    return decorator
