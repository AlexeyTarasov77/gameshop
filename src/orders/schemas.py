from datetime import datetime
from decimal import Decimal
import re
from typing import Annotated, Any
from uuid import UUID
from pydantic import (
    AfterValidator,
    EmailStr,
    AliasChoices,
    Field,
    field_validator,
    model_validator,
)
from payments.models import AvailablePaymentSystems
from shopping.schemas import ItemInCartDTO
from users.schemas import ShowUser
from core.schemas import Base64Int, BaseDTO
from orders.models import InAppOrder, OrderStatus


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


class _InAppOrderItemProduct(BaseDTO):
    id: Base64Int
    name: str


class InAppOrderItemDTO(BaseDTO):
    id: Base64Int
    product: _InAppOrderItemProduct
    price: Decimal
    quantity: int = Field(gt=0)
    total_price: Decimal


class InAppOrderCustomerDTO(BaseDTO):
    email: EmailStr | None = Field(
        validation_alias=AliasChoices("customer_email", "email"), default=None
    )
    phone: PhoneNumber | None = Field(
        validation_alias=AliasChoices("customer_phone", "phone"), default=None
    )
    tg_username: CustomerTg = Field(
        validation_alias=AliasChoices("customer_tg_username", "tg_username")
    )

    name: CustomerName | None = Field(
        validation_alias=AliasChoices("customer_name", "name"), default=None
    )


class InAppOrderCustomerWithUserIdDTO(InAppOrderCustomerDTO):
    user_id: Base64Int | None


class InAppOrderCustomerWithUserDTO(InAppOrderCustomerDTO):
    user: ShowUser | None


class CreateInAppOrderDTO(BaseDTO):
    cart: list[ItemInCartDTO]
    user: InAppOrderCustomerDTO
    selected_ps: AvailablePaymentSystems = AvailablePaymentSystems.PAYPALYCH

    # TODO: check if that validator is redundant
    @field_validator("cart")
    @classmethod
    def check_cart(cls, value: list) -> list:
        assert len(value) > 0, "Cart can't be empty"
        return value


class UpdateOrderDTO(BaseDTO):
    status: OrderStatus


class BaseOrderDTO(BaseDTO):
    id: UUID
    order_date: datetime
    status: OrderStatus
    total: Decimal


class InAppOrderDTO(BaseOrderDTO):
    customer: InAppOrderCustomerWithUserIdDTO

    @model_validator(mode="before")
    @classmethod
    def convert_customer_data(cls, obj: Any) -> Any:
        if not isinstance(obj, InAppOrder):
            return obj
        obj.customer = InAppOrderCustomerWithUserIdDTO.model_validate(obj)  # type: ignore
        return obj


class OrderPaymentDTO[T: BaseDTO](BaseDTO):
    payment_url: str
    order: T


class InAppOrderExtendedDTO(InAppOrderDTO):
    items: list[InAppOrderItemDTO]
    customer: InAppOrderCustomerWithUserDTO  # type: ignore
    bill_id: str
    paid_with: AvailablePaymentSystems

    @model_validator(mode="before")
    @classmethod
    def convert_customer_data(cls, obj: Any) -> Any:
        if not isinstance(obj, InAppOrder):
            return obj
        obj.customer = InAppOrderCustomerWithUserDTO.model_validate(obj)  # type: ignore
        return obj


class CreateSteamTopUpOrderDTO(BaseDTO):
    steam_login: str
    rub_amount: Decimal
    selected_ps: AvailablePaymentSystems = AvailablePaymentSystems.PAYPALYCH
    customer_email: EmailStr


class SteamTopUpOrderCustomerDTO(BaseDTO):
    email: EmailStr | None = Field(validation_alias="customer_email", default=None)
    steam_login: str


class SteamTopUpOrderCustomerWithUserIdDTO(SteamTopUpOrderCustomerDTO):
    user_id: Base64Int | None


class SteamTopUpOrderDTO(BaseOrderDTO):
    customer: SteamTopUpOrderCustomerWithUserIdDTO
    amount: Decimal
    percent_fee: int
