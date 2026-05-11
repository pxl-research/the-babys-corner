from fastapi import APIRouter
from app.schemas import TagsListResponse
from app.services.catalog import get_catalog

router = APIRouter(prefix="/api/filters", tags=["filters"])


@router.get("/tags", response_model=TagsListResponse)
async def get_tags():
    return TagsListResponse(tags=get_catalog().get_tags())
