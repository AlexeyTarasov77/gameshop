import typing as t


class Response:
    status: t.Literal["success", "error"]
    data: dict[str, t.Any] | None = None
    errors: list[str]
