import random
import typing as t
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from fastapi import Path as PathParam

from core.schemas import Base64Int
from core.utils import filename_split


type EntityIDParam = t.Annotated[Base64Int, PathParam(gt=0)]

DEFAULT_UPLOAD_DIR: t.Final[Path] = Path() / "media"


async def save_upload_file(
    upload_file: UploadFile, dest_path: Path | None = None
) -> Path:
    if dest_path is None:
        if not upload_file.filename:
            raise Exception("upload file filename can't be None")
        dest_path = DEFAULT_UPLOAD_DIR / upload_file.filename
        if not DEFAULT_UPLOAD_DIR.exists():
            DEFAULT_UPLOAD_DIR.mkdir()
    name, extensions = filename_split(dest_path.name)
    name += str(random.randint(10, 10000))
    unique_filename = f"{name}.{'.'.join(extensions)}"
    dest_path = dest_path.parent / unique_filename
    try:
        async with aiofiles.open(dest_path, "wb") as buffer:
            while content := await upload_file.read():
                await buffer.write(content)
    finally:
        await upload_file.close()
    return dest_path
