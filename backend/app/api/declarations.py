from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.declaration import Declaration, DeclarationItem
from app.models.company_settings import CompanySettings
from app.schemas.declaration import (
    DeclarationCreate,
    DeclarationUpdate,
    DeclarationResponse,
    DeclarationListResponse,
    ValidationResult,
)
from app.services.validator import validate_declaration

router = APIRouter(prefix="/api/declarations", tags=["declarations"])


@router.post("", response_model=DeclarationResponse, status_code=201)
async def create_declaration(body: DeclarationCreate, db: AsyncSession = Depends(get_db)):
    decl = Declaration(**body.model_dump(exclude={"items"}))

    # 회사 설정에서 신고인/수출자 정보 자동 채움
    if not decl.declarant_code and not decl.exporter_business_number:
        cs_result = await db.execute(select(CompanySettings).where(CompanySettings.id == 1))
        cs = cs_result.scalar_one_or_none()
        if cs:
            if not decl.declarant_code:
                decl.declarant_code = cs.declarant_code
            if not decl.declarant_name:
                decl.declarant_name = cs.declarant_name
            if not decl.exporter_business_number:
                decl.exporter_business_number = cs.exporter_business_number
            if not decl.exporter_address:
                decl.exporter_address = cs.exporter_address
            if not decl.loading_port:
                decl.loading_port = cs.loading_port

    for item_data in body.items:
        decl.items.append(DeclarationItem(**item_data.model_dump()))
    db.add(decl)
    await db.commit()
    await db.refresh(decl, ["items"])
    return decl


@router.get("", response_model=List[DeclarationListResponse])
async def list_declarations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Declaration).order_by(Declaration.created_at.desc())
    if status:
        query = query.where(Declaration.status == status)
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{decl_id}", response_model=DeclarationResponse)
async def get_declaration(decl_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Declaration).options(selectinload(Declaration.items)).where(Declaration.id == decl_id)
    )
    decl = result.scalar_one_or_none()
    if not decl:
        raise HTTPException(404, "신고서를 찾을 수 없습니다")
    return decl


@router.put("/{decl_id}", response_model=DeclarationResponse)
async def update_declaration(decl_id: int, body: DeclarationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Declaration).options(selectinload(Declaration.items)).where(Declaration.id == decl_id)
    )
    decl = result.scalar_one_or_none()
    if not decl:
        raise HTTPException(404, "신고서를 찾을 수 없습니다")
    if decl.status not in ("draft", "validated"):
        raise HTTPException(400, "제출된 신고서는 수정할 수 없습니다")

    update_data = body.model_dump(exclude={"items"}, exclude_unset=True)
    for key, val in update_data.items():
        setattr(decl, key, val)

    if body.items is not None:
        # 기존 품목 삭제 후 재생성
        decl.items.clear()
        for item_data in body.items:
            decl.items.append(DeclarationItem(**item_data.model_dump()))

    decl.status = "draft"
    await db.commit()
    await db.refresh(decl, ["items"])
    return decl


@router.delete("/{decl_id}", status_code=204)
async def delete_declaration(decl_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Declaration).where(Declaration.id == decl_id))
    decl = result.scalar_one_or_none()
    if not decl:
        raise HTTPException(404, "신고서를 찾을 수 없습니다")
    if decl.status not in ("draft",):
        raise HTTPException(400, "초안 상태의 신고서만 삭제할 수 있습니다")
    await db.delete(decl)
    await db.commit()


@router.post("/{decl_id}/validate", response_model=ValidationResult)
async def validate_declaration_endpoint(decl_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Declaration).options(selectinload(Declaration.items)).where(Declaration.id == decl_id)
    )
    decl = result.scalar_one_or_none()
    if not decl:
        raise HTTPException(404, "신고서를 찾을 수 없습니다")

    data = {c.name: getattr(decl, c.name) for c in Declaration.__table__.columns}
    items = [
        {c.name: getattr(item, c.name) for c in DeclarationItem.__table__.columns}
        for item in decl.items
    ]
    errors = validate_declaration(data, items)

    if not errors:
        decl.status = "validated"
        await db.commit()

    return ValidationResult(valid=len(errors) == 0, errors=errors)


@router.get("/stats/summary")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """대시보드용 상태별 건수 집계."""
    result = await db.execute(
        select(Declaration.status, func.count(Declaration.id)).group_by(Declaration.status)
    )
    rows = result.all()
    counts = {row[0]: row[1] for row in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "draft": counts.get("draft", 0),
        "validated": counts.get("validated", 0),
        "submitted": counts.get("submitted", 0),
        "accepted": counts.get("accepted", 0),
        "rejected": counts.get("rejected", 0),
    }
