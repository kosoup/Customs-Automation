from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.company_settings import CompanySettings
from app.schemas.company_settings import CompanySettingsUpdate, CompanySettingsResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _get_or_create_settings(db: AsyncSession) -> CompanySettings:
    result = await db.execute(select(CompanySettings).where(CompanySettings.id == CompanySettings.SINGLETON_ID))
    cs = result.scalar_one_or_none()
    if cs is None:
        cs = CompanySettings(id=CompanySettings.SINGLETON_ID)
        db.add(cs)
        await db.commit()
        await db.refresh(cs)
    return cs


@router.get("", response_model=CompanySettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> CompanySettings:
    return await _get_or_create_settings(db)


@router.put("", response_model=CompanySettingsResponse)
async def update_settings(body: CompanySettingsUpdate, db: AsyncSession = Depends(get_db)) -> CompanySettings:
    cs = await _get_or_create_settings(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cs, field, value)
    await db.commit()
    await db.refresh(cs)
    return cs
