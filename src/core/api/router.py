from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from config import Config
from core.ioc import Resolve
from core.api.sse import message_stream
from core.utils import FILES_UPLOAD_DIR
from products.handlers import router as product_router
from users.handlers import router as users_router
from news.handlers import router as news_router
from orders.handlers import router as orders_router
from shopping.handlers import cart_router, wishlist_router
from payments.handlers import router as payments_router

major_version = Resolve(Config).api_version[0]

api_router = APIRouter(prefix=f"/api/v{major_version}", tags=[f"api_v{major_version}"])

api_router.include_router(product_router)
api_router.include_router(users_router)
api_router.include_router(news_router)
api_router.include_router(orders_router)
api_router.include_router(cart_router)
api_router.include_router(wishlist_router)
api_router.include_router(payments_router)

router = APIRouter()
router.include_router(api_router)

router.add_api_route("/stream", message_stream)


@router.get("/ping", include_in_schema=False)
async def ping() -> dict[str, str | list[str]]:
    return {"status": "available", "version": Resolve(Config).api_version}


@router.get("/media/{filename}", include_in_schema=False)
async def media_serve(filename: str):
    dir = FILES_UPLOAD_DIR
    if not (dir / filename).exists():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"File {filename} does not exist"
        )
    return FileResponse(dir / filename)
