from core.db.models import SqlAlchemyBaseModel

PRODUCT_DELIVERY_METHODS = ["code", "onAccount"]


class Product(SqlAlchemyBaseModel): ...
