from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.declaration import Declaration
from app.models.company_settings import CompanySettings
from app.models.submission import Submission
from app.schemas.submission import SubmissionResponse, TrackResponse
from app.services.submission import file_export, utradehub, unipass_tracker
from app.services.xml_generator import generate_govcbr830_xml

router = APIRouter(prefix="/api/declarations", tags=["submissions"])


async def _get_validated_decl(decl_id: int, db: AsyncSession) -> Declaration:
    result = await db.execute(
        select(Declaration).options(selectinload(Declaration.items)).where(Declaration.id == decl_id)
    )
    decl = result.scalar_one_or_none()
    if not decl:
        raise HTTPException(404, "신고서를 찾을 수 없습니다")
    return decl


@router.post("/{decl_id}/submit", response_model=SubmissionResponse, status_code=201)
async def submit_declaration(
    decl_id: int,
    method: str = Query("file_export", description="utradehub | file_export"),
    db: AsyncSession = Depends(get_db),
):
    decl = await _get_validated_decl(decl_id, db)

    if decl.status not in ("validated",):
        raise HTTPException(400, "검증(validated) 상태의 신고서만 제출할 수 있습니다")
    if method not in ("utradehub", "file_export"):
        raise HTTPException(400, f"지원하지 않는 제출 방식: {method}")

    sub = Submission(declaration_id=decl_id, method=method, status="pending")
    db.add(sub)

    try:
        if method == "utradehub":
            result = await utradehub.submit(decl)
            sub.status = "success"
            sub.tracking_number = result.get("tracking_number")
            sub.response_raw = result.get("response_raw")
        elif method == "file_export":
            # 파일 내보내기는 별도 다운로드 엔드포인트로 제공
            # 여기서는 이력만 기록
            sub.status = "success"
            sub.tracking_number = None
        decl.status = "submitted"
        if sub.tracking_number:
            decl.submission_ref = sub.tracking_number

    except RuntimeError as e:
        sub.status = "failed"
        sub.error_message = str(e)
        await db.commit()
        raise HTTPException(503, str(e))
    except Exception as e:
        sub.status = "failed"
        sub.error_message = str(e)
        await db.commit()
        raise HTTPException(502, f"제출 중 오류가 발생했습니다: {e}")

    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("/{decl_id}/track", response_model=TrackResponse)
async def track_declaration(decl_id: int, db: AsyncSession = Depends(get_db)):
    decl = await _get_validated_decl(decl_id, db)

    if decl.submission_ref:
        result = await unipass_tracker.track_by_ref(decl.submission_ref)
    elif decl.invoice_number:
        result = await unipass_tracker.track_by_invoice(decl.invoice_number)
    else:
        return TrackResponse(
            code="NO_REF",
            message="접수번호나 인보이스 번호가 없어 조회할 수 없습니다"
        )

    # 수리번호가 반환되면 DB에 저장
    if result.get("accept_number") and not decl.unipass_ref:
        decl.unipass_ref = result["accept_number"]
        decl.status = "accepted"
        await db.commit()

    return TrackResponse(**{k: v for k, v in result.items() if k != "raw"})


@router.get("/{decl_id}/export-file")
async def export_file(
    decl_id: int,
    fmt: str = Query("xlsx", description="xlsx | csv"),
    db: AsyncSession = Depends(get_db),
):
    decl = await _get_validated_decl(decl_id, db)

    if fmt not in ("xlsx", "csv"):
        raise HTTPException(400, f"지원하지 않는 내보내기 형식: {fmt}")
    if fmt == "csv":
        content = file_export.generate_csv(decl)
        filename = f"declaration_{decl_id}.csv"
        media_type = "text/csv; charset=utf-8-sig"
    else:
        content = file_export.generate_excel(decl)
        filename = f"declaration_{decl_id}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{decl_id}/export-xml")
async def export_xml(decl_id: int, db: AsyncSession = Depends(get_db)):
    """GOVCBR830 XML 다운로드."""
    decl = await _get_validated_decl(decl_id, db)

    cs_result = await db.execute(select(CompanySettings).where(CompanySettings.id == 1))
    cs = cs_result.scalar_one_or_none()

    xml_bytes = generate_govcbr830_xml(decl, cs)
    filename = f"GOVCBR830_{decl_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"

    return Response(
        content=xml_bytes,
        media_type="application/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
