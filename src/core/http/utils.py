import random
from pathlib import Path
from typing import Final

import aiofiles
from fastapi import UploadFile

DEFAULT_UPLOAD_DIR: Final[str] = Path() / "media"

type FilePath = str | Path


async def save_upload_file(
    upload_file: UploadFile, dest_path: FilePath | None = None
) -> FilePath:
    if dest_path is None:
        dest_path = DEFAULT_UPLOAD_DIR / (
            upload_file.filename + str(random.randint(10, 10000))
        )
    try:
        async with aiofiles.open(dest_path, "wb") as buffer:
            while content := await upload_file.read():
                await buffer.write(content)
    finally:
        await upload_file.close()
    return dest_path
