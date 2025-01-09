from datetime import datetime
from decimal import Decimal
import re
from pydantic import EmailStr, Field, field_validator
from core.schemas import Base64Int, BaseDTO
from orders.models import OrderStatus


class OrderItemCreateDTO(BaseDTO):
    quantity: int = Field(gt=0)
    price: Decimal
    product_id: Base64Int


class OrderItemShowDTO(OrderItemCreateDTO):
    id: Base64Int


class CustomerDataDTO(BaseDTO):
    email: EmailStr | None = None
    phone: str | None = Field(min_length=5, default=None)
    tg_username: str
    user_id: Base64Int | None = None
    name: str

    @field_validator("name")
    @classmethod
    def check_name(cls, value: str) -> str:
        LETTER_MATCH_PATTERN = re.compile(r"^[а-яА-Яa-zA-Z]+$")
        if not LETTER_MATCH_PATTERN.match(value):
            raise ValueError("Имя может состоять только из букв")
        return value

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value: str) -> str:
        PHONE_MATCH_PATTERN = re.compile(
            r"^\+?\d{1,3}?([-. ])?(\d{1,4}([-. x])?){1,4}$"
        )
        match = PHONE_MATCH_PATTERN.match(value)
        if not match:
            raise ValueError("Невалидный номер телефона")
        # normalize phone number
        if not value.startswith("+"):
            value = "+" + value
        delimiters = match.group(1), match.group(3)
        for delimiter in delimiters:
            if delimiter is not None:
                value.replace(delimiter, "")
        return value


class CreateOrderDTO(BaseDTO):
    cart: list[OrderItemCreateDTO]
    user: CustomerDataDTO


class BaseShowOrder(BaseDTO):
    id: Base64Int
    order_date: datetime
    status: OrderStatus
