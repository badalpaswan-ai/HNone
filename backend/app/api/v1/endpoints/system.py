from fastapi import APIRouter

from app.core.config import settings
from app.core.security import rbac_metadata

router = APIRouter()


@router.get("/", tags=["System"], summary="Health check")
def health():
    return {
        "status": "running",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get(
    "/rbac/endpoints",
    tags=["Access Control"],
    summary="List roles and endpoint permissions",
)
def rbac_endpoints():
    return rbac_metadata()
