from dataclasses import dataclass
from logging import Logger
import re
import asyncio
import sys

from sqlalchemy import delete
from core.ioc import Resolve
from typing import cast
from bs4 import BeautifulSoup, Tag, NavigableString
import requests
from gateways.db.main import SqlAlchemyDatabase
from products.models import ProductOnSale
from returns.maybe import Maybe
from datetime import datetime
from pytz import timezone


@dataclass
class ParsableProduct:
    name: str
    photo_url: str
    cheapest_price: float
    deal_until: datetime | None

    def __str__(self) -> str:
        return (
            f"<strong>Имя:</strong> {self.name}\n"
            f"<strong>Цена:</strong> {self.cheapest_price} RUB\n"
            f"<strong>Скидка действует до:</strong> {self.deal_until}"
        )

    @staticmethod
    def from_html(el: Tag):
        maybe_tag_a: Maybe[NavigableString | Tag | int] = Maybe.from_optional(
            el.find("div", class_="pull-left")
        ).bind_optional(lambda div: div.find("a"))
        tag_a = maybe_tag_a.unwrap()
        if not (isinstance(tag_a, Tag)):
            raise ValueError("Got invalid html tag")
        span_tag = el.find("span", string=re.compile("^Deal until:"))
        name = str(tag_a.get("title"))
        photo_tag = tag_a.find("img")
        if not photo_tag or not isinstance(photo_tag, Tag):
            raise ValueError("Tag with photo_url not found")
        photo_url = str(photo_tag.get("src"))
        deal_until = None
        if span_tag:
            if not any([isinstance(span_tag, Tag), getattr(span_tag, "string", None)]):
                raise ValueError("Got invalid html tag")
            date, time, tz_string = span_tag.string.split()[2:]  # type: ignore
            dt = datetime.strptime(date + " " + time, "%d.%m.%Y %H:%M")
            tz = timezone(tz_string)
            deal_until = tz.localize(dt)
        price_regex = re.compile(r"\d+([.,]\d+)?")
        maybe_price_tag = (
            Maybe.from_optional(cast(Tag | None, el.find("div", class_="row")))
            .bind_optional(lambda row: row.contents[1])
            .bind_optional(
                lambda el: cast(Tag | None, el.find_next("div", class_="row"))
            )
            .bind_optional(lambda row: row.contents[2])
            .bind_optional(
                lambda container: container.find_next("span", string=price_regex)
            )
        )
        price_tag = maybe_price_tag.unwrap()
        price_match = re.search(price_regex, getattr(price_tag, "string"))
        if not price_match:
            raise ValueError("Unable to extract price")
        price = float(price_match.group().replace(",", "."))
        return ParsableProduct(
            name=name, photo_url=photo_url, cheapest_price=price, deal_until=deal_until
        )


def parse_discounted_products(
    url: str, count: int | None = None
) -> list[ParsableProduct]:
    headers = {
        "Accept": "text/html",
    }
    req = requests.get(url, headers)
    soup = BeautifulSoup(req.text, "html.parser")
    maybe_products: Maybe[list[ParsableProduct]] = (
        Maybe.from_optional(soup.find("div", class_="content-wrapper"))
        .bind_optional(lambda el: cast(Tag, el).find("section", class_="content"))
        .bind_optional(
            lambda content: cast(Tag, content).find_all(
                "div", class_="box-body comparison-table-entry", limit=count
            )
        )
        .bind_optional(
            lambda products: [
                ParsableProduct.from_html(product_tag) for product_tag in products
            ]
        )
    )
    return maybe_products.unwrap()


async def main():
    SALES_URL = "https://www.xbox-now.com/ru/deal-list"
    logger = Resolve(Logger)
    try:
        limit = int(sys.argv[2])
    except Exception:
        limit = None
    logger.info("Parsing up to %s discounts from %s", limit, SALES_URL)
    discounted_products = parse_discounted_products(SALES_URL, limit)
    logger.info(
        "%s discounts succesfully parsed. Loading to db...", len(discounted_products)
    )
    async with Resolve(SqlAlchemyDatabase).session_factory() as session:
        logger.debug("Cleaning old discounts...")
        await session.execute(delete(ProductOnSale))
        session.add_all(
            [
                ProductOnSale(
                    name=product.name,
                    price=product.cheapest_price,
                    photo_url=product.photo_url,
                    deal_until=product.deal_until,
                )
                for product in discounted_products
            ]
        )
        await session.commit()
        logger.debug("Commiting transaction")
    logger.info("Discounts were succesfully loaded to db")


if __name__ == "__main__":
    asyncio.run(main())
