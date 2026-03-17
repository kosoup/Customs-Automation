"""
uTradeHub (KTNET) API 연동.
수출신고 EDI 전송 서비스.

실제 API 키 및 계정은 .env 파일에서 로드한다:
  UTRADEHUB_API_KEY=...
  UTRADEHUB_SENDER_ID=...
  UTRADEHUB_RECEIVER_ID=...

uTradeHub EDI는 XML 메시지 기반이며, 아래는 수출신고서(CUSEXPDEC) 포맷 기준이다.
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import settings
from app.models.declaration import Declaration

UTRADEHUB_BASE_URL = "https://edi.utradehub.or.kr"
UTRADEHUB_SUBMIT_PATH = "/edi/submit"


def _build_xml(declaration: Declaration, sender_id: str, receiver_id: str) -> str:
    """수출신고서 XML 전문 생성 (CUSEXPDEC 포맷 기준)."""
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    root = ET.Element("CUSEXPDEC")
    root.set("xmlns", "urn:customs.go.kr:CUSEXPDEC:1")

    # 전문 헤더
    hdr = ET.SubElement(root, "HEADER")
    ET.SubElement(hdr, "SENDER_ID").text = sender_id
    ET.SubElement(hdr, "RECEIVER_ID").text = receiver_id
    ET.SubElement(hdr, "SEND_DT").text = now
    ET.SubElement(hdr, "DECL_CODE").text = declaration.declarant_code or ""

    # 공통사항 1 (신고인, 수출자, 구매자)
    c1 = ET.SubElement(root, "COMMON1")
    ET.SubElement(c1, "EXPORTER_NM").text = declaration.exporter_name or ""
    ET.SubElement(c1, "EXPORTER_BIZ_NO").text = declaration.exporter_business_number or ""
    ET.SubElement(c1, "EXPORTER_ADDR").text = declaration.exporter_address or ""
    ET.SubElement(c1, "BUYER_NM").text = declaration.buyer_name or ""
    ET.SubElement(c1, "BUYER_COUNTRY").text = declaration.buyer_country_code or ""
    ET.SubElement(c1, "BUYER_ADDR").text = declaration.buyer_address or ""

    # 공통사항 2 (무역조건, 운송)
    c2 = ET.SubElement(root, "COMMON2")
    ET.SubElement(c2, "INCOTERMS").text = declaration.incoterms or ""
    ET.SubElement(c2, "CURRENCY").text = declaration.currency_code or ""
    ET.SubElement(c2, "PAYMENT_METHOD").text = declaration.payment_method or ""
    ET.SubElement(c2, "INVOICE_NO").text = declaration.invoice_number or ""
    ET.SubElement(c2, "INVOICE_DT").text = str(declaration.invoice_date) if declaration.invoice_date else ""
    ET.SubElement(c2, "TOTAL_AMT").text = str(declaration.total_amount or "")
    ET.SubElement(c2, "LOADING_PORT").text = declaration.loading_port or ""
    ET.SubElement(c2, "DEST_COUNTRY").text = declaration.destination_country_code or ""
    ET.SubElement(c2, "DEST_PORT").text = declaration.destination_port or ""
    ET.SubElement(c2, "SHIP_DT").text = str(declaration.shipping_date) if declaration.shipping_date else ""
    ET.SubElement(c2, "NET_WEIGHT").text = str(declaration.net_weight_kg or "")
    ET.SubElement(c2, "GROSS_WEIGHT").text = str(declaration.gross_weight_kg or "")
    ET.SubElement(c2, "PKG_TYPE").text = declaration.package_type or ""
    ET.SubElement(c2, "PKG_CNT").text = str(declaration.package_count or "")

    # 품목 란
    items_el = ET.SubElement(root, "ITEMS")
    for item in sorted(declaration.items, key=lambda i: i.item_seq):
        el = ET.SubElement(items_el, "ITEM")
        ET.SubElement(el, "SEQ").text = str(item.item_seq)
        ET.SubElement(el, "GOODS_NM_KR").text = item.product_name_ko or ""
        ET.SubElement(el, "GOODS_NM_EN").text = item.product_name_en or ""
        ET.SubElement(el, "HSCODE").text = item.hscode or ""
        ET.SubElement(el, "MODEL").text = item.model_spec or ""
        ET.SubElement(el, "QTY").text = str(item.quantity or "")
        ET.SubElement(el, "UNIT").text = item.unit or ""
        ET.SubElement(el, "UNIT_PRICE").text = str(item.unit_price or "")
        ET.SubElement(el, "AMOUNT").text = str(item.amount or "")

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


async def submit(declaration: Declaration) -> dict:
    """
    uTradeHub에 수출신고서 EDI를 전송한다.
    API 키 미설정 시 NotConfiguredError를 반환.
    """
    api_key = settings.UTRADEHUB_API_KEY
    if not api_key:
        raise RuntimeError(
            "UTRADEHUB_API_KEY가 설정되지 않았습니다. "
            ".env 파일에 UTRADEHUB_API_KEY, UTRADEHUB_SENDER_ID, UTRADEHUB_RECEIVER_ID를 입력하세요."
        )

    sender_id = getattr(settings, "UTRADEHUB_SENDER_ID", "")
    receiver_id = getattr(settings, "UTRADEHUB_RECEIVER_ID", "CUST0001")

    xml_body = _build_xml(declaration, sender_id, receiver_id)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{UTRADEHUB_BASE_URL}{UTRADEHUB_SUBMIT_PATH}",
            content=xml_body,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "Authorization": f"Bearer {api_key}",
            },
        )
        resp.raise_for_status()

    # 응답 XML 파싱 (접수번호 추출)
    root = ET.fromstring(resp.text)
    ref_el = root.find(".//RECEIPT_NO") or root.find(".//REF_NO")
    tracking = ref_el.text if ref_el is not None else None

    return {
        "status": "success",
        "tracking_number": tracking,
        "response_raw": resp.text,
    }
