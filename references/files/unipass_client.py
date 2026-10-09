"""
UNI-PASS 전송 서비스
관세청 전자통관시스템 연동 (실제 + Mock 모드)
"""
import httpx
import logging
import asyncio
import os
import random
import string
from datetime import datetime
from typing import Optional
from app.models.declaration import DeclarationResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── UNI-PASS 엔드포인트 상수 ────────────────────────────────────────────────
UNIPASS_ENDPOINTS = {
    "test":       "https://unipasstest.customs.go.kr/tczs/ejp/ExprtDclrRcept.do",
    "production": "https://unipass.customs.go.kr/tczs/ejp/ExprtDclrRcept.do",
}

UNIPASS_HEADERS = {
    "Content-Type": "application/xml; charset=UTF-8",
    "Accept":       "application/xml",
    "User-Agent":   "KCS-Client/1.0",
}


# ── Mock 응답 생성 ───────────────────────────────────────────────────────────

def _generate_declaration_number() -> str:
    """테스트용 신고번호 생성 (형식: 세관코드 + 연도 + 일련번호)"""
    now = datetime.now()
    serial = "".join(random.choices(string.digits, k=7))
    return f"01001{now.strftime('%y')}{serial}"


def _generate_receipt_number() -> str:
    """테스트용 접수번호 생성"""
    return "R" + datetime.now().strftime("%Y%m%d%H%M%S") + random.choice(string.digits)


MOCK_SUCCESS_RESPONSE = """\
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <ResultCode>0000</ResultCode>
  <ResultMessage>정상처리되었습니다.</ResultMessage>
  <DeclarationNumber>{decl_num}</DeclarationNumber>
  <ReceiptNumber>{rcpt_num}</ReceiptNumber>
  <ProcessDateTime>{proc_dt}</ProcessDateTime>
</Response>
"""

MOCK_ERROR_RESPONSES = [
    ("<Response><ResultCode>E001</ResultCode><ResultMessage>세번부호 오류</ResultMessage></Response>", "세번부호 오류"),
    ("<Response><ResultCode>E002</ResultCode><ResultMessage>신고인부호 미등록</ResultMessage></Response>", "신고인부호 미등록"),
    ("<Response><ResultCode>E003</ResultCode><ResultMessage>수출화주 정보 불일치</ResultMessage></Response>", "수출화주 정보 불일치"),
]


async def _mock_send(xml_bytes: bytes) -> DeclarationResponse:
    """
    Mock 전송 (UNI-PASS 미연동 시 테스트 목적)
    실제 UNI-PASS 계정 없이도 전체 흐름 테스트 가능
    """
    logger.info("[MOCK] UNI-PASS 전송 시뮬레이션 시작")
    await asyncio.sleep(1.2)  # 네트워크 지연 시뮬레이션

    # 95% 확률로 성공
    if random.random() < 0.95:
        decl_num = _generate_declaration_number()
        rcpt_num = _generate_receipt_number()
        raw = MOCK_SUCCESS_RESPONSE.format(
            decl_num=decl_num,
            rcpt_num=rcpt_num,
            proc_dt=datetime.now().strftime("%Y%m%d%H%M%S"),
        )
        logger.info(f"[MOCK] 신고 수리 완료 → 신고번호: {decl_num}")
        return DeclarationResponse(
            success=True,
            message="[MOCK] 신고가 정상 수리되었습니다.",
            declaration_number=decl_num,
            receipt_number=rcpt_num,
            raw_response=raw,
        )
    else:
        err_xml, err_msg = random.choice(MOCK_ERROR_RESPONSES)
        logger.warning(f"[MOCK] 신고 반려: {err_msg}")
        return DeclarationResponse(
            success=False,
            message=f"[MOCK] 신고 반려: {err_msg}",
            raw_response=err_xml,
        )


# ── 실제 전송 ────────────────────────────────────────────────────────────────

def _parse_unipass_response(response_text: str) -> DeclarationResponse:
    """UNI-PASS XML 응답 파싱"""
    from lxml import etree
    try:
        root = etree.fromstring(response_text.encode("utf-8"))
        result_code = (root.findtext("ResultCode") or "").strip()
        result_msg  = (root.findtext("ResultMessage") or "알 수 없는 오류").strip()
        decl_num    = root.findtext("DeclarationNumber")
        rcpt_num    = root.findtext("ReceiptNumber")

        if result_code == "0000":
            return DeclarationResponse(
                success=True,
                message=result_msg,
                declaration_number=decl_num,
                receipt_number=rcpt_num,
                raw_response=response_text,
            )
        else:
            return DeclarationResponse(
                success=False,
                message=f"[{result_code}] {result_msg}",
                raw_response=response_text,
            )
    except Exception as e:
        logger.error(f"응답 파싱 실패: {e}\n원문: {response_text[:500]}")
        return DeclarationResponse(
            success=False,
            message=f"응답 파싱 오류: {e}",
            raw_response=response_text,
        )


async def _real_send(
    xml_bytes: bytes,
    signed_xml: Optional[bytes] = None,
) -> DeclarationResponse:
    """
    실제 UNI-PASS 전송

    Args:
        xml_bytes:   원본 XML
        signed_xml:  전자서명된 XML (있으면 이것을 전송)
    """
    payload = signed_xml if signed_xml else xml_bytes
    endpoint = UNIPASS_ENDPOINTS[settings.UNIPASS_ENV]

    logger.info(f"UNI-PASS 전송 시작 → {endpoint}")

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            verify=settings.SSL_VERIFY,
        ) as client:
            response = await client.post(
                endpoint,
                content=payload,
                headers={
                    **UNIPASS_HEADERS,
                    # 실제 연동 시 관세청에서 발급받은 인증 헤더 추가
                    # "X-Customs-AuthKey": settings.UNIPASS_AUTH_KEY,
                },
            )
            response.raise_for_status()
            logger.info(f"UNI-PASS 응답 수신 (HTTP {response.status_code})")
            return _parse_unipass_response(response.text)

    except httpx.TimeoutException:
        msg = "UNI-PASS 연결 시간 초과 (30초)"
        logger.error(msg)
        return DeclarationResponse(success=False, message=msg)

    except httpx.HTTPStatusError as e:
        msg = f"UNI-PASS HTTP 오류: {e.response.status_code}"
        logger.error(f"{msg}\n{e.response.text[:500]}")
        return DeclarationResponse(success=False, message=msg, raw_response=e.response.text)

    except Exception as e:
        msg = f"전송 중 예외 발생: {type(e).__name__}: {e}"
        logger.error(msg)
        return DeclarationResponse(success=False, message=msg)


# ── 공개 인터페이스 ──────────────────────────────────────────────────────────

async def send_declaration(
    xml_bytes: bytes,
    signed_xml: Optional[bytes] = None,
) -> DeclarationResponse:
    """
    수출신고서 UNI-PASS 전송 (Mock/Real 자동 선택)

    - settings.MOCK_MODE=True  → Mock 전송 (테스트)
    - settings.MOCK_MODE=False → 실제 UNI-PASS 전송
    """
    if settings.MOCK_MODE:
        logger.info("MOCK_MODE 활성화 → Mock 전송 사용")
        return await _mock_send(xml_bytes)
    else:
        return await _real_send(xml_bytes, signed_xml)
