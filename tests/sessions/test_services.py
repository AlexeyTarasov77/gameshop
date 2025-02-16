from tests.utils import exc_to_ctx_manager

from random import randint
import pytest
from contextlib import nullcontext as does_not_raise
from unittest.mock import AsyncMock, MagicMock, Mock, create_autospec, patch

from sessions.domain.services import SessionsService
from sessions.repositories import CartSessionManager, WishlistSessionManager
from core.services.exceptions import EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError


@pytest.fixture
def sessions_service() -> SessionsService:
    uow = create_autospec(AbstractUnitOfWork)
    uow.__aenter__.return_value = uow
    cart_repo = create_autospec(CartSessionManager)
    cart_repo.get_for_session.return_value = cart_repo
    wishlist_repo = create_autospec(WishlistSessionManager)
    wishlist_repo.get_for_session.return_value = wishlist_repo
    return SessionsService(uow, cart_repo, wishlist_repo)


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
        session_id = "testid"
        cart_manager = sessions_service._cart_manager_cls
        if update_mock:
            cart_manager.update_qty_by_id = update_mock
        if delete_mock:
            cart_manager.delete_by_id = delete_mock
        with exc_to_ctx_manager(expected_exc):
            await sessions_service.cart_update_qty(product_id, qty, session_id)
        cart_manager.get_for_session.assert_called_once_with(session_id)
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
        session_id = "test"
        expected_qty = dto_mock.quantity or 1
        sessions_service._cart_manager_cls.check_exists = AsyncMock(
            return_value=already_exists
        )
        dto_mock.product_id = randint(1, 100)
        with patch.object(
            sessions_service, "_require_product_in_stock"
        ) as require_product_in_stock_mock:
            res = await sessions_service.cart_add(dto_mock, session_id)
            assert dto_mock.quantity == expected_qty
            require_product_in_stock_mock.assert_awaited_once_with(dto_mock.product_id)
            if already_exists:
                cart_add = sessions_service._cart_manager_cls.add
                cart_add.assert_awaited_once_with(dto_mock)
                assert res == cart_add.return_value
            else:
                sessions_service._cart_manager_cls.create.assert_awaited_once_with(
                    dto_mock
                )
                assert res == dto_mock.quantity
        sessions_service._cart_manager_cls.get_for_session.assert_called_once_with(
            session_id
        )

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
        expected_exc_ctx = (
            pytest.raises(expected_exc) if expected_exc else does_not_raise()
        )
        session_id = "test"
        product_id = randint(1, 100)
        sessions_service._cart_manager_cls.delete_by_id = delete_mock
        with expected_exc_ctx:
            await sessions_service.cart_remove(product_id, session_id)
        delete_mock.assert_awaited_once_with(product_id)
        sessions_service._cart_manager_cls.get_for_session.assert_called_once_with(
            session_id
        )

    @pytest.mark.parametrize(["already_exists"], [(True,), (False,)])
    @pytest.mark.asyncio
    async def test_wishlist_add(self, sessions_service, already_exists: bool):
        check_exists_mock = AsyncMock(return_value=already_exists)
        sessions_service._wishlist_manager_cls.check_exists = check_exists_mock
        product_id = randint(1, 100)
        session_id = "test"
        with patch.object(
            sessions_service, "_require_product_in_stock"
        ) as require_product_in_stock_mock:
            added: bool = await sessions_service.wishlist_add(product_id, session_id)
            assert added == (not already_exists)
            require_product_in_stock_mock.assert_awaited_once_with(product_id)
            check_exists_mock.assert_awaited_once_with(product_id)

    @pytest.mark.parametrize(
        ["remove_mock", "expected_exc"],
        [
            (AsyncMock(side_effect=NotFoundError), EntityNotFoundError),
            (AsyncMock(), None),
        ],
    )
    @pytest.mark.asyncio
    async def test_wishlist_remove(self, sessions_service, remove_mock, expected_exc):
        session_id = "test"
        product_id = randint(1, 100)
        sessions_service._wishlist_manager_cls.remove = remove_mock
        with exc_to_ctx_manager(expected_exc):
            await sessions_service.wishlist_remove(product_id, session_id)
            if not expected_exc:
                remove_mock.assert_awaited_once_with(product_id)
