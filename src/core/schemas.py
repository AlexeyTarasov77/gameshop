import base64
from typing import Annotated

from fastapi import UploadFile
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    PlainSerializer,
    AnyHttpUrl,
)

from core.utils import filename_split


class BaseDTO(BaseModel):
    class Config:
        from_attributes = True


def _check_image[T: UploadFile](file: T) -> T:
    _, extenstions = filename_split(str(file.filename))
    last_ext = extenstions[-1]
    acceptable_extensions = ["png", "jpg", "jpeg", "gif"]
    assert last_ext in acceptable_extensions, (
        "Provided file is not a valid image. Extension should be one of: "
        + ", ".join(acceptable_extensions)
    )
    return file


def _parse_int(s: str | int) -> int:
    try:
        return int(s)
    except ValueError:
        return int(base64.b64decode(str(s)))


type UrlStr = Annotated[AnyHttpUrl, AfterValidator(lambda val: str(val))]

Image = Annotated[UploadFile, AfterValidator(_check_image)]
Base64Int = Annotated[
    str | int,
    BeforeValidator(_parse_int, json_schema_input_type=str),
    PlainSerializer(
        lambda n: base64.b64encode(str(n).encode()).decode(), return_type=str
    ),
]
