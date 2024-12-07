import random
from pathlib import Path
from typing import Final

import aiofiles
from fastapi import UploadFile

DEFAULT_UPLOAD_DIR: Final[Path] = Path() / "media"


def _filename_split(p: Path) -> tuple[str, str]:
    """Splits filename to name and extensions"""
    filename_splitted = p.name.split(".")
    filename_i = 1 if p.name.startswith(".") else 0
    filename = filename_splitted[filename_i]
    if p.name.startswith("."):
        filename = "." + filename
    extensions = ".".join(filename_splitted[filename_i + 1 :])
    return filename, extensions


async def save_upload_file(upload_file: UploadFile, dest_path: Path | None = None) -> Path:
    if dest_path is None:
        dest_path = DEFAULT_UPLOAD_DIR / upload_file.filename
        if not DEFAULT_UPLOAD_DIR.exists():
            DEFAULT_UPLOAD_DIR.mkdir()
    name, extensions = _filename_split(dest_path)
    name += str(random.randint(10, 10000))
    unique_filename = f"{name}.{extensions}"
    dest_path = dest_path.parent / unique_filename
    try:
        async with aiofiles.open(dest_path, "wb") as buffer:
            while content := await upload_file.read():
                await buffer.write(content)
    finally:
        await upload_file.close()
    return dest_path
