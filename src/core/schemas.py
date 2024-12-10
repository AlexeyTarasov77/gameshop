from typing import Annotated

from fastapi import UploadFile
from pydantic import AfterValidator, BaseModel

from core.utils import filename_split


class BaseDTO(BaseModel):
    class Config:
        from_attributes = True


def _check_image[T: UploadFile](file: T) -> T:
    _, extenstions = filename_split(file.filename)
    last_ext = extenstions[-1]
    acceptable_extensions = ["png", "jpg", "jpeg", "gif"]
    assert last_ext in acceptable_extensions, (
        "Provided file is not a valid image. Extension should be one of: "
        + ", ".join(acceptable_extensions)
    )
    return file


Image = Annotated[UploadFile, AfterValidator(_check_image)]
