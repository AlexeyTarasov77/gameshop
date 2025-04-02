import asyncio
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
