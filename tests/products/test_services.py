from contextlib import contextmanager

from inspect import iscoroutinefunction
from random import randint
from unittest.mock import (
    AsyncMock,
    Mock,
    NonCallableMock,
    create_autospec,
    patch,
)
import pytest

from core.services.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    EntityOperationRestrictedByRefError,
)
from core.pagination import PaginationParams
from gateways.db.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    OperationRestrictedByRefError,
)
from products.domain.services import ProductsService
from core.uow import AbstractUnitOfWork


@contextmanager
def patch_dto_validate():
    model_validate_res = "test res"
    with patch(
        "core.schemas.BaseDTO.model_validate", return_value=model_validate_res
    ) as model_validate_mock:
        yield model_validate_mock


@pytest.fixture
def products_service():
    uow = create_autospec(AbstractUnitOfWork)
    uow.__aenter__.return_value = uow
    for repo_name in (
        "products_repo",
        "categories_repo",
        "delivery_methods_repo",
        "platforms_repo",
    ):
        assert repo_name in AbstractUnitOfWork.__annotations__
        setattr(uow, repo_name, NonCallableMock())
    service = ProductsService(uow)
    return service


def assert_uow_used(uow_mock: Mock):
    uow_mock.__aenter__.assert_awaited_once()
    uow_mock.__aexit__.assert_awaited_once()


class TestProductsService:
    @pytest.mark.parametrize(
        ["create_product_mock", "expected_exc"],
        [
            (AsyncMock(return_value="test product"), None),
            (
                AsyncMock(side_effect=AlreadyExistsError),
                EntityAlreadyExistsError,
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_product(
        self,
        products_service,
        create_product_mock: AsyncMock,
        expected_exc: type[Exception] | None,
    ):
        products_service._uow.products_repo.create_with_image = create_product_mock
        create_dto_mock = Mock()
        with patch_dto_validate() as model_validate_mock:
            if expected_exc:
                with pytest.raises(expected_exc):
                    await products_service.create_product(create_dto_mock)
            else:
                assert (
                    await products_service.create_product(create_dto_mock)
                    == model_validate_mock.return_value
                )
                model_validate_mock.assert_called_once_with(
                    create_product_mock.return_value
                )
        assert_uow_used(products_service._uow)
        create_product_mock.assert_awaited_once_with(create_dto_mock)

    @pytest.mark.parametrize(
        ["update_product_mock", "expected_exc"],
        [
            (AsyncMock(return_value="test product"), None),
            (AsyncMock(side_effect=AlreadyExistsError), EntityAlreadyExistsError),
            (AsyncMock(side_effect=NotFoundError), EntityNotFoundError),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_product(
        self,
        products_service,
        update_product_mock: AsyncMock,
        expected_exc: type[Exception] | None,
    ):
        products_service._uow.products_repo.update_by_id = update_product_mock
        update_dto_mock = Mock()
        product_id = randint(1, 100)
        with patch_dto_validate() as model_validate_mock:
            if expected_exc:
                with pytest.raises(expected_exc):
                    await products_service.update_product(product_id, update_dto_mock)
            else:
                assert (
                    await products_service.update_product(product_id, update_dto_mock)
                    == model_validate_mock.return_value
                )
                model_validate_mock.assert_called_once_with(
                    update_product_mock.return_value
                )
        assert_uow_used(products_service._uow)
        update_product_mock.assert_awaited_once_with(product_id, update_dto_mock)

    @pytest.mark.parametrize(
        ["delete_product_mock", "expected_exc"],
        [
            (AsyncMock(), None),
            (AsyncMock(side_effect=NotFoundError), EntityNotFoundError),
            (
                AsyncMock(side_effect=OperationRestrictedByRefError),
                EntityOperationRestrictedByRefError,
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_delete_product(
        self,
        products_service,
        delete_product_mock,
        expected_exc: type[Exception] | None,
    ):
        products_service._uow.products_repo.delete_by_id = delete_product_mock
        product_id = randint(1, 100)
        if expected_exc:
            with pytest.raises(expected_exc):
                await products_service.delete_product(product_id)
        else:
            assert await products_service.delete_product(product_id) is None
        assert_uow_used(products_service._uow)
        delete_product_mock.assert_awaited_once_with(product_id)

    @pytest.mark.parametrize(
        ["get_product_mock", "expected_exc"],
        [
            (AsyncMock(), None),
            (AsyncMock(side_effect=NotFoundError), EntityNotFoundError),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_product(
        self, products_service, get_product_mock, expected_exc: type[Exception] | None
    ):
        products_service._uow.products_repo.get_by_id = get_product_mock
        product_id = randint(1, 100)
        model_validate_res = "test res"
        with patch_dto_validate() as model_validate_mock:
            if expected_exc:
                with pytest.raises(expected_exc):
                    await products_service.get_product(product_id)
            else:
                assert (
                    await products_service.get_product(product_id) == model_validate_res
                )
                model_validate_mock.assert_called_once_with(
                    get_product_mock.return_value
                )
        assert_uow_used(products_service._uow)
        get_product_mock.assert_awaited_once_with(product_id)

    async def _objects_list_test_helper(
        self,
        products_service,
        obj_name_plural: str,
    ):
        objects_len = 10
        objects_list_mock = AsyncMock(
            return_value=["test" + str(i) for i in range(objects_len)]
        )
        getattr(
            products_service._uow, obj_name_plural + "_repo"
        ).list = objects_list_mock
        model_validate_res = "test res"
        test_func = getattr(products_service, obj_name_plural + "_list")
        assert iscoroutinefunction(test_func)
        with patch_dto_validate() as model_validate_mock:
            assert await test_func() == [model_validate_res] * objects_len
            model_validate_mock.assert_called()
        assert_uow_used(products_service._uow)
        objects_list_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_categories_list(self, products_service):
        await self._objects_list_test_helper(products_service, "categories")

    @pytest.mark.asyncio
    async def test_platforms_list(self, products_service):
        await self._objects_list_test_helper(products_service, "platforms")

    @pytest.mark.asyncio
    async def test_delivery_methods_list(self, products_service):
        await self._objects_list_test_helper(products_service, "delivery_methods")

    @pytest.mark.asyncio
    async def test_list_products(self, products_service):
        list_products_args = (
            "test query",
            None,
            None,
            None,
            PaginationParams(),
        )
        products_len = 3
        products = ["product" + str(i) for i in range(products_len)]
        list_products_mock = AsyncMock(return_value=(products, products_len))
        products_service._uow.products_repo.filter_paginated_list = list_products_mock
        model_validate_res = "test res"
        with patch_dto_validate() as model_validate_mock:
            assert await products_service.list_products(*list_products_args) == (
                [model_validate_res] * products_len,
                products_len,
            )
            model_validate_mock.assert_called()
        assert_uow_used(products_service._uow)
        list_products_mock.assert_awaited_once_with(*list_products_args)
