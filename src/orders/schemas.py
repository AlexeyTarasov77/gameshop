from datetime import datetime
from decimal import Decimal
import re
from typing import Annotated, Self
from uuid import UUID
from pydantic import AfterValidator, EmailStr, Field, field_validator
from payments.models import AvailablePaymentSystems
from users.schemas import ShowUser
from core.schemas import Base64Int, BaseDTO
from orders.models import Order, OrderStatus


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


class _BaseOrderItemDTO(BaseDTO):
    quantity: int = Field(gt=0)
    price: Decimal


class OrderItemCreateDTO(_BaseOrderItemDTO):
    product_id: Base64Int


class OrderItemProduct(BaseDTO):
    id: int
    name: str


class OrderItemShowDTO(_BaseOrderItemDTO):
    id: int
    product: OrderItemProduct
    total_price: Decimal


class CustomerDTO(BaseDTO):
    email: EmailStr | None = None
    phone: PhoneNumber | None = None
    tg_username: CustomerTg
    name: CustomerName | None = None

    @classmethod
    def from_order(cls, order: Order) -> Self:
        prefix = "customer_"
        return cls.model_construct(
            None,
            **{
                k.removeprefix(prefix): getattr(order, k)
                for k in order.__table__.c.keys()
                if k.startswith(prefix)
            },
        )


class CustomerWithUserIdDTO(CustomerDTO):
    user_id: Base64Int | None

    @classmethod
    def from_order(cls, order: Order) -> Self:
        obj = super().from_order(order)
        obj.user_id = order.user_id
        return obj


class CustomerWithUserDTO(CustomerDTO):
    user: ShowUser | None

    @classmethod
    def from_order(cls, order: Order) -> Self:
        obj = super().from_order(order)
        obj.user = ShowUser.model_validate(order.user) if order.user else None
        return obj


class CreateOrderDTO(BaseDTO):
    cart: list[OrderItemCreateDTO]
    user: CustomerDTO
    selected_system_name: AvailablePaymentSystems = AvailablePaymentSystems.PAYPALYCH

    @field_validator("cart")
    @classmethod
    def check_cart(cls, value: list) -> list:
        assert len(value) > 0
        return value


class UpdateOrderDTO(BaseDTO):
    status: OrderStatus
    bill_id: str | None = None


class ShowOrder(BaseDTO):
    id: UUID
    order_date: datetime
    status: OrderStatus
    total: Decimal
    customer: CustomerWithUserIdDTO

    @classmethod
    def from_model(cls, order: Order, **kwargs):
        return cls.model_validate(
            {
                **order.dump(),
                "customer": cls.__annotations__["customer"].from_order(order),
                **kwargs,
            }
        )


class CreateOrderResDTO(BaseDTO):
    payment_url: str
    order: ShowOrder


class ShowOrderExtended(ShowOrder):
    items: list[OrderItemShowDTO]
    customer: CustomerWithUserDTO  # type: ignore
