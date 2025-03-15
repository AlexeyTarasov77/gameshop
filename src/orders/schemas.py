from datetime import datetime
from decimal import Decimal
import re
from typing import Annotated, Self
from uuid import UUID
from pydantic import AfterValidator, EmailStr, Field, field_validator
from payments.models import AvailablePaymentSystems
from shopping.schemas import AddToCartDTO
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
    LETTER_MATCH_PATTERN = re.compile(r"^([а-яА-Яa-zA-Z]+)(\s[а-яА-Яa-zA-Z]+)?$")
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


class OrderItemInCartDTO(AddToCartDTO): ...


class OrderItemProduct(BaseDTO):
    id: Base64Int
    name: str


class OrderItemShowDTO(BaseDTO):
    id: Base64Int
    product: OrderItemProduct
    price: Decimal
    quantity: int = Field(gt=0)
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
    cart: list[OrderItemInCartDTO]
    user: CustomerDTO
    selected_ps: AvailablePaymentSystems = AvailablePaymentSystems.PAYPALYCH

    @field_validator("cart")
    @classmethod
    def check_cart(cls, value: list) -> list:
        assert len(value) > 0, "Cart can't by empty"
        return value


class UpdateOrderDTO(BaseDTO):
    status: OrderStatus


class BaseShowOrderDTO(BaseDTO):
    id: UUID
    order_date: datetime
    status: OrderStatus
    total: Decimal


class ShowOrder(BaseShowOrderDTO):
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
    bill_id: str
    paid_with: AvailablePaymentSystems


class SteamTopUpCreateDTO(BaseDTO):
    steam_login: str
    rub_amount: Decimal
    selected_ps: AvailablePaymentSystems = AvailablePaymentSystems.PAYPALYCH
    customer_email: EmailStr


class ShowSteamTopUp(BaseShowOrderDTO):
    steam_login: str
    amount: Decimal
    percent_fee: int


class SteamTopUpCreateResDTO(BaseDTO):
    payment_url: str
    order: ShowSteamTopUp
