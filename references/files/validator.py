"""
XSD 유효성 검증 서비스
관세청 스키마 기반 XML 검증
"""
import os
import logging
from pathlib import Path
from typing import Tuple, List
from lxml import etree

logger = logging.getLogger(__name__)

# 스키마 파일 경로 (배포 시 실제 XSD 파일 배치 필요)
SCHEMA_DIR = Path(__file__).parent.parent.parent / "schemas"
SCHEMA_FILE = SCHEMA_DIR / "KCS_DeclarationOfEXP_DJPSchemaModule_1.0_standard.xsd"

# ── 폴백용 인라인 스키마 (XSD 파일 없을 때 기본 구조만 검증) ────────────────
MINIMAL_SCHEMA_STR = """\
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:wco="urn:kr:gov:kcs:data:standard:KCS_DeclarationOfEXP_DJPSchemaModule:1:0"
           targetNamespace="urn:kr:gov:kcs:data:standard:KCS_DeclarationOfEXP_DJPSchemaModule:1:0"
           elementFormDefault="qualified">

  <xs:element name="Declaration">
    <xs:complexType>
      <xs:sequence>
        <xs:any minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
      </xs:sequence>
      <xs:anyAttribute processContents="lax"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""


def _load_schema() -> etree.XMLSchema:
    """XSD 스키마 로드 (실제 파일 우선, 없으면 폴백)"""
    if SCHEMA_FILE.exists():
        logger.info(f"XSD 스키마 로드: {SCHEMA_FILE}")
        with open(SCHEMA_FILE, "rb") as f:
            schema_doc = etree.parse(f)
        return etree.XMLSchema(schema_doc)
    else:
        logger.warning(
            f"XSD 파일 없음: {SCHEMA_FILE}\n"
            "→ 폴백 스키마 사용 (기본 구조만 검증)\n"
            f"→ 실제 스키마는 관세청 UNI-PASS 포털에서 수령 후 {SCHEMA_DIR}에 배치하세요."
        )
        schema_doc = etree.fromstring(MINIMAL_SCHEMA_STR.encode())
        return etree.XMLSchema(etree.ElementTree(schema_doc))


def validate_xml(xml_bytes: bytes) -> Tuple[bool, List[str]]:
    """
    XML 바이트를 XSD로 검증합니다.

    Returns:
        (is_valid, error_messages)
    """
    errors: List[str] = []

    # 1. 파싱 가능한지 먼저 확인
    try:
        doc = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as e:
        return False, [f"XML 파싱 오류: {e}"]

    # 2. 스키마 검증
    try:
        schema = _load_schema()
        is_valid = schema.validate(doc)
        if not is_valid:
            errors = [
                f"[{err.line}:{err.column}] {err.message}"
                for err in schema.error_log
            ]
        return is_valid, errors
    except Exception as e:
        logger.error(f"스키마 로드 실패: {e}")
        # 스키마 검증 자체가 실패한 경우 구조 검증만 수행
        return _manual_validate(doc)


def _manual_validate(root: etree._Element) -> Tuple[bool, List[str]]:
    """
    스키마 없이 필수 필드 존재 여부 수동 검증
    """
    errors: List[str] = []
    NS = "urn:kr:gov:kcs:data:standard:KCS_DeclarationOfEXP_DJPSchemaModule:1:0"

    required_fields = [
        "DeclarationOfficeID",
        "ID",
        "InvoiceAmount",
        "IssueDateTime",
        "TypeCode",
    ]

    for field in required_fields:
        el = root.find(f"{{{NS}}}{field}")
        if el is None or not (el.text or "").strip():
            errors.append(f"필수 필드 누락 또는 빈 값: <{field}>")

    # 란(GovernmentAgencyGoodsItem) 존재 확인
    gs = root.find(f"{{{NS}}}GoodsShipment")
    if gs is not None:
        items = gs.findall(f"{{{NS}}}GovernmentAgencyGoodsItem")
        if len(items) == 0:
            errors.append("품목 란(GovernmentAgencyGoodsItem)이 최소 1개 필요합니다.")
        for item in items:
            seq = item.find(f"{{{NS}}}SequenceNumeric")
            hs = item.findall(f".//{{{NS}}}Classification/{{{NS}}}ID")
            if not hs:
                seq_text = seq.text if seq is not None else "?"
                errors.append(f"란 {seq_text}: 세번부호(HS Code)가 누락되었습니다.")

    return len(errors) == 0, errors


def validate_xml_string(xml_str: str) -> Tuple[bool, List[str]]:
    """문자열 입력 버전"""
    return validate_xml(xml_str.encode("utf-8"))
