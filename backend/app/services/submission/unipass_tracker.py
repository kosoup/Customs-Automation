"""
관세청 UNI-PASS Open API - 수출통관 상태 조회.
API 문서: https://unipass.customs.go.kr/openapi/

주요 API:
  - 수출신고수리내역조회 (expDclrAceptDtlsQry)
  - 화물통관진행정보 (cargCclsQry)

응답 형식: XML
인증: API 키를 URL 파라미터로 전달
"""
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import httpx
from defusedxml import ElementTree as DET
from defusedxml.common import DefusedXmlException

from app.config import settings

logger = logging.getLogger(__name__)

UNIPASS_BASE_URL = "https://unipass.customs.go.kr/ext/rest"


def _first(el: ET.Element, *paths: str) -> Optional[ET.Element]:
    for path in paths:
        found = el.find(path)
        if found is not None:
            return found
    return None


def _parse_status_xml(xml_text: str) -> dict:
    """UNI-PASS 응답 XML을 딕셔너리로 파싱."""
    try:
        root = DET.fromstring(xml_text)
        result = {}

        # 공통 응답 코드
        code_el = _first(root, ".//tCd", ".//errCd")
        msg_el = _first(root, ".//tMsg", ".//errMsg")
        result["code"] = code_el.text if code_el is not None else None
        result["message"] = msg_el.text if msg_el is not None else None

        # 수출신고 상태
        status_el = _first(root, ".//expDclrStts", ".//dclrStts")
        result["declaration_status"] = status_el.text if status_el is not None else None

        # 수리번호
        acpt_el = _first(root, ".//expDclrAceptNo", ".//aceptNo")
        result["accept_number"] = acpt_el.text if acpt_el is not None else None

        # 수리일자
        acpt_dt = _first(root, ".//expDclrAceptDt", ".//aceptDt")
        result["accept_date"] = acpt_dt.text if acpt_dt is not None else None

        result["raw"] = xml_text
        return result
    except (ET.ParseError, DefusedXmlException):
        logger.warning("UNI-PASS 상태 응답 XML 파싱 실패", exc_info=True)
        return {"code": "PARSE_ERROR", "message": "XML 파싱 실패", "raw": xml_text}


async def track_by_invoice(invoice_number: str) -> dict:
    """
    인보이스 번호로 수출신고 상태를 조회한다.
    API 키 미설정 시 설정 안내 메시지를 반환한다.
    """
    api_key = settings.UNIPASS_API_KEY
    if not api_key:
        return {
            "code": "NOT_CONFIGURED",
            "message": "UNIPASS_API_KEY가 설정되지 않았습니다. .env 파일에 키를 입력하세요.",
            "declaration_status": None,
            "accept_number": None,
        }

    url = f"{UNIPASS_BASE_URL}/expDclrAceptDtlsQry/retrieveExpDclrAceptDtls"
    params = {"crkyCd": api_key, "invNo": invoice_number}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError:
        logger.warning("UNI-PASS 수출신고 상태 조회 실패 (invoice_number=%s)", invoice_number, exc_info=True)
        return {
            "code": "REQUEST_ERROR",
            "message": "UNI-PASS 조회 요청이 실패했습니다.",
            "declaration_status": None,
            "accept_number": None,
        }

    return _parse_status_xml(resp.text)


async def track_by_ref(submission_ref: str) -> dict:
    """
    접수번호(수리번호)로 화물 통관 상태를 조회한다.
    """
    api_key = settings.UNIPASS_API_KEY
    if not api_key:
        return {
            "code": "NOT_CONFIGURED",
            "message": "UNIPASS_API_KEY가 설정되지 않았습니다.",
            "declaration_status": None,
        }

    url = f"{UNIPASS_BASE_URL}/cargCclsQry/retrieveCargCcls"
    params = {"crkyCd": api_key, "mblNo": submission_ref}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError:
        logger.warning("UNI-PASS 화물통관 상태 조회 실패 (submission_ref=%s)", submission_ref, exc_info=True)
        return {
            "code": "REQUEST_ERROR",
            "message": "UNI-PASS 조회 요청이 실패했습니다.",
            "declaration_status": None,
        }

    return _parse_status_xml(resp.text)
