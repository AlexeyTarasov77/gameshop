import asyncio
from collections.abc import Callable, Generator, Sequence
from functools import wraps
from logging import Logger
import time
from typing import Coroutine, Any
from concurrent.futures import ThreadPoolExecutor


def run_coroutine_sync[T](coroutine: Coroutine[Any, Any, T]) -> T:
    def run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(coroutine)
        finally:
            new_loop.close()

    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(run_in_new_loop)
        return future.result()


def normalize_s(s: str) -> str:
    return s.strip().lower()


def measure_time_async[T](func: Callable[..., Coroutine[Any, Any, T]]):
    from core.ioc import Resolve

    logger = Resolve(Logger)

    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        t1 = time.perf_counter()
        logger.info("%s execution started", func)
        res = await func(*args, **kwargs)
        logger.info(
            "%s completed execution, which took: %.2f seconds",
            func,
            time.perf_counter() - t1,
        )
        return res

    return wrapper


def chunkify[T](seq: Sequence[T], chunk_size: int) -> Generator[Sequence[T]]:
    full_chunks_count, left_unchunked = divmod(len(seq), chunk_size)
    top = 0
    for i in range(full_chunks_count):
        top = i + 1 * chunk_size
        yield seq[i:top]
    yield seq[top : top + left_unchunked]
