from datetime import datetime
from random import randint
from unittest.mock import Mock, NonCallableMock, create_autospec, patch
import pytest
from sqlalchemy import Select, inspect, not_, or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from gateways.db.sqlalchemy_gateway import PaginationRepository, SqlAlchemyRepository

from products.models import Product
from products.repositories import ProductsRepository


@pytest.fixture
def products_repo():
    session = create_autospec(AsyncSession)
    return ProductsRepository(session)


def get_dto_mock(**kwargs):
    dto_mock = Mock(**kwargs)
    dto_dump = {"a": 1, "b": 2}
    dto_mock.model_dump.return_value = dto_dump
    return dto_mock


class TestProductsRepo:
    @pytest.mark.asyncio
    async def test_create_with_image(self, products_repo):
        image_url = "test image url"
        dto_mock = get_dto_mock()
        create_mock_res = "created product"
        with patch.object(
            SqlAlchemyRepository,
            "create",
            return_value=create_mock_res,
        ) as create_mock:
            res = await products_repo.create_with_image(dto_mock, image_url)
            dto_mock.model_dump.assert_called_with(
                exclude={"category", "platform", "delivery_method", "image"},
            )
            create_mock.assert_awaited_once_with(
                **dto_mock.model_dump.return_value,
                image_url=image_url,
                category_id=dto_mock.category.id,
                platform_id=dto_mock.platform.id,
                delivery_method_id=dto_mock.delivery_method.id,
            )
            assert res == create_mock_res

    @pytest.mark.parametrize(
        ["dto_mock", "image_url"],
        [
            (get_dto_mock(category=None), "test url"),
            (get_dto_mock(), "test_url"),
            (get_dto_mock(), None),
            (get_dto_mock(platform=None), "test_url"),
            (get_dto_mock(delivery_method=None), "test_url"),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_by_id(self, products_repo, dto_mock, image_url: str | None):
        product_id = randint(1, 100)
        disallowed_fields = {"image", "category", "platform", "delivery_method"}
        with patch.object(
            SqlAlchemyRepository, "update", return_value="updated product"
        ) as update_mock:
            res = await products_repo.update_by_id(product_id, dto_mock, image_url)
            dto_mock.model_dump.assert_called_with(
                exclude=disallowed_fields,
                exclude_unset=True,
            )
            update_mock_data = dto_mock.model_dump.return_value
            for field in disallowed_fields:
                assert field not in update_mock_data
            if image_url:
                assert update_mock_data["image_url"] == image_url
            if dto_mock.platform:
                assert update_mock_data["platform_id"] == dto_mock.platform.id
            if dto_mock.category:
                assert update_mock_data["category_id"] == dto_mock.category.id
            if dto_mock.delivery_method:
                assert (
                    update_mock_data["delivery_method_id"]
                    == dto_mock.delivery_method.id
                )
            update_mock.assert_awaited_once_with(update_mock_data, id=product_id)
            assert res == update_mock.return_value

    @pytest.mark.asyncio
    async def test_delete_by_id(self, products_repo):
        product_id = randint(1, 100)
        with patch.object(
            SqlAlchemyRepository, "delete_or_raise_not_found"
        ) as delete_mock:
            res = await products_repo.delete_by_id(product_id)
            assert res is None
            delete_mock.assert_awaited_once_with(id=product_id)

    @pytest.mark.asyncio
    async def test_get_by_id(self, products_repo):
        product_id = randint(1, 100)
        with patch.object(
            SqlAlchemyRepository, "get_one", return_value="received product"
        ) as get_one_mock:
            res = await products_repo.get_by_id(product_id)
            get_one_mock.assert_awaited_once_with(id=product_id)
            assert res == get_one_mock.return_value

    @pytest.mark.asyncio
    async def test_list_by_ids(self, products_repo):
        products_ids = [randint(1, 100) for _ in range(10)]
        query_res = NonCallableMock()
        products_repo.session.execute.return_value = query_res
        with patch.object(
            Select, "where", return_value="test sql query"
        ) as where_clause_mock:
            res = await products_repo.list_by_ids(products_ids)
            assert inspect(where_clause_mock.call_args[0][0]).compare(
                Product.id.in_(products_ids)
            )
            products_repo.session.execute.assert_awaited_once_with(
                where_clause_mock.return_value
            )
            query_res.scalars.assert_called_once()
            query_res.scalars().all.assert_called_once()
            assert res == query_res.scalars().all()

    @pytest.mark.parametrize(
        ["query", "category_id", "discounted", "in_stock"],
        [
            ("test query", randint(1, 100), True, True),
            ("test query", randint(1, 100), False, False),
            (None, None, None, None),
        ],
    )
    @pytest.mark.asyncio
    async def test_filter_paginated_list(
        self,
        products_repo,
        query: str | None,
        category_id: int | None,
        discounted: bool | None,
        in_stock: bool | None,
    ):
        pagination_params_mock = Mock()
        test_stmt = select(Product)
        query_res = NonCallableMock()
        products_repo.session.execute.return_value = query_res
        with (
            patch.object(
                PaginationRepository, "_get_pagination_stmt", return_value=test_stmt
            ) as pagination_stmt_mock,
            patch.object(
                PaginationRepository, "_split_records_and_count"
            ) as pagination_res_mock,
        ):
            res = await products_repo.filter_paginated_list(
                query, category_id, discounted, in_stock, pagination_params_mock
            )
            pagination_stmt_mock.assert_called_once_with(pagination_params_mock)
            if query is not None:
                test_stmt = test_stmt.where(Product.name.ilike(f"%{query}%"))
            if category_id is not None:
                test_stmt = test_stmt.filter_by(category_id=category_id)
            if discounted is not None:
                base_cond = and_(
                    or_(
                        Product.discount_valid_to.is_(None),
                        Product.discount_valid_to >= datetime.now(),
                    ),
                    Product.discount > 0,
                )

                if discounted is True:
                    test_stmt = test_stmt.where(base_cond)
                else:
                    test_stmt = test_stmt.where(not_(base_cond))
            if in_stock is not None:
                test_stmt = test_stmt.filter_by(in_stock=in_stock)
            session_exec = products_repo.session.execute
            session_exec.assert_awaited()
            assert str(session_exec.call_args[0][0]) == str(test_stmt)
            pagination_res_mock.assert_called_once_with(query_res.all())
            assert res == pagination_res_mock.return_value
