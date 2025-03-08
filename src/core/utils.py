import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum
import random
import string
from pathlib import Path
from types import EllipsisType
from typing import Any
from config import Config

import aiofiles
from fastapi import UploadFile

type UnspecifiedType = EllipsisType


class CIEnum(StrEnum):
    """Adds support for caseinsensitive member lookup.
    Note that member name should be equal to it's value to work as expected"""

    @classmethod
    def _missing_(cls, value: Any):
        return isinstance(value, str) and cls.__members__.get(value.upper())


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


def filename_split(orig_filename: str) -> tuple[str, list[str]]:
    """Splits filename to name and extensions"""
    filename_splitted = orig_filename.split(".")
    filename_i = 1 if orig_filename.startswith(".") else 0
    filename = filename_splitted[filename_i]
    if orig_filename.startswith("."):
        filename = "." + filename
    extensions = filename_splitted[filename_i + 1 :]
    return filename, extensions


def get_upload_dir() -> Path:
    return Path() / "media"


def _get_unique_filename(upload_file: UploadFile) -> str:
    if upload_file.filename is None:
        unique_filename = "".join(
            random.sample([char for char in string.ascii_letters], 20)
        ) + str(random.randint(1, 10000))
    else:
        name, extensions = filename_split(upload_file.filename)
        name += str(random.randint(10, 100000))
        unique_filename = f"{name}.{'.'.join(extensions)}"
    return unique_filename


async def save_upload_file(upload_file: UploadFile) -> str:
    unique_filename = _get_unique_filename(upload_file)
    dest_path = get_upload_dir() / unique_filename
    try:
        async with aiofiles.open(dest_path, "wb") as dst:
            while content := await upload_file.read(1024):
                await dst.write(content)
    finally:
        await upload_file.close()
    return unique_filename


def get_uploaded_file_url(filename: str) -> str:
    from core.ioc import Resolve

    cfg = Resolve(Config)
    return f"{cfg.server.addr}/media/{filename}"
