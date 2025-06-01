import base64
from contextlib import suppress
from decimal import Decimal
from enum import StrEnum
from fastapi import HTTPException, status
import json
from typing import Annotated, Final, Literal
from fastapi import UploadFile, Path as PathParam
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    HttpUrl,
    PlainSerializer,
    AnyHttpUrl,
    SerializerFunctionWrapHandler,
    TypeAdapter,
    ValidationError,
    WrapSerializer,
)
from pydantic_extra_types.country import CountryAlpha2
from pydantic_extra_types.currency_code import Currency

from core.utils import (
    resolve_file_url,
    filename_split,
    run_coroutine_sync,
    save_upload_file,
)


class BaseDTO(BaseModel):
    class Config:
        from_attributes = True


def require_dto_not_empty(dto: BaseDTO):
    if not dto.model_dump(exclude_unset=True):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Nothing to update. No data provided",
        )


def _check_and_save_image(file: UploadFile) -> str:
    assert file.filename or file.content_type
    if file.content_type:
        assert (
            file.content_type.split("/")[0] == "image"
        ), "Provided file is not a valid image"
    else:
        _, extenstions = filename_split(str(file.filename))
        last_ext = extenstions[-1]
        acceptable_extensions = ["png", "jpg", "jpeg", "gif"]
        assert last_ext in acceptable_extensions, (
            "Provided file is not a valid image. Extension should be one of: "
            + ", ".join(acceptable_extensions)
        )
    return run_coroutine_sync(save_upload_file(file))


def _parse_int(s: str | int) -> int:
    if isinstance(s, int):
        return s
    with suppress(ValueError):
        return int(s)
    try:
        return int(base64.b64decode(str(s)).decode())
    except ValueError:
        raise ValueError(
            'Invalid id, it should be either valid int, int in str form ("1") or valid int base64 encoded'
        )


def _parse_id_optional(s: str | int) -> int | None:
    if s != "":
        id = _parse_int(s)
        assert id > 0, "Value should be greater than 0"
        return id


def _is_valid_url(s: str) -> bool:
    try:
        HttpUrl(s)
    except ValidationError:
        return False
    return True


def float_ser_wrap(v: Decimal, nxt: SerializerFunctionWrapHandler) -> str:
    return str(nxt(round(v)))


def check_currency(v: str) -> str:
    from_, to = v.split("/")
    curr_ta = TypeAdapter(Currency)
    curr_ta.validate_python(from_)
    curr_ta.validate_python(to)
    return v


RoundedDecimal = Annotated[
    Decimal | int, WrapSerializer(float_ser_wrap, when_used="json")
]
ExchangeRate = Annotated[str, AfterValidator(check_currency)]
ParseJson = BeforeValidator(lambda s: json.loads(s) if isinstance(s, str) else s)
UrlStr = Annotated[AnyHttpUrl, AfterValidator(lambda val: str(val))]
ImgUrl = Annotated[
    str,
    PlainSerializer(lambda s: resolve_file_url(s) if not _is_valid_url(s) else s),
]
UploadImage = Annotated[UploadFile, AfterValidator(_check_and_save_image)]
_base64int_serializer = PlainSerializer(
    lambda n: base64.b64encode(str(n).encode()).decode(),
    return_type=str,
    when_used="json",
)
Base64Int = Annotated[
    str | int,
    BeforeValidator(_parse_int, json_schema_input_type=str),
    _base64int_serializer,
]
EntityIDParam = Annotated[Base64Int, PathParam(gt=0)]
Base64IntOptionalIDParam = Annotated[
    str | int | None,
    BeforeValidator(_parse_id_optional, json_schema_input_type=str),
    _base64int_serializer,
]

type EmptyRegionT = Literal[""]

EMPTY_REGION: Final[EmptyRegionT] = ""

ProductRegion = Annotated[
    CountryAlpha2 | EmptyRegionT,
    BeforeValidator(lambda s: s.strip() if isinstance(s, str) else s),
]


class OrderByOption(StrEnum):
    ASC = "asc"
    DESC = "desc"
