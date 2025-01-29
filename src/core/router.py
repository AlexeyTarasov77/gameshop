from fastapi import APIRouter
from products.handlers import router as product_router
from users.handlers import router as users_router
from news.handlers import router as news_router
from orders.handlers import router as orders_router

router = APIRouter(prefix="/api/v1", tags=["api_v1"])


router.include_router(product_router)
router.include_router(users_router)
router.include_router(news_router)
router.include_router(orders_router)
