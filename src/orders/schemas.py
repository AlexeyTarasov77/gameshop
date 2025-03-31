from datetime import datetime
from decimal import Decimal
import re
from typing import Annotated, Any, Literal
from uuid import UUID
from pydantic import (
    AfterValidator,
    EmailStr,
    AliasChoices,
    Field,
    HttpUrl,
    PlainSerializer,
    field_validator,
    model_validator,
)
from payments.models import AvailablePaymentSystems
from shopping.schemas import ItemInCartDTO
from users.schemas import ShowUser
from core.schemas import Base64Int, BaseDTO
from orders.models import InAppOrder, OrderCategory, OrderStatus


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


def check_steam_friend_link(value: HttpUrl):
    assert value.host == "s.team", "Friend link domain should be equal to: s.team"


OrderCategoryField = Annotated[
    OrderCategory, PlainSerializer(lambda v: {"name": v.value.label, "id": v.value})
]

PhoneNumber = Annotated[str, AfterValidator(check_phone)]
CustomerName = Annotated[str, AfterValidator(check_name)]
CustomerTg = Annotated[str, AfterValidator(normalize_tg_username)]
SteamFriendLink = Annotated[HttpUrl, AfterValidator(check_steam_friend_link)]
SteamGiftRegions = Literal["ua", "ru", "kz"]


class _WithOptionalUserId(BaseDTO):
    user_id: Base64Int | None


class _WithOptionalUser(BaseDTO):
    user: ShowUser | None


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


class InAppOrderCustomerWithUserIdDTO(InAppOrderCustomerDTO, _WithOptionalUserId): ...


class InAppOrderCustomerWithUserDTO(InAppOrderCustomerDTO, _WithOptionalUser): ...


class CreateInAppOrderDTO(BaseDTO):
    cart: list[ItemInCartDTO]
    user: InAppOrderCustomerDTO
    selected_ps: AvailablePaymentSystems = AvailablePaymentSystems.PAYPALYCH

    @field_validator("cart")
    @classmethod
    def check_cart(cls, value: list) -> list:
        assert len(value) > 0, "Cart can't be empty"
        return value


class UpdateOrderDTO(BaseDTO):
    status: OrderStatus


class ShowBaseOrderDTO(BaseDTO):
    id: UUID
    order_date: datetime
    status: OrderStatus
    total: Decimal
    bill_id: str | None = None
    paid_with: AvailablePaymentSystems | None = None
    category: OrderCategoryField


class InAppOrderDTO(ShowBaseOrderDTO):
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

    @model_validator(mode="before")
    @classmethod
    def convert_customer_data(cls, obj: Any) -> Any:
        if not isinstance(obj, InAppOrder):
            return obj
        obj.customer = InAppOrderCustomerWithUserDTO.model_validate(obj)  # type: ignore
        return obj


class CreateSteamOrderBaseDTO(BaseDTO):
    selected_ps: AvailablePaymentSystems = AvailablePaymentSystems.PAYPALYCH
    customer_email: EmailStr


class CreateSteamTopUpOrderDTO(CreateSteamOrderBaseDTO):
    steam_login: str
    rub_amount: Decimal = Field(gt=0)


class CreateSteamGiftOrderDTO(CreateSteamOrderBaseDTO):
    friend_link: SteamFriendLink
    product_id: Base64Int
    region: SteamGiftRegions


class SteamTopUpOrderCustomerDTO(BaseDTO):
    customer_email: EmailStr | None = None
    steam_login: str


class _BaseSteamTopUpOrderDTO(SteamTopUpOrderCustomerDTO, ShowBaseOrderDTO):
    amount: Decimal
    percent_fee: int


class SteamTopUpOrderDTO(_BaseSteamTopUpOrderDTO, _WithOptionalUser): ...


class SteamTopUpOrderExtendedDTO(_BaseSteamTopUpOrderDTO, _WithOptionalUser): ...


class SteamGiftOrderDTO(CreateSteamGiftOrderDTO, _WithOptionalUserId): ...
