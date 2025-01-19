from datetime import datetime
from decimal import Decimal
import re
from typing import Annotated
from pydantic import AfterValidator, EmailStr, Field, field_validator
from users.schemas import ShowUser
from core.schemas import Base64Int, BaseDTO
from orders.models import OrderStatus


def check_phone(value: str) -> str:
    assert len(value) >= 5, "Номер телефона слишком короткий!"
    PHONE_MATCH_PATTERN = re.compile(
        r"^\+?\(*\d{1,3}?\)*([-. ])?(\d{1,4}([-. x])?){1,4}$"
    )
    match = PHONE_MATCH_PATTERN.match(value)
    assert match, "Невалидный номер телефона"
    # normalize phone number
    if not value.startswith("+"):
        value = "+" + value
    delimiters = match.group(1), match.group(3)
    for delimiter in delimiters:
        if delimiter is not None:
            value.replace(delimiter, "")
    return value


def check_name(value: str) -> str:
    LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z]+$")
    if not LETTER_MATCH_PATTERN.match(value):
        raise ValueError("Имя может состоять только из букв")
    return value


def normalize_tg_username(value: str) -> str:
    if value.startswith("@"):
        value.replace("@", "")
    return value


PhoneNumber = Annotated[str, AfterValidator(check_phone)]
CustomerName = Annotated[str, AfterValidator(check_name)]
CustomerTg = Annotated[str, AfterValidator(normalize_tg_username)]


class OrderItemCreateDTO(BaseDTO):
    quantity: int = Field(gt=0)
    price: Decimal
    product_id: Base64Int


class OrderItemShowDTO(OrderItemCreateDTO):
    id: Base64Int


class CustomerDataDTO(BaseDTO):
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
    tg_username: CustomerTg
    user_id: Base64Int | None = None
    name: CustomerName | None = None


class CreateOrderDTO(BaseDTO):
    cart: list[OrderItemCreateDTO]
    user: CustomerDataDTO

    @field_validator("cart")
    @classmethod
    def check_cart(cls, value):
        assert len(value) > 0
        return value


class UpdateOrderDTO(BaseDTO):
    status: OrderStatus


class BaseOrderDTO(BaseDTO):
    id: Base64Int
    order_date: datetime
    status: OrderStatus
    customer_email: EmailStr | None
    customer_name: str | None
    customer_phone: str | None
    customer_tg: CustomerTg


class BaseShowOrder(BaseOrderDTO):
    user_id: int | None


class ShowOrderWithRelations(BaseOrderDTO):
    user: ShowUser | None
    items: list[OrderItemShowDTO]
