from pathlib import Path
from fastapi import UploadFile
import random
import aiofiles
from string import ascii_letters

from config import Config


def filename_split(orig_filename: str) -> tuple[str, list[str]]:
    """Splits filename to name and extensions"""
    filename_splitted = orig_filename.split(".")
    filename_i = 1 if orig_filename.startswith(".") else 0
    filename = filename_splitted[filename_i]
    if orig_filename.startswith("."):
        filename = "." + filename
    extensions = filename_splitted[filename_i + 1 :]
    return filename, extensions


FILES_UPLOAD_DIR = Path() / "media"


def _get_unique_filename(upload_file: UploadFile) -> str:
    if upload_file.filename is None:
        unique_filename = "".join(
            random.sample([char for char in ascii_letters], 20)
        ) + str(random.randint(1, 10000))
    else:
        name, extensions = filename_split(upload_file.filename)
        name += str(random.randint(10, 100000))
        unique_filename = f"{name}.{'.'.join(extensions)}"
    return unique_filename


async def save_upload_file(upload_file: UploadFile) -> str:
    unique_filename = _get_unique_filename(upload_file)
    dest_path = FILES_UPLOAD_DIR / unique_filename
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
