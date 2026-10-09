"""
수출신고 API 라우터
POST /api/declaration/validate  → XSD 검증
POST /api/declaration/sign      → 전자서명
POST /api/declaration/submit    → UNI-PASS 전송
POST /api/declaration/full      → 검증 + 서명 + 전송 일괄
GET  /api/declaration/xml       → XML 미리보기
"""
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from app.models.declaration import (
    DeclarationRequest,
    DeclarationResponse,
    SignRequest,
    SignResponse,
    ValidationErrorDetail,
)
from app.services.xml_builder import build_xml
from app.services.validator import validate_xml
from app.services.unipass_client import send_declaration
from app.services.signer import sign_xml_via_java

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/declaration", tags=["수출신고"])


# ── 1. XML 미리보기 ──────────────────────────────────────────────────────────

@router.post(
    "/xml",
    response_class=Response,
    summary="XML 생성 미리보기",
    description="신고 데이터를 XML로 변환하여 반환합니다. 전송은 하지 않습니다.",
)
async def preview_xml(req: DeclarationRequest):
    try:
        xml_bytes = build_xml(req)
        return Response(
            content=xml_bytes,
            media_type="application/xml",
            headers={"Content-Disposition": f"attachment; filename=declaration_{req.declaration_id}.xml"},
        )
    except Exception as e:
        logger.error(f"XML 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"XML 생성 실패: {e}")


# ── 2. XSD 유효성 검증 ───────────────────────────────────────────────────────

@router.post(
    "/validate",
    summary="XSD 유효성 검증",
    description="생성된 XML이 관세청 스키마를 준수하는지 검증합니다.",
)
async def validate_declaration(req: DeclarationRequest) -> dict:
    try:
        xml_bytes = build_xml(req)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"XML 생성 실패: {e}")

    is_valid, errors = validate_xml(xml_bytes)

    return {
        "valid": is_valid,
        "error_count": len(errors),
        "errors": [{"message": e} for e in errors],
        "xml_preview": xml_bytes.decode("utf-8")[:2000] + ("..." if len(xml_bytes) > 2000 else ""),
    }


# ── 3. 전자서명 ──────────────────────────────────────────────────────────────

@router.post(
    "/sign",
    summary="공인인증서 전자서명",
    description="XML에 공인인증서로 전자서명합니다. Java 서명 서비스 필요.",
)
async def sign_declaration(req: SignRequest) -> SignResponse:
    result = await sign_xml_via_java(req)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error or "전자서명 실패"
        )
    return result


# ── 4. UNI-PASS 전송 ─────────────────────────────────────────────────────────

@router.post(
    "/submit",
    summary="UNI-PASS 전송",
    description="서명된 XML을 관세청 UNI-PASS에 전송합니다.",
)
async def submit_declaration(req: DeclarationRequest) -> DeclarationResponse:
    # XML 생성
    try:
        xml_bytes = build_xml(req)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"XML 생성 실패: {e}")

    # 유효성 검증 (실제 XSD 파일이 있을 때만 블로킹, 폴백 스키마는 경고만)
    from pathlib import Path
    from app.services.validator import SCHEMA_FILE
    if SCHEMA_FILE.exists():
        is_valid, val_errors = validate_xml(xml_bytes)
        if not is_valid:
            raise HTTPException(
                status_code=422,
                detail={"message": "XML 유효성 검증 실패", "errors": val_errors},
            )
    else:
        logger.warning("실제 XSD 파일 없음 → 검증 생략 후 전송 진행")

    # UNI-PASS 전송 (서명 없이)
    result = await send_declaration(xml_bytes)
    return result


# ── 5. 일괄 처리 (검증 + 서명 + 전송) ───────────────────────────────────────

@router.post(
    "/full",
    summary="전체 신고 처리 (검증 → 서명 → 전송)",
    description="""
    수출신고 전 과정을 한 번에 처리합니다:
    1. Pydantic 모델 검증
    2. XML 생성
    3. XSD 스키마 검증
    4. 공인인증서 전자서명 (cert_* 파라미터 선택)
    5. UNI-PASS 전송
    """,
)
async def full_declaration(
    req: DeclarationRequest,
    cert_alias: str | None = None,
    keystore_path: str | None = None,
    keystore_password: str | None = None,
) -> DeclarationResponse:

    logger.info(f"수출신고 전체 처리 시작: 신고번호={req.declaration_id}, 란={len(req.goods_items)}개")

    # ① XML 생성
    try:
        xml_bytes = build_xml(req)
        logger.info(f"XML 생성 완료 ({len(xml_bytes):,} bytes)")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"XML 생성 실패: {e}")

    # ② XSD 검증
    is_valid, val_errors = validate_xml(xml_bytes)
    if not is_valid:
        logger.warning(f"XSD 검증 실패: {val_errors}")
        return DeclarationResponse(
            success=False,
            message="XML 유효성 검증 실패",
            errors=[ValidationErrorDetail(field="xml", message=e) for e in val_errors],
        )
    logger.info("XSD 검증 통과")

    # ③ 전자서명 (인증서 정보 제공 시)
    signed_xml: bytes | None = None
    if keystore_path and cert_alias and keystore_password:
        sign_req = SignRequest(
            xml_content=xml_bytes.decode("utf-8"),
            cert_alias=cert_alias,
            keystore_path=keystore_path,
            keystore_password=keystore_password,
        )
        sign_result = await sign_xml_via_java(sign_req)
        if sign_result.success and sign_result.signed_xml:
            signed_xml = sign_result.signed_xml.encode("utf-8")
            logger.info("전자서명 완료")
        else:
            logger.warning(f"전자서명 실패 (미서명 전송 계속): {sign_result.error}")
    else:
        logger.info("인증서 정보 미제공 → 서명 생략")

    # ④ UNI-PASS 전송
    result = await send_declaration(xml_bytes, signed_xml)
    logger.info(f"전송 결과: success={result.success}, 신고번호={result.declaration_number}")
    return result


# ── 6. 헬스체크 ──────────────────────────────────────────────────────────────

@router.get("/health", summary="서비스 상태 확인")
async def health():
    from app.services.signer import is_signer_available
    from app.core.config import settings

    java_ok = await is_signer_available()
    return {
        "status": "ok",
        "mock_mode": settings.MOCK_MODE,
        "unipass_env": settings.UNIPASS_ENV,
        "java_signer": "running" if java_ok else "not running",
    }
