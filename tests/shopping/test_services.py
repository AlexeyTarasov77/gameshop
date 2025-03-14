from shopping.domain.interfaces import CartManagerI, WishlistManagerI
from tests.utils import exc_to_ctx_manager

from random import randint
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, create_autospec, patch

from shopping.domain.services import ShoppingService
from core.services.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import AlreadyExistsError, NotFoundError


@pytest.fixture
def sessions_service() -> ShoppingService:
    uow = create_autospec(AbstractUnitOfWork)
    uow.__aenter__.return_value = uow
    cart_repo = create_autospec(CartManagerI)
    wishlist_repo = create_autospec(WishlistManagerI)
    return ShoppingService(uow, cart_repo, wishlist_repo)


class TestSessionsService:
    @pytest.mark.parametrize(
        ["qty", "update_mock", "delete_mock", "expected_exc"],
        [
            (randint(1, 10), AsyncMock(), None, None),
            (0, None, AsyncMock(), None),
            (
                randint(1, 10),
                AsyncMock(side_effect=NotFoundError),
                None,
                EntityNotFoundError,
            ),
            (
                0,
                None,
                AsyncMock(side_effect=NotFoundError),
                EntityNotFoundError,
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_cart_update_qty(
        self,
        sessions_service,
        qty: int,
        update_mock: AsyncMock | None,
        delete_mock: AsyncMock | None,
        expected_exc: type[Exception] | None,
    ):
        product_id = randint(1, 100)
        cart_manager = sessions_service._cart_manager
        if update_mock:
            cart_manager.update_qty_by_id = update_mock
        if delete_mock:
            cart_manager.delete_by_id = delete_mock
        with exc_to_ctx_manager(expected_exc):
            await sessions_service.cart_update_qty(product_id, qty)
        if qty == 0:
            assert delete_mock
            return delete_mock.assert_awaited_once_with(product_id)
        assert update_mock
        update_mock.assert_awaited_once_with(product_id, qty)

    @pytest.mark.parametrize(
        ["already_exists", "dto_mock"],
        [(True, MagicMock(quantity=None)), (False, MagicMock(quantity=10))],
    )
    @pytest.mark.asyncio
    async def test_cart_add(
        self, sessions_service, already_exists: bool, dto_mock: Mock
    ):
        expected_qty = dto_mock.quantity or 1
        sessions_service._cart_manager.check_exists = AsyncMock(
            return_value=already_exists
        )
        dto_mock.product_id = randint(1, 100)
        with patch.object(
            sessions_service, "_require_product_in_stock"
        ) as require_product_in_stock_mock:
            res = await sessions_service.cart_add(dto_mock)
            assert dto_mock.quantity == expected_qty
            require_product_in_stock_mock.assert_awaited_once_with(dto_mock.product_id)
            if already_exists:
                cart_add = sessions_service._cart_manager.add
                cart_add.assert_awaited_once_with(dto_mock)
                assert res == cart_add.return_value
            else:
                sessions_service._cart_manager.create.assert_awaited_once_with(dto_mock)
                assert res == expected_qty

    @pytest.mark.parametrize(
        ["delete_mock", "expected_exc"],
        [
            (AsyncMock(), None),
            (AsyncMock(side_effect=NotFoundError), EntityNotFoundError),
        ],
    )
    @pytest.mark.asyncio
    async def test_cart_remove(
        self, sessions_service, delete_mock: AsyncMock, expected_exc
    ):
        sessions_service._cart_manager.delete_by_id = delete_mock
        product_id = randint(1, 100)
        with exc_to_ctx_manager(expected_exc):
            await sessions_service.cart_remove(product_id)
        delete_mock.assert_awaited_once_with(product_id)

    @pytest.mark.parametrize(
        ["append_mock", "expected_exc"],
        [
            (AsyncMock(), None),
            (AsyncMock(side_effect=AlreadyExistsError), EntityAlreadyExistsError),
        ],
    )
    @pytest.mark.asyncio
    async def test_wishlist_add(self, sessions_service, append_mock, expected_exc):
        sessions_service._wishlist_manager.append = append_mock
        product_id = randint(1, 100)
        with patch.object(
            sessions_service, "_require_product_in_stock"
        ) as require_product_in_stock_mock:
            with exc_to_ctx_manager(expected_exc):
                await sessions_service.wishlist_add(product_id)
                require_product_in_stock_mock.assert_awaited_once_with(product_id)
                append_mock.assert_awaited_once_with(product_id)

    @pytest.mark.parametrize(
        ["remove_mock", "expected_exc"],
        [
            (AsyncMock(side_effect=NotFoundError), EntityNotFoundError),
            (AsyncMock(), None),
        ],
    )
    @pytest.mark.asyncio
    async def test_wishlist_remove(self, sessions_service, remove_mock, expected_exc):
        product_id = randint(1, 100)
        sessions_service._wishlist_manager.remove = remove_mock
        with exc_to_ctx_manager(expected_exc):
            await sessions_service.wishlist_remove(product_id)
            remove_mock.assert_awaited_once_with(product_id)
