import random
import string
import typing as t
from pathlib import Path
from config import Config

import aiofiles
from fastapi import UploadFile


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
    from core.ioc import Resolve

    return Path() / Resolve(Config).server.media_serve_path


async def save_upload_file(upload_file: UploadFile) -> str:
    # if not UPLOAD_DIR.exists():
    #     UPLOAD_DIR.mkdir()
    if upload_file.filename is None:
        unique_filename = "".join(
            random.sample([char for char in string.ascii_letters], 20)
        ) + str(random.randint(1, 10000))
    else:
        name, extensions = filename_split(upload_file.filename)
        name += str(random.randint(10, 100000))
        unique_filename = f"{name}.{'.'.join(extensions)}"
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
    serve_url = cfg.server.media_serve_path
    return f"{cfg.server.addr}/{serve_url}/{filename}"


class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs) -> t.Self:
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
