from fastapi import APIRouter, Query

from app.services import unipass_api

router = APIRouter(prefix="/api/unipass", tags=["unipass"])


@router.get("/hs-search")
async def hs_search(q: str = Query(..., min_length=1), page: int = 1) -> dict:
    """HS코드 검색. q=품목명 또는 부분 HS코드."""
    return await unipass_api.search_hs(q, page)


@router.get("/tariff/{hscode}")
async def tariff(hscode: str) -> dict:
    """관세율 조회."""
    return await unipass_api.get_tariff(hscode)


@router.get("/customs-check/{hscode}")
async def customs_check(hscode: str) -> dict:
    """세관장확인대상 조회."""
    return await unipass_api.check_customs_confirmation(hscode)
