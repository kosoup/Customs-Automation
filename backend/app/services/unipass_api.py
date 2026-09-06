"""
관세청 UNI-PASS Open API - HS코드/관세율/세관장확인 조회.
Base URL: https://unipass.customs.go.kr:38010/ext/rest/
응답 형식: XML
"""
import xml.etree.ElementTree as ET
from typing import Optional

import httpx
from defusedxml import ElementTree as DET
from defusedxml.common import DefusedXmlException

from app.config import settings

UNIPASS_BASE = "https://unipass.customs.go.kr:38010/ext/rest"


def _text(el, path: str) -> Optional[str]:
    node = el.find(path)
    return node.text.strip() if node is not None and node.text else None


async def search_hs(keyword: str, page: int = 1, size: int = 10) -> dict:
    """
    HS 부호검색 API.
    엔드포인트: hsSrchQry/retrieveHsSrch
    keyword가 숫자면 HS코드 부분 검색, 아니면 품목명 검색.
    """
    if not settings.UNIPASS_KEY_HS_SEARCH:
        return {"items": [], "error": "UNI-PASS HS 검색 API 키가 설정되지 않았습니다"}

    params: dict = {"crkyCd": settings.UNIPASS_KEY_HS_SEARCH}
    if keyword.strip().isdigit():
        params["hsSgn"] = keyword.strip()
    else:
        params["hsSgnNm"] = keyword.strip()

    url = f"{UNIPASS_BASE}/hsSrchQry/retrieveHsSrch"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return {"items": [], "error": str(e)}

    try:
        root = DET.fromstring(resp.text)
    except (ET.ParseError, DefusedXmlException):
        return {"items": [], "error": "XML 파싱 실패"}

    items = []
    for item_el in root.findall(".//item") or root.findall(".//hsSrch"):
        hscode = _text(item_el, "hsSgn") or _text(item_el, "hsCode") or ""
        name_ko = _text(item_el, "hsSgnNm") or _text(item_el, "itemNm") or ""
        name_en = _text(item_el, "hsSgnEnNm") or _text(item_el, "itemEnNm") or ""
        if hscode or name_ko:
            items.append({"hscode": hscode, "name_ko": name_ko, "name_en": name_en})

    return {"items": items}


async def get_tariff(hscode: str) -> dict:
    """
    관세율기본조회 API.
    엔드포인트: tariffRtInfoQry/retrieveTariffRtInfo
    """
    if not settings.UNIPASS_KEY_TARIFF:
        return {"hscode": hscode, "error": "UNI-PASS 관세율 API 키가 설정되지 않았습니다"}

    url = f"{UNIPASS_BASE}/tariffRtInfoQry/retrieveTariffRtInfo"
    params = {"crkyCd": settings.UNIPASS_KEY_TARIFF, "hsSgn": hscode.strip()}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return {"hscode": hscode, "error": str(e)}

    try:
        root = DET.fromstring(resp.text)
    except (ET.ParseError, DefusedXmlException):
        return {"hscode": hscode, "error": "XML 파싱 실패"}

    item_el = root.find(".//item")
    if item_el is None:
        item_el = root.find(".//tariffRtInfo")
    if item_el is None:
        item_el = root

    return {
        "hscode": hscode,
        "tariff_rate": _text(item_el, "bsTariffRt") or _text(item_el, "tariffRt") or _text(item_el, "gnrlTariffRt"),
        "unit": _text(item_el, "statUnit") or _text(item_el, "unit"),
        "duty_type": _text(item_el, "tariffTypeCd") or _text(item_el, "dutyTypeCd"),
    }


async def check_customs_confirmation(hscode: str) -> dict:
    """
    세관장확인대상물품조회 API.
    엔드포인트: cstmHsConfQry/retrieveCstmHsConf
    """
    if not settings.UNIPASS_KEY_CUSTOMS_CHECK:
        return {"is_target": False, "error": "UNI-PASS 세관장확인 API 키가 설정되지 않았습니다"}

    url = f"{UNIPASS_BASE}/cstmHsConfQry/retrieveCstmHsConf"
    params = {"crkyCd": settings.UNIPASS_KEY_CUSTOMS_CHECK, "hsSgn": hscode.strip()}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        return {"is_target": False, "error": str(e)}

    try:
        root = DET.fromstring(resp.text)
    except (ET.ParseError, DefusedXmlException):
        return {"is_target": False, "error": "XML 파싱 실패"}

    requirements = []
    for el in root.findall(".//item") or root.findall(".//cstmHsConf"):
        law_name = _text(el, "rgltnLwNm") or _text(el, "lawNm") or ""
        conf_org = _text(el, "confOrgNm") or _text(el, "orgNm") or ""
        if law_name or conf_org:
            requirements.append({"law_name": law_name, "confirmation_org": conf_org})

    is_target = len(requirements) > 0
    return {"is_target": is_target, "requirements": requirements}
