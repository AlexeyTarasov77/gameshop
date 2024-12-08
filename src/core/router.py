from fastapi import APIRouter
from products.handlers import router as product_router
from users.handlers import router as users_router

router = APIRouter(prefix="/api/v1", tags=["api_v1"])
router.include_router(product_router)
router.include_router(users_router)
