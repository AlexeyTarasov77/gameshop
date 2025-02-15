from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from config import Config
from core.ioc import Resolve
from core.utils import get_upload_dir
from products.handlers import router as product_router
from users.handlers import router as users_router
from news.handlers import router as news_router
from orders.handlers import router as orders_router
from sessions.handlers import cart_router, wishlist_router

major_version = Resolve(Config).api_version[0]

api_router = APIRouter(prefix=f"/api/v{major_version}", tags=[f"api_v{major_version}"])

api_router.include_router(product_router)
api_router.include_router(users_router)
api_router.include_router(news_router)
api_router.include_router(orders_router)
api_router.include_router(cart_router)
api_router.include_router(wishlist_router)

router = APIRouter()
router.include_router(api_router)


@router.get("/ping")
async def ping() -> dict[str, str | list[str]]:
    return {"status": "available", "version": Resolve(Config).api_version}


media_serve_url = f"/{Resolve(Config).server.media_serve_path}"


@router.get(media_serve_url)
async def media_serve(filename: str | None = None):
    dir = get_upload_dir()
    if filename:
        if not (dir / filename).exists():
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"File {filename} does not exist"
            )
        return FileResponse(dir / filename)
    content = ""
    for path in dir.iterdir():
        path_with_query_param = media_serve_url + f"?filename={path.name}"
        print(path, path_with_query_param)
        content += f'<a href="{path_with_query_param}" style="margin-right: 50px;">{path.name}</a>'
    return HTMLResponse(content)
