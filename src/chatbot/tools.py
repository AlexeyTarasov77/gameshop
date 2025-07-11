from logging import Logger
from langchain_core.tools import BaseTool, tool

from core.uow import AbstractUnitOfWork
from products.schemas import ListProductsParamsDTO


class ChatBotToolsContainer:
    def __init__(self, uow: AbstractUnitOfWork, logger: Logger):
        self._uow = uow
        self._logger = logger

    @tool
    async def _find_games(self, params: ListProductsParamsDTO):
        """
        Use this tool to find and search for games. Call this when users ask about games, want to browse games,
        or need to filter games by specific criteria.

        Use the query parameter for text-based searches (game names, descriptions).
        Use discounted=True to find games on sale or discounted=False for regular price games.
        Use in_stock=True to only show available games or in_stock=False for out-of-stock games.
        Filter by categories, platforms, delivery methods, or regions as needed.
        Use price_ordering to sort results by price (ascending/descending).

        This tool handles pagination automatically and returns a list of matching games.
        """
        self._logger.info(
            "Invoked find_games llm tool. Params: %s", params.model_dump()
        )
        async with self._uow as uow:
            return await uow.products_repo.filter_paginated_list(params)

    def get_tools(self) -> list[BaseTool]:
        return [self._find_games]
