import sys
from pathlib import Path

sys.path.append(Path().absolute().as_posix())

from random import randint
import pytest
from contextlib import nullcontext as does_not_raise
from unittest.mock import AsyncMock, create_autospec

from cart.domain.services import CartService
from cart.repositories import CartRepository
from core.services.exceptions import EntityNotFoundError
from core.uow import AbstractUnitOfWork
from gateways.db.exceptions import NotFoundError


@pytest.fixture
def cart_service() -> CartService:
    uow = create_autospec(AbstractUnitOfWork)
    uow.__aenter__.return_value = uow
    cart_repo = create_autospec(CartRepository)
    return CartService(uow, cart_repo)


class TestCartService:
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
    async def test_update_product_qty(
        self,
        cart_service,
        qty: int,
        update_mock: AsyncMock | None,
        delete_mock: AsyncMock | None,
        expected_exc: type[Exception] | None,
    ):
        product_id = randint(1, 100)
        session_id = "testid"
        if update_mock:
            cart_service._cart_repo.update_qty_by_id = update_mock
        if delete_mock:
            cart_service._cart_repo.delete_by_id = delete_mock
        expected_exc_ctx = (
            pytest.raises(expected_exc) if expected_exc else does_not_raise()
        )
        with expected_exc_ctx:
            await cart_service.update_product_qty(product_id, qty, session_id)
        if qty == 0:
            assert delete_mock
            return delete_mock.assert_awaited_once_with(product_id, session_id)
        assert update_mock
        update_mock.assert_awaited_once_with(product_id, qty, session_id)
